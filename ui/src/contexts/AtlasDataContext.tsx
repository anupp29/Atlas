/**
 * AtlasDataContext — single source of truth for all dashboard data.
 *
 * Wraps useAtlasDashboardData so WebSocket connections are created ONCE
 * at the app level, not once per component that needs the data.
 * All consumers call useAtlasData() instead of useAtlasDashboardData() directly.
 */
import React, { createContext, useContext } from 'react';
import { useAtlasDashboardData } from '@/hooks/use-atlas-data';
import type { ActivityFeedEntry, Client, Incident } from '@/types/atlas';

interface AtlasDataContextValue {
  incidents: Incident[];
  clients: Client[];
  activityFeed: ActivityFeedEntry[];
  backendConnected: boolean;
  isLoading: boolean;
  isError: boolean;
  lastUpdated: Date | null;
}

const AtlasDataContext = createContext<AtlasDataContextValue | null>(null);

export function AtlasDataProvider({ children }: { children: React.ReactNode }) {
  const data = useAtlasDashboardData();
  return (
    <AtlasDataContext.Provider value={data}>
      {children}
    </AtlasDataContext.Provider>
  );
}

export function useAtlasData(): AtlasDataContextValue {
  const ctx = useContext(AtlasDataContext);
  if (!ctx) throw new Error('useAtlasData must be used within AtlasDataProvider');
  return ctx;
}
