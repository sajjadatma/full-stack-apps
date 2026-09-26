import { execFileSync } from "node:child_process"
import path from "node:path"
import { fileURLToPath } from "node:url"

const __dirname = path.dirname(fileURLToPath(import.meta.url))
const backendDir = path.resolve(__dirname, "../../backend")

/**
 * Ensure the bootstrap superuser and the RBAC seed data exist before the test
 * run. This mirrors the application's own idempotent `init_db` bootstrap, so
 * tests keep working even if the local development superuser was removed
 * through the Admin UI.
 */
export default function globalSetup() {
  execFileSync(
    "uv",
    [
      "run",
      "python",
      "-c",
      "from sqlmodel import Session; from app.core.db import engine, init_db; session = Session(engine); init_db(session); session.close()",
    ],
    {
      cwd: backendDir,
      env: { ...process.env, FASTAPI_ENV: "development" },
      stdio: "inherit",
    },
  )
}
