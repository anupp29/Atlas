/// <reference types="vite/client" />

interface ImportMetaEnv {
	readonly VITE_ATLAS_API_BASE_URL?: string;
	readonly VITE_ATLAS_WS_BASE_URL?: string;
	readonly VITE_ATLAS_POLL_INTERVAL_MS?: string;
	readonly VITE_ATLAS_DEFAULT_CLIENT_ID?: string;
}

interface ImportMeta {
	readonly env: ImportMetaEnv;
}
