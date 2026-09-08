import { spawnSync } from "node:child_process";
import { createHash } from "node:crypto";
import { readFileSync } from "node:fs";

const consumerRoot = "/consumer";

function sha256Bytes(bytes) {
  return createHash("sha256").update(bytes).digest("hex");
}

function sha256File(relativePath) {
  return sha256Bytes(readFileSync(`${consumerRoot}/${relativePath}`));
}

function canonicalize(value) {
  if (Array.isArray(value)) {
    return value.map(canonicalize);
  }
  if (value !== null && typeof value === "object") {
    return Object.fromEntries(
      Object.keys(value)
        .sort()
        .map((key) => [key, canonicalize(value[key])]),
    );
  }
  return value;
}

if (process.cwd() !== consumerRoot) {
  throw new Error(`CONSUMER_GRAPH_CHANGED:FINGERPRINT_CWD:${process.cwd()}`);
}

const npmLs = spawnSync("npm", ["ls", "--all", "--json"], {
  cwd: consumerRoot,
  encoding: "utf8",
  windowsHide: true,
});
if (npmLs.error || npmLs.status === null) {
  throw new Error(`CONSUMER_GRAPH_CHANGED:NPM_LS_START:${npmLs.error?.message ?? "unknown"}`);
}

let npmLsJson;
try {
  npmLsJson = JSON.parse(npmLs.stdout);
} catch (error) {
  throw new Error(`CONSUMER_GRAPH_CHANGED:NPM_LS_JSON:${error.message}`);
}
const npmLsCanonical = `${JSON.stringify(canonicalize(npmLsJson))}\n`;

console.log(
  JSON.stringify(
    {
      schema: "c1-stryker-sidecar-consumer-graph.v1",
      consumer_root: consumerRoot,
      package_json_sha256: sha256File("package.json"),
      package_lock_sha256: sha256File("package-lock.json"),
      node_modules_package_lock_sha256: sha256File("node_modules/.package-lock.json"),
      npm_ls_exit_code: npmLs.status,
      npm_ls_canonical_sha256: sha256Bytes(Buffer.from(npmLsCanonical, "utf8")),
      npm_ls_stderr_sha256: sha256Bytes(Buffer.from(npmLs.stderr, "utf8")),
    },
    null,
    2,
  ),
);
