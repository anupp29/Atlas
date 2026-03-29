const DEFAULT_API_BASE_URL = 'http://localhost:8000';
const DEFAULT_POLL_INTERVAL_MS = 10000;
const DEFAULT_CLIENT_ID = 'FINCORE_UK_001';

function trimTrailingSlash(url: string): string {
  return url.replace(/\/+$/, '');
}

function deriveWebSocketBaseUrl(apiBaseUrl: string): string {
  try {
    const parsed = new URL(apiBaseUrl);
    parsed.protocol = parsed.protocol === 'https:' ? 'wss:' : 'ws:';
    return trimTrailingSlash(parsed.toString());
  } catch {
    return 'ws://localhost:8000';
  }
}

function parsePollInterval(rawValue: string | undefined): number {
  if (!rawValue) return DEFAULT_POLL_INTERVAL_MS;
  const parsed = Number(rawValue);
  if (!Number.isFinite(parsed) || parsed < 1000) return DEFAULT_POLL_INTERVAL_MS;
  return Math.floor(parsed);
}

const apiBaseUrl = trimTrailingSlash(import.meta.env.VITE_ATLAS_API_BASE_URL || DEFAULT_API_BASE_URL);
const wsBaseUrl = trimTrailingSlash(import.meta.env.VITE_ATLAS_WS_BASE_URL || deriveWebSocketBaseUrl(apiBaseUrl));

export const atlasConfig = {
  apiBaseUrl,
  wsBaseUrl,
  pollIntervalMs: parsePollInterval(import.meta.env.VITE_ATLAS_POLL_INTERVAL_MS),
  defaultClientId: import.meta.env.VITE_ATLAS_DEFAULT_CLIENT_ID || DEFAULT_CLIENT_ID,
};
