import { readFileSync, realpathSync, writeFileSync } from "node:fs";
import { createRequire } from "node:module";
import path from "node:path";
import { defineConfig } from "vitest/config";

const outputDirectory = process.env.C1_SIDECAR_RUNTIME_EVIDENCE_DIR;
const phase = process.env.C1_SIDECAR_RUNTIME_PHASE;
if (outputDirectory !== "/evidence" || !["dry-run", "mutation"].includes(phase)) {
  throw new Error("SIDECAR_RESOLUTION_FAILED:RUNTIME_EVIDENCE_ENV");
}

const localRequire = createRequire(import.meta.url);
const packagePath = localRequire.resolve("vitest/package.json");
const nodePath = localRequire.resolve("vitest/node");
const packageRealpath = realpathSync(packagePath);
const nodeRealpath = realpathSync(nodePath);
const expectedPrefix = `/consumer/node_modules${path.sep}`;
if (!packageRealpath.startsWith(expectedPrefix) || !nodeRealpath.startsWith(expectedPrefix)) {
  throw new Error(
    `SIDECAR_RESOLUTION_FAILED:ACTIVE_VITEST_OUTSIDE_CONSUMER:${packageRealpath}:${nodeRealpath}`,
  );
}

const packageJson = JSON.parse(readFileSync(packagePath, "utf8"));
if (packageJson.version !== "4.0.18") {
  throw new Error(`SIDECAR_RESOLUTION_FAILED:ACTIVE_VITEST_VERSION:${packageJson.version}`);
}

writeFileSync(
  `${outputDirectory}/vitest-runtime-resolution-${phase}-${process.pid}.json`,
  `${JSON.stringify(
    {
      schema: "c1-stryker-sidecar-runtime-resolution.v1",
      phase,
      pid: process.pid,
      cwd: process.cwd(),
      config_url: import.meta.url,
      vitest_version: packageJson.version,
      vitest_package_path: packagePath,
      vitest_package_realpath: packageRealpath,
      vitest_node_path: nodePath,
      vitest_node_realpath: nodeRealpath,
    },
    null,
    2,
  )}\n`,
  "utf8",
);

export default defineConfig({
  test: {
    include: ["src/__tests__/validator-probe-fixture.test.ts"],
  },
});
