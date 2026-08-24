import { createHash } from "node:crypto";
import { readFileSync } from "node:fs";

const expectedCwd = "/consumer";
const pluginEntry = "/tool/node_modules/@stryker-mutator/vitest-runner/dist/src/index.js";
const pluginSha256 = "094dfe20dc1e057ee6fb40deecd1693ca85ad8aa0aa905407fe7158fff5a1998";

if (process.cwd() !== expectedCwd) {
  throw new Error(`SIDECAR_RESOLUTION_FAILED:ENTRY_CWD:${process.cwd()}`);
}
const actualPluginSha256 = createHash("sha256").update(readFileSync(pluginEntry)).digest("hex");
if (actualPluginSha256 !== pluginSha256) {
  throw new Error(`SIDECAR_RESOLUTION_FAILED:PLUGIN_SHA256:${actualPluginSha256}`);
}

const rangesText = process.env.C1_SIDECAR_MUTATE_RANGES_JSON;
if (!rangesText) {
  throw new Error("C1_SIDECAR_MUTATE_RANGES_JSON is required");
}
const mutate = JSON.parse(rangesText);
if (!Array.isArray(mutate) || mutate.length === 0 || mutate.some((value) => typeof value !== "string")) {
  throw new Error("C1_SIDECAR_MUTATE_RANGES_JSON must be a non-empty JSON string array");
}

const dryRunOnly = process.env.C1_SIDECAR_DRY_RUN_ONLY === "1";

export default {
  plugins: [pluginEntry],
  testRunner: "vitest",
  mutate,
  vitest: {
    configFile: "vitest.sidecar-probe.config.mjs",
    related: true,
  },
  reporters: dryRunOnly ? ["clear-text"] : ["clear-text", "json"],
  jsonReporter: {
    fileName: "/evidence/sidecar-mutation-report.json",
  },
  dryRunOnly,
  dryRunTimeoutMinutes: 2,
  timeoutMS: 10000,
  timeoutFactor: 1.5,
  concurrency: 1,
  allowConsoleColors: false,
  allowEmpty: false,
  disableTypeChecks: true,
  cleanTempDir: true,
  tempDirName: ".stryker-tmp-c1-sidecar-probe",
  symlinkNodeModules: true,
  fileLogLevel: "off",
  logLevel: "info",
  thresholds: {
    high: 80,
    low: 60,
    break: null,
  },
  ignorePatterns: [
    "artifacts/**",
    "docs/**",
    "memory/**",
    ".next/**",
  ],
};
