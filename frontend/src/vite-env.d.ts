/// <reference types="vite/client" />

interface ImportMetaEnv {
  readonly VITE_API_BASE_URL?: string;
  readonly VITE_EVENT_TITLE?: string;
  readonly VITE_EVENT_SUBTITLE?: string;
  readonly VITE_BRAND_NAME?: string;
  readonly VITE_PIN_FAIL_REDIRECT_URL?: string;
}

interface ImportMeta {
  readonly env: ImportMetaEnv;
}
