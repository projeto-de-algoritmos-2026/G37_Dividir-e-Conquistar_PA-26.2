import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

// host 127.0.0.1 + porta 5500 para bater exatamente com o README e o run.py
// (no macOS "localhost" pode virar IPv6 ::1 e nao atender em 127.0.0.1)
export default defineConfig({
  plugins: [react()],
  server: { host: "127.0.0.1", port: 5500 },
});
