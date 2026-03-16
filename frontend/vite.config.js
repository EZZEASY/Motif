import { defineConfig } from "vite";

export default defineConfig({
  server: {
    port: 5173,
    proxy: {
      "/ws": {
        target: "http://127.0.0.1:8001",
        ws: true,
      },
      "/animations": {
        target: "http://127.0.0.1:8001",
      },
      "/api": {
        target: "http://127.0.0.1:8001",
      },
      "/characters": {
        target: "http://127.0.0.1:8001",
      },
    },
  },
});
