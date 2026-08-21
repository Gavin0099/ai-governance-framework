import { createHash } from "node:crypto";
import { readFileSync, realpathSync } from "node:fs";
import { createRequire } from "node:module";
import path from "node:path";
import { pathToFileURL } from "node:url";

const expectedCwd = "/consumer";
const toolRoot = "/tool";
const bindingPath = "/probe-input/plugin-entry-binding.json";

function fail(message) {
  throw new Error(`SIDECAR_RESOLUTION_FAILED:${message}`);
}

function sha256(filePath) {
  return createHash("sha256").update(readFileSync(filePath)).digest("hex");
}

function requireUnder(actualPath, root, label) {
  const real = realpathSync(actualPath);
  const prefix = `${root}${path.sep}`;
  if (real !== root && !real.startsWith(prefix)) {
    fail(`${label}_OUTSIDE_${root}:${real}`);
  }
  return real;
}

if (process.cwd() !== expectedCwd) {
  fail(`ENTRY_CWD:${process.cwd()}`);
}

const binding = JSON.parse(readFileSync(bindingPath, "utf8"));
const consumerRequire = createRequire("/consumer/package.json");
const toolRequire = createRequire("/tool/package.json");

const corePackage = toolRequire.resolve("@stryker-mutator/core/package.json");
const runnerPackage = toolRequire.resolve("@stryker-mutator/vitest-runner/package.json");
const pluginEntry = toolRequire.resolve("@stryker-mutator/vitest-runner");
const toolVitestPackage = toolRequire.resolve("vitest/package.json");
const consumerVitestPackage = consumerRequire.resolve("vitest/package.json");
const consumerVitestNode = consumerRequire.resolve("vitest/node");

const core = JSON.parse(readFileSync(corePackage, "utf8"));
const runner = JSON.parse(readFileSync(runnerPackage, "utf8"));
const toolVitest = JSON.parse(readFileSync(toolVitestPackage, "utf8"));
const consumerVitest = JSON.parse(readFileSync(consumerVitestPackage, "utf8"));

if (core.version !== "10.0.0" || runner.version !== "10.0.0") {
  fail("TOOL_VERSION");
}
if (toolVitest.version !== "4.0.18" || consumerVitest.version !== "4.0.18") {
  fail("VITEST_VERSION");
}

const actual = {
  core_package_realpath: requireUnder(corePackage, toolRoot, "CORE"),
  plugin_package_realpath: requireUnder(runnerPackage, toolRoot, "PLUGIN_PACKAGE"),
  plugin_entry_realpath: requireUnder(pluginEntry, toolRoot, "PLUGIN_ENTRY"),
  tool_vitest_package_realpath: requireUnder(toolVitestPackage, toolRoot, "TOOL_VITEST"),
  consumer_vitest_package_realpath: requireUnder(
    consumerVitestPackage,
    "/consumer/node_modules",
    "CONSUMER_VITEST_PACKAGE",
  ),
  consumer_vitest_node_realpath: requireUnder(
    consumerVitestNode,
    "/consumer/node_modules",
    "CONSUMER_VITEST_NODE",
  ),
};

if (pluginEntry !== binding.plugin.entry_path) {
  fail(`PLUGIN_ENTRY_PATH:${pluginEntry}`);
}
if (sha256(pluginEntry) !== binding.plugin.entry_sha256) {
  fail("PLUGIN_ENTRY_SHA256");
}
if (sha256(binding.core.cli_path) !== binding.core.cli_sha256) {
  fail("CORE_CLI_SHA256");
}

const pluginModule = await import(pathToFileURL(pluginEntry).href);
const consumerVitestNodeModule = await import(pathToFileURL(consumerVitestNode).href);
if (!Array.isArray(pluginModule.strykerPlugins) || pluginModule.strykerPlugins.length === 0) {
  fail("PLUGIN_EXPORT");
}
if (typeof consumerVitestNodeModule.createVitest !== "function") {
  fail("CONSUMER_CREATE_VITEST_EXPORT");
}

console.log(
  JSON.stringify(
    {
      schema: "c1-stryker-sidecar-resolution.v1",
      entry_cwd: process.cwd(),
      core: { version: core.version, package_path: corePackage, realpath: actual.core_package_realpath },
      plugin: {
        version: runner.version,
        package_path: runnerPackage,
        entry_path: pluginEntry,
        entry_sha256: sha256(pluginEntry),
        realpath: actual.plugin_entry_realpath,
        exports_stryker_plugins: true,
      },
      tool_vitest: {
        version: toolVitest.version,
        package_path: toolVitestPackage,
        realpath: actual.tool_vitest_package_realpath,
      },
      consumer_vitest: {
        version: consumerVitest.version,
        package_path: consumerVitestPackage,
        package_realpath: actual.consumer_vitest_package_realpath,
        node_path: consumerVitestNode,
        node_realpath: actual.consumer_vitest_node_realpath,
        exports_create_vitest: true,
      },
    },
    null,
    2,
  ),
);
