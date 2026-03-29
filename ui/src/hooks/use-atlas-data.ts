import { useEffect, useMemo, useState, useCallback } from 'react';
import { useMutation, useQueries, useQuery, useQueryClient } from '@tanstack/react-query';
import { mockActivityFeed, mockAuditLog, mockClients, mockIncidents } from '@/data/mock';
import {
  fetchActiveIncidents,
  fetchIncidentDetails,
  fetchAuditLog,
  fetchTrustLevel,
  buildWsUrl,
  approveIncident,
  rejectIncident,
  modifyIncident,
  fetchPlaybookLibrary,
  confirmTrustUpgrade,
} from '@/lib/atlas-api';
import type { ApprovalPayload, RejectionPayload, ModifyPayload } from '@/lib/atlas-api';
import {
  adaptActiveIncident,
  adaptActivityEvent,
  adaptAuditRecord,
  buildClientsFromLiveData,
  knownBackendClientIds,
  backendClientIdFromFrontend,
} from '@/lib/atlas-adapters';
import { atlasConfig } from '@/lib/atlas-config';
import type { ActivityFeedEntry, AuditEntry, Incident } from '@/types/atlas';

const fallbackIncidentById = Object.fromEntries(mockIncidents.map((incident) => [incident.id, incident]));

function parseIncomingMessage(event: MessageEvent): Record<string, any> | null {
  try {
    return JSON.parse(event.data);
  } catch {
    return null;
  }
}

function mergeIncidentState(
  current: Record<string, Record<string, any>>,
  incoming: Record<string, any>,
): Record<string, Record<string, any>> {
  const threadId = String(incoming?.thread_id || '');
  if (!threadId) return current;
  return {
    ...current,
    [threadId]: {
      ...current[threadId],
      ...incoming,
    },
  };
}

function sortAuditEntries(entries: AuditEntry[]): AuditEntry[] {
  return [...entries].sort((left, right) => {
    const leftDate = new Date(left.timestamp.replace(' ', 'T')).getTime();
    const rightDate = new Date(right.timestamp.replace(' ', 'T')).getTime();
    return rightDate - leftDate;
  });
}

// ─── Robust WebSocket with auto-reconnect ────────────────────────────────────

interface ManagedSocket {
  close: () => void;
}

function createManagedSocket(
  url: string,
  onMessage: (payload: Record<string, any>) => void,
  maxRetries = 8,
): ManagedSocket {
  let ws: WebSocket | null = null;
  let retries = 0;
  let destroyed = false;
  let retryTimer: ReturnType<typeof setTimeout> | null = null;

  function connect() {
    if (destroyed) return;
    try {
      ws = new WebSocket(url);
    } catch {
      scheduleRetry();
      return;
    }

    ws.onmessage = (event) => {
      const payload = parseIncomingMessage(event);
      if (!payload || payload.type === 'ping') return;
      onMessage(payload);
    };

    ws.onopen = () => {
      retries = 0;
    };

    ws.onerror = () => {
      // onerror always followed by onclose — let onclose handle retry
    };

    ws.onclose = () => {
      if (!destroyed) scheduleRetry();
    };
  }

  function scheduleRetry() {
    if (destroyed || retries >= maxRetries) return;
    const delay = Math.min(1000 * 2 ** retries, 30_000);
    retries += 1;
    retryTimer = setTimeout(connect, delay);
  }

  connect();

  return {
    close() {
      destroyed = true;
      if (retryTimer) clearTimeout(retryTimer);
      if (ws && (ws.readyState === WebSocket.OPEN || ws.readyState === WebSocket.CONNECTING)) {
        ws.close();
      }
    },
  };
}

// ─── Main dashboard hook ─────────────────────────────────────────────────────

export function useAtlasDashboardData() {
  const queryClient = useQueryClient();
  const [activityEvents, setActivityEvents] = useState<ActivityFeedEntry[]>([]);
  const [incidentStates, setIncidentStates] = useState<Record<string, Record<string, any>>>({});
  const [lastUpdated, setLastUpdated] = useState<Date | null>(null);

  const activeIncidentsQuery = useQuery({
    queryKey: ['atlas', 'active-incidents'],
    queryFn: () => fetchActiveIncidents(),
    refetchInterval: atlasConfig.pollIntervalMs,
    retry: 2,
    retryDelay: (attempt) => Math.min(1000 * 2 ** attempt, 10_000),
  });

  const trustQueries = useQueries({
    queries: knownBackendClientIds.map((clientId) => ({
      queryKey: ['atlas', 'trust', clientId],
      queryFn: () => fetchTrustLevel(clientId),
      refetchInterval: atlasConfig.pollIntervalMs * 3,
      retry: 1,
    })),
  });

  useEffect(() => {
    const sockets: ManagedSocket[] = [];

    const activitySocket = createManagedSocket(
      buildWsUrl('/ws/activity'),
      (payload) => {
        const entry = adaptActivityEvent(payload);
        if (!entry) return;
        setActivityEvents((current) => {
          const withoutDuplicate = current.filter((existing) => existing.id !== entry.id);
          return [entry, ...withoutDuplicate].slice(0, 100);
        });
        setLastUpdated(new Date());
      },
    );
    sockets.push(activitySocket);

    knownBackendClientIds.forEach((clientId) => {
      const incidentSocket = createManagedSocket(
        buildWsUrl(`/ws/incidents/${clientId}`),
        (payload) => {
          if (payload.type === 'active_incidents' && Array.isArray(payload.incidents)) {
            setIncidentStates((current) =>
              payload.incidents.reduce(
                (acc: Record<string, Record<string, any>>, incidentState: Record<string, any>) =>
                  mergeIncidentState(acc, incidentState),
                current,
              ),
            );
            setLastUpdated(new Date());
          }

          if (payload.type === 'new_incident' && payload.thread_id) {
            setIncidentStates((current) => mergeIncidentState(current, payload));
            setLastUpdated(new Date());
          }

          if (payload.type === 'incident_updated' && payload.incident?.thread_id) {
            setIncidentStates((current) => mergeIncidentState(current, payload.incident));
            setLastUpdated(new Date());
          }

          queryClient.invalidateQueries({ queryKey: ['atlas', 'active-incidents'] });
        },
      );
      sockets.push(incidentSocket);
    });

    return () => sockets.forEach((s) => s.close());
  }, [queryClient]);

  useEffect(() => {
    const records = activeIncidentsQuery.data?.incidents;
    if (!records || records.length === 0) return;
    setIncidentStates((current) =>
      records.reduce(
        (acc: Record<string, Record<string, any>>, record) =>
          mergeIncidentState(acc, record as unknown as Record<string, any>),
        current,
      ),
    );
  }, [activeIncidentsQuery.data]);

  const liveIncidents = useMemo(() => {
    const records = activeIncidentsQuery.data?.incidents || [];
    return records.map((record) => adaptActiveIncident(record, incidentStates, fallbackIncidentById));
  }, [activeIncidentsQuery.data, incidentStates]);

  const trustByBackendClient = useMemo(() => {
    const trust: Record<string, number> = {};
    trustQueries.forEach((query) => {
      if (query.data?.client_id) {
        trust[query.data.client_id] = query.data.trust_level;
      }
    });
    return trust;
  }, [trustQueries]);

  const backendConnected = activeIncidentsQuery.isSuccess;

  const incidents: Incident[] = useMemo(() => {
    if (!backendConnected) return mockIncidents;
    return liveIncidents;
  }, [backendConnected, liveIncidents]);

  const clients = useMemo(() => {
    if (!backendConnected && Object.keys(trustByBackendClient).length === 0) return mockClients;
    return buildClientsFromLiveData(mockClients, liveIncidents, trustByBackendClient);
  }, [backendConnected, liveIncidents, trustByBackendClient]);

  const activityFeed = useMemo(() => {
    if (!backendConnected) return mockActivityFeed;
    return activityEvents.slice(0, 80);
  }, [backendConnected, activityEvents]);

  return {
    incidents,
    clients,
    activityFeed,
    backendConnected,
    isLoading: activeIncidentsQuery.isLoading,
    isError: activeIncidentsQuery.isError,
    lastUpdated,
  };
}

export function useAtlasIncidentDetails(threadId: string | undefined, clientId?: string) {
  const detailsQuery = useQuery({
    queryKey: ['atlas', 'incident-details', threadId || 'none', clientId || 'none'],
    queryFn: () => fetchIncidentDetails(threadId || '', clientId),
    enabled: !!threadId,
    refetchInterval: atlasConfig.pollIntervalMs,
    retry: 1,
  });

  return {
    incidentDetails: detailsQuery.data?.incident,
    lastUpdated: detailsQuery.data?.last_updated,
    isLoading: detailsQuery.isLoading,
    isSuccess: detailsQuery.isSuccess,
    isError: detailsQuery.isError,
  };
}

export function useAtlasAuditLog() {
  const auditQuery = useQuery({
    queryKey: ['atlas', 'audit-log'],
    queryFn: async () => {
      const responses = await Promise.allSettled(
        knownBackendClientIds.map((clientId) => fetchAuditLog(clientId)),
      );
      const liveEntries: AuditEntry[] = [];
      let fulfilledCount = 0;

      responses.forEach((response) => {
        if (response.status === 'fulfilled') {
          fulfilledCount += 1;
          liveEntries.push(...response.value.records.map((record) => adaptAuditRecord(record)));
        }
      });

      if (fulfilledCount === 0) return mockAuditLog;
      return sortAuditEntries(liveEntries);
    },
    refetchInterval: atlasConfig.pollIntervalMs * 3,
    retry: 1,
  });

  return {
    auditLog: auditQuery.data || mockAuditLog,
    isLoading: auditQuery.isLoading,
    isError: auditQuery.isError,
  };
}

export function useAtlasClientAudit(frontendClientId: string | undefined, frontendClientName: string | undefined) {
  const backendClientId = frontendClientId ? backendClientIdFromFrontend(frontendClientId) : undefined;

  const clientAuditQuery = useQuery({
    queryKey: ['atlas', 'audit-log', backendClientId || 'fallback'],
    queryFn: async () => {
      if (!backendClientId) {
        return mockAuditLog.filter((entry) => !frontendClientName || entry.client === frontendClientName);
      }
      const response = await fetchAuditLog(backendClientId);
      return sortAuditEntries(response.records.map((record) => adaptAuditRecord(record)));
    },
    refetchInterval: atlasConfig.pollIntervalMs * 3,
    retry: 1,
  });

  const fallback = frontendClientName
    ? mockAuditLog.filter((entry) => entry.client === frontendClientName)
    : mockAuditLog;

  return {
    auditLog: clientAuditQuery.data || fallback,
    isLoading: clientAuditQuery.isLoading,
  };
}

// ─── Approval / Rejection / Modification mutations ───────────────────────────

export function useAtlasApproval() {
  const queryClient = useQueryClient();

  const invalidate = useCallback(() => {
    queryClient.invalidateQueries({ queryKey: ['atlas', 'active-incidents'] });
  }, [queryClient]);

  const approveMutation = useMutation({
    mutationFn: (payload: ApprovalPayload) => approveIncident(payload),
    onSuccess: invalidate,
  });

  const rejectMutation = useMutation({
    mutationFn: (payload: RejectionPayload) => rejectIncident(payload),
    onSuccess: invalidate,
  });

  const modifyMutation = useMutation({
    mutationFn: (payload: ModifyPayload) => modifyIncident(payload),
    onSuccess: invalidate,
  });

  return {
    approve: approveMutation.mutateAsync,
    reject: rejectMutation.mutateAsync,
    modify: modifyMutation.mutateAsync,
    isApproving: approveMutation.isPending,
    isRejecting: rejectMutation.isPending,
    isModifying: modifyMutation.isPending,
    approveError: approveMutation.error,
    rejectError: rejectMutation.error,
    modifyError: modifyMutation.error,
  };
}

// ─── Live log stream per client ──────────────────────────────────────────────

export interface LogLine {
  id: string;
  timestamp: string;
  source: string;
  severity: 'ERROR' | 'WARN' | 'INFO' | 'DEBUG';
  line: string;
  client_id: string;
}

export function useAtlasLogStream(clientId: string | null, maxLines = 200) {
  const [logs, setLogs] = useState<LogLine[]>([]);

  useEffect(() => {
    if (!clientId) return;

    const socket = createManagedSocket(
      buildWsUrl(`/ws/logs/${clientId}`),
      (payload) => {
        if (payload.type === 'log_line') {
          const entry: LogLine = {
            id: `${payload.timestamp || Date.now()}-${Math.random()}`,
            timestamp: payload.timestamp || new Date().toISOString(),
            source: payload.source || 'unknown',
            severity: payload.severity || 'INFO',
            line: payload.line || '',
            client_id: payload.client_id || clientId,
          };
          setLogs((prev) => [entry, ...prev].slice(0, maxLines));
        }
      },
    );

    return () => socket.close();
  }, [clientId, maxLines]);

  return logs;
}

// ─── Trust management (SDM only) ─────────────────────────────────────────────

export function useAtlasTrustManagement() {
  const queryClient = useQueryClient();

  const trustQueries = useQueries({
    queries: knownBackendClientIds.map((clientId) => ({
      queryKey: ['atlas', 'trust-detail', clientId],
      queryFn: () => fetchTrustLevel(clientId),
      refetchInterval: 30_000,
      retry: 1,
    })),
  });

  const confirmUpgradeMutation = useMutation({
    mutationFn: (clientId: string) => confirmTrustUpgrade(clientId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['atlas', 'trust'] });
      queryClient.invalidateQueries({ queryKey: ['atlas', 'trust-detail'] });
    },
  });

  const trustData = trustQueries
    .map((q, i) => ({
      clientId: knownBackendClientIds[i],
      data: q.data,
      isLoading: q.isLoading,
    }))
    .filter((t) => !!t.data);

  return {
    trustData,
    confirmUpgrade: confirmUpgradeMutation.mutateAsync,
    isConfirming: confirmUpgradeMutation.isPending,
    confirmError: confirmUpgradeMutation.error,
  };
}

// ─── Playbook library ────────────────────────────────────────────────────────

export type { PlaybookRecord } from '@/lib/atlas-api';

export function useAtlasPlaybooks() {
  const query = useQuery({
    queryKey: ['atlas', 'playbooks'],
    queryFn: () => fetchPlaybookLibrary(),
    refetchInterval: 60_000,
    retry: 1,
  });

  return {
    playbooks: query.data?.playbooks ?? [],
    isLoading: query.isLoading,
    isError: query.isError,
    backendPlaybooks: query.isSuccess,
  };
}
