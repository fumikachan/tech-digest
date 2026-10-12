/// <reference types="vite/client" />

// ビルド時に埋め込む環境変数（VITE_ で始まるものだけがブラウザ側のコードに入る。秘密の値は置かない）
interface ImportMetaEnv {
  // API のベース URL（例: https://xxxx.execute-api.ap-northeast-1.amazonaws.com）。
  // なければ /api（開発サーバーがローカルの API に中継する）
  readonly VITE_API_BASE_URL?: string;
}

interface ImportMeta {
  readonly env: ImportMetaEnv;
}
