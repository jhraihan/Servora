import { readFileSync, rmSync, writeFileSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";
import { createElement } from "react";
import { renderToStaticMarkup } from "react-dom/server";
import { createServer } from "vite";

const root = join(dirname(fileURLToPath(import.meta.url)), "..");
const dist = join(root, "dist");
const EMPTY_MAIN = /(<main class="[^"]*">)(<\/main>)/;
const PUBLIC_PAGES = [
  "src/pages/Services.jsx",
  "src/pages/ProviderSearch.jsx",
  "src/pages/ProviderProfile.jsx",
  "src/pages/Auth.jsx",
];

function chunksFor(manifest, keys, seen = new Set()) {
  for (const key of keys) {
    const chunk = manifest[key];
    if (!chunk || chunk.isEntry || seen.has(chunk.file)) continue;
    seen.add(chunk.file);
    chunksFor(manifest, chunk.imports ?? [], seen);
  }
  return seen;
}

const shell = readFileSync(join(dist, "index.html"), "utf8");
if (!EMPTY_MAIN.test(shell)) {
  throw new Error("dist/index.html has no empty <main> to prerender into");
}
const manifestDir = join(dist, ".vite");
const manifest = JSON.parse(readFileSync(join(manifestDir, "manifest.json"), "utf8"));
rmSync(manifestDir, { recursive: true });
const preloads = [...chunksFor(manifest, PUBLIC_PAGES)]
  .map((file) => `    <link rel="modulepreload" crossorigin href="/${file}">`)
  .join("\n");
writeFileSync(join(dist, "app.html"), shell.replace("</head>", `${preloads}\n  </head>`));

const vite = await createServer({
  root,
  logLevel: "error",
  appType: "custom",
  server: { middlewareMode: true, hmr: false },
});
try {
  const { default: HomeHero } = await vite.ssrLoadModule("/src/pages/HomeHero.jsx");
  const hero = renderToStaticMarkup(createElement(HomeHero));
  writeFileSync(join(dist, "index.html"), shell.replace(EMPTY_MAIN, `$1${hero}$2`));
  console.log("Prerendered the landing hero into dist/index.html; other routes use dist/app.html.");
} finally {
  await vite.close();
}
