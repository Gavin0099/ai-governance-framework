const rangesText = process.env.C1_PROBE_MUTATE_RANGES_JSON;
if (!rangesText) {
  throw new Error("C1_PROBE_MUTATE_RANGES_JSON is required");
}

const mutate = JSON.parse(rangesText);
if (!Array.isArray(mutate) || mutate.length === 0 || mutate.some((value) => typeof value !== "string")) {
  throw new Error("C1_PROBE_MUTATE_RANGES_JSON must be a non-empty JSON string array");
}

const dryRunOnly = process.env.C1_PROBE_DRY_RUN_ONLY === "1";

export default {
  testRunner: "vitest",
  mutate,
  vitest: {
    configFile: "vitest.config.ts",
    related: true,
  },
  reporters: dryRunOnly ? ["clear-text"] : ["clear-text", "json"],
  jsonReporter: {
    fileName: "reports/c1-validator-probe-mutation.json",
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
  tempDirName: ".stryker-tmp-c1-validator-probe",
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
    "ai-governance-framework/**",
    ".next/**",
  ],
};
