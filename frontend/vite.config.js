import { defineConfig, loadEnv } from "vite";
import react from "@vitejs/plugin-react";
import tailwindcss from "@tailwindcss/vite";

function landingPageRouting() {
  return {
    name: "landing-page-routing",
    configurePreviewServer(server) {
      server.middlewares.use((req, _res, next) => {
        const path = req.url.split("?")[0];
        const isPage = req.headers.accept?.includes("text/html") && !path.includes(".");
        if (isPage && path !== "/") req.url = "/app.html";
        next();
      });
    },
  };
}

export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, process.cwd(), "");
  const backend = env.BACKEND_URL || "http://127.0.0.1:8000";

  return {
    plugins: [react(), tailwindcss(), landingPageRouting()],
    build: { manifest: true },
    server: {
      port: 5173,
      proxy: {
        "/api": { target: backend, changeOrigin: true },
        "/media": { target: backend, changeOrigin: true },
      },
    },
    test: {
      environment: "jsdom",
      globals: true,
      setupFiles: ["./src/test/setup.js"],
      include: ["src/**/*.test.{js,jsx}"],
      css: false,
    },
  };
});
