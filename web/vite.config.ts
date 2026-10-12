import { defineConfig } from "vite";

export default defineConfig({
  // 出力するファイルを相対パスで参照する（GitHub Pages のサブパスでも S3 でも同じビルドで動く）
  base: "./",
  server: {
    host: "127.0.0.1",
    port: 5173,
    strictPort: true,
    // 開発中は /api/... をローカルの API（python -m tech_digest.api.devserver）に中継する。
    // ブラウザから見ると同じオリジンへのリクエストになるので、CORS の設定が要らない。
    // 本番では VITE_API_BASE_URL（API Gateway の URL）を直接呼ぶ（src/api.ts）
    proxy: {
      "/api": {
        target: "http://127.0.0.1:8080",
        rewrite: (path) => path.replace(/^\/api/, ""),
      },
    },
  },
});
