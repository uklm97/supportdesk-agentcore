import react from "@vitejs/plugin-react";
import { defineConfig } from "vitest/config";

// `global` is needed by amazon-cognito-identity-js, which was written for Node.
export default defineConfig({
  plugins: [react()],
  define: { global: "globalThis" },
  server: { port: 5173, strictPort: true }, // 5173 is the origin the API's CORS rule allows
  test: { environment: "node", include: ["src/**/*.test.ts"] },
});
