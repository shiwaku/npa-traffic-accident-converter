/// <reference types="vite/client" />
/// <reference types="vite-plugin-pwa/client" />

interface ImportMetaEnv {
  /** 事故データ PMTiles のURL（未指定なら dev server の /data/ から取得） */
  readonly VITE_PMTILES_URL?: string;
}
