import { spawnSync } from "node:child_process";
import { readFileSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";

const here = dirname(fileURLToPath(import.meta.url));
const backend = join(here, "..", "..", "backend");
const python = process.platform === "win32"
  ? join(backend, "venv", "Scripts", "python.exe")
  : join(backend, "venv", "bin", "python");

export default function teardown() {
  const script = readFileSync(join(here, "cleanup.py"), "utf8");
  const result = spawnSync(python, ["manage.py", "shell", "-c", script], {
    cwd: backend,
    encoding: "utf8",
  });
  const summary = (result.stdout || "").trim().split("\n").pop();
  if (result.status !== 0) {
    throw new Error(`E2E cleanup failed: ${result.stderr}`);
  }
  console.log(summary);
}
