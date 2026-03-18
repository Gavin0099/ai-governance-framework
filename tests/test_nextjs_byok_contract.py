"""
Integration tests for examples/nextjs-byok-contract.

Covers:
  - ByokKeyPropagationValidator unit behaviour
  - RouteRateLimitValidator unit behaviour
  - contract.yaml loads via domain_contract_loader
  - run_validators.py CLI: fixture pass/advisory-warn behaviour
"""
import importlib.util
import json
import subprocess
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))

# ── Paths ─────────────────────────────────────────────────────────────────────

EXAMPLE_DIR = Path("examples/nextjs-byok-contract")
CONTRACT_FILE = EXAMPLE_DIR / "contract.yaml"
BYOK_VALIDATOR_PATH = EXAMPLE_DIR / "validators" / "byok_key_propagation_validator.py"
RATE_VALIDATOR_PATH = EXAMPLE_DIR / "validators" / "route_rate_limit_validator.py"
FIXTURE_BYOK_COMPLIANT = EXAMPLE_DIR / "fixtures" / "ingest_byok_compliant.checks.json"
FIXTURE_BYOK_VIOLATION = EXAMPLE_DIR / "fixtures" / "ingest_byok_violation.checks.json"
FIXTURE_RATE_COMPLIANT = EXAMPLE_DIR / "fixtures" / "rate_limit_compliant.checks.json"
FIXTURE_RATE_VIOLATION = EXAMPLE_DIR / "fixtures" / "rate_limit_violation.checks.json"
RUN_VALIDATORS = EXAMPLE_DIR / "run_validators.py"


# ── Loader helpers ────────────────────────────────────────────────────────────

def _load_class(module_path: Path, class_name: str):
    spec = importlib.util.spec_from_file_location(module_path.stem, str(module_path.resolve()))
    mod = importlib.util.module_from_spec(spec)          # type: ignore[arg-type]
    spec.loader.exec_module(mod)                         # type: ignore[union-attr]
    return getattr(mod, class_name)


def _run_cli(*args):
    return subprocess.run(
        [sys.executable, str(RUN_VALIDATORS.resolve()), *args],
        cwd=Path(".").resolve(),
        capture_output=True,
        text=True,
        check=False,
    )


# ── ByokKeyPropagationValidator ───────────────────────────────────────────────

class TestByokKeyPropagationValidator:
    @pytest.fixture(autouse=True)
    def validator(self):
        cls = _load_class(BYOK_VALIDATOR_PATH, "ByokKeyPropagationValidator")
        self.v = cls()

    def _run(self, file_path, source_code, api_roots=None):
        payload = {"file_path": file_path, "source_code": source_code}
        if api_roots is not None:
            payload["api_route_roots"] = api_roots
        return self.v.validate(payload)

    # ── Files outside api_route_roots ─────────────────────────────────────────

    def test_lib_file_skipped(self):
        result = self._run(
            "lib/embeddings.ts",
            "export async function generateEmbedding(text: string) { return []; }",
        )
        assert result.ok is True
        assert result.violations == []
        assert result.metadata["in_api"] is False

    def test_non_ingest_api_route_skipped(self):
        result = self._run(
            "src/app/api/query/route.ts",
            "export async function POST() { const e = await generateEmbedding('x'); }",
        )
        assert result.ok is True
        assert result.violations == []
        assert result.metadata.get("is_ingest") is False

    # ── Compliant ingest routes ───────────────────────────────────────────────

    def test_ingest_with_user_key_passes(self):
        source = (
            "const userKey = session.user.openaiKey;\n"
            "const embedding = await generateEmbedding(text, { apiKey: userKey });\n"
        )
        result = self._run("src/app/api/ingest/route.ts", source)
        assert result.ok is True

    def test_ingest_with_session_user_key_passes(self):
        """session?.user.openaiKey is a specific key reference — not an auth guard."""
        source = (
            "const session = await getServerSession();\n"
            "const embedding = await generateEmbedding(text, session?.user.openaiKey);\n"
        )
        result = self._run("src/app/api/ingest/route.ts", source)
        assert result.ok is True

    def test_ingest_with_openai_api_key_var_passes(self):
        source = "const embedding = await generateEmbedding(text, openaiApiKey);\n"
        result = self._run("src/app/api/ingest/route.ts", source)
        assert result.ok is True

    def test_ingest_no_embedding_call_passes(self):
        source = "export async function POST() { return new Response('ok'); }\n"
        result = self._run("src/app/api/ingest/route.ts", source)
        assert result.ok is True

    def test_embedding_in_comment_no_fp(self):
        """// generateEmbedding(text) in comment — must not trigger."""
        source = (
            "// TODO: call generateEmbedding(text) with user key later\n"
            "export async function POST() { return new Response('stub'); }\n"
        )
        result = self._run("src/app/api/ingest/route.ts", source)
        assert result.ok is True

    # ── Violation ─────────────────────────────────────────────────────────────

    def test_ingest_without_user_key_detected(self):
        source = (
            "const embedding = await generateEmbedding(text);\n"
            "// no user key passed\n"
        )
        result = self._run("src/app/api/ingest/route.ts", source)
        assert result.ok is False
        assert len(result.violations) == 1
        assert "BYOK_INGEST_KEY_PROPAGATION" in result.violations[0]
        assert result.metadata["is_ingest"] is True

    def test_ingest_batch_path_also_detected(self):
        source = "const emb = await generateEmbedding(entry.content);\n"
        result = self._run("src/app/api/ingest-batch/route.ts", source)
        assert result.ok is False

    def test_windows_path_normalised(self):
        source = "const emb = await generateEmbedding(text);\n"
        result = self._run(r"src\app\api\ingest\route.ts", source)
        assert result.ok is False

    def test_custom_api_roots_respected(self):
        source = "const emb = await generateEmbedding(text);\n"
        result_skip = self._run(
            "src/app/api/ingest/route.ts", source,
            api_roots=["pages/api/"],
        )
        assert result_skip.ok is True

        result_detect = self._run(
            "src/app/api/ingest/route.ts", source,
            api_roots=["src/app/api/"],
        )
        assert result_detect.ok is False

    def test_rule_ids_always_present(self):
        result = self._run("lib/clean.ts", "export const x = 1;")
        assert "BYOK_INGEST_KEY_PROPAGATION" in result.rule_ids

    def test_advisory_mode_in_metadata(self):
        result = self._run("src/app/api/ingest/route.ts", "export const x = 1;")
        assert result.metadata.get("mode") == "advisory"


# ── RouteRateLimitValidator ───────────────────────────────────────────────────

class TestRouteRateLimitValidator:
    @pytest.fixture(autouse=True)
    def validator(self):
        cls = _load_class(RATE_VALIDATOR_PATH, "RouteRateLimitValidator")
        self.v = cls()

    def _run(self, file_path, source_code, api_roots=None):
        payload = {"file_path": file_path, "source_code": source_code}
        if api_roots is not None:
            payload["api_route_roots"] = api_roots
        return self.v.validate(payload)

    # ── Files outside api_route_roots ─────────────────────────────────────────

    def test_lib_file_skipped(self):
        result = self._run("lib/utils.ts", "export function add(a: number, b: number) { return a + b; }")
        assert result.ok is True
        assert result.metadata["in_api"] is False

    # ── No mutation handler ───────────────────────────────────────────────────

    def test_get_only_route_skipped(self):
        source = "export async function GET() { return Response.json({ ok: true }); }\n"
        result = self._run("src/app/api/health/route.ts", source)
        assert result.ok is True
        assert result.metadata.get("has_mutation") is False

    # ── Compliant mutation handlers ───────────────────────────────────────────

    def test_post_with_ratelimit_passes(self):
        source = (
            "import { Ratelimit } from '@upstash/ratelimit';\n"
            "const ratelimit = new Ratelimit({ ... });\n"
            "export async function POST(req: Request) {\n"
            "  const { success } = await ratelimit.limit(userId);\n"
            "  if (!success) return new Response('Too Many Requests', { status: 429 });\n"
            "}\n"
        )
        result = self._run("src/app/api/ingest/route.ts", source)
        assert result.ok is True

    def test_post_with_rate_limit_function_passes(self):
        source = (
            "import { withRateLimit } from '@/lib/rate-limit';\n"
            "export async function POST(req: Request) { ... }\n"
        )
        result = self._run("src/app/api/query/route.ts", source)
        assert result.ok is True

    def test_pages_router_handler_with_rate_limit_passes(self):
        source = (
            "import { rateLimiter } from '@/lib/rate-limit';\n"
            "export default async function handler(req, res) {\n"
            "  await rateLimiter.check(req);\n"
            "  res.json({ ok: true });\n"
            "}\n"
        )
        result = self._run("pages/api/ingest.ts", source)
        assert result.ok is True

    def test_rate_limit_in_comment_not_counted(self):
        """Commenting out rate limiting should still trigger the violation."""
        source = (
            "// const { success } = await ratelimit.limit(userId);\n"
            "export async function POST(req: Request) { return Response.json({}); }\n"
        )
        result = self._run("src/app/api/ingest/route.ts", source)
        assert result.ok is False

    # ── Violations ────────────────────────────────────────────────────────────

    def test_post_without_rate_limit_detected(self):
        source = "export async function POST(req: Request) { return Response.json({ ok: true }); }\n"
        result = self._run("src/app/api/ingest/route.ts", source)
        assert result.ok is False
        assert "ROUTE_RATE_LIMIT_COVERAGE" in result.violations[0]
        assert result.metadata["has_mutation"] is True

    def test_delete_without_rate_limit_detected(self):
        source = "export const DELETE = async (req: Request) => Response.json({ deleted: true });\n"
        result = self._run("src/app/api/entries/route.ts", source)
        assert result.ok is False

    def test_put_without_rate_limit_detected(self):
        source = "export async function PUT(req: Request) { return Response.json({ updated: true }); }\n"
        result = self._run("src/app/api/settings/route.ts", source)
        assert result.ok is False

    def test_rule_ids_always_present(self):
        result = self._run("lib/clean.ts", "export const x = 1;")
        assert "ROUTE_RATE_LIMIT_COVERAGE" in result.rule_ids


# ── Contract loader ───────────────────────────────────────────────────────────

def test_nextjs_byok_contract_loads():
    from governance_tools.domain_contract_loader import load_domain_contract
    loaded = load_domain_contract(CONTRACT_FILE)
    assert loaded is not None
    assert loaded["name"] == "nextjs-byok"
    assert len(loaded["validators"]) == 2
    names = {v["name"] for v in loaded["validators"]}
    assert "byok_key_propagation_validator" in names
    assert "route_rate_limit_validator" in names


# ── CLI integration tests ─────────────────────────────────────────────────────

def test_byok_compliant_fixture_exit_zero():
    proc = _run_cli(str(FIXTURE_BYOK_COMPLIANT.resolve()), "--json")
    assert proc.returncode == 0
    result = json.loads(proc.stdout)
    assert result["overall_pass"] is True


def test_byok_violation_fixture_advisory_exit_zero():
    """Violation detected but advisory — exit 0, ok=False, hard_stop=False."""
    proc = _run_cli(str(FIXTURE_BYOK_VIOLATION.resolve()), "--json")
    assert proc.returncode == 0
    result = json.loads(proc.stdout)
    assert result["overall_pass"] is True
    byok_results = [
        r for f in result["fixtures"]
        for r in f["results"]
        if r["validator"] == "byok_key_propagation_validator"
    ]
    assert byok_results[0]["ok"] is False
    assert byok_results[0]["hard_stop"] is False
    assert any("BYOK_INGEST_KEY_PROPAGATION" in v for v in byok_results[0]["violations"])


def test_rate_limit_compliant_fixture_passes():
    proc = _run_cli(str(FIXTURE_RATE_COMPLIANT.resolve()), "--json")
    assert proc.returncode == 0
    result = json.loads(proc.stdout)
    assert result["overall_pass"] is True


def test_rate_limit_violation_fixture_advisory():
    proc = _run_cli(str(FIXTURE_RATE_VIOLATION.resolve()), "--json")
    assert proc.returncode == 0
    result = json.loads(proc.stdout)
    assert result["overall_pass"] is True
    rate_results = [
        r for f in result["fixtures"]
        for r in f["results"]
        if r["validator"] == "route_rate_limit_validator"
    ]
    assert rate_results[0]["ok"] is False
    assert rate_results[0]["hard_stop"] is False


def test_all_fixtures_advisory_exit_zero():
    proc = _run_cli(str((EXAMPLE_DIR / "fixtures").resolve()), "--json")
    assert proc.returncode == 0
    result = json.loads(proc.stdout)
    assert result["overall_pass"] is True
    assert len(result["fixtures"]) == 4


def test_json_flag_routes_text_to_stderr():
    proc = _run_cli(str(FIXTURE_BYOK_VIOLATION.resolve()), "--json")
    assert proc.stderr  # text output goes to stderr
    json.loads(proc.stdout)  # stdout is valid JSON


def test_no_fixtures_error():
    proc = _run_cli(str((EXAMPLE_DIR / "rules").resolve()))
    assert proc.returncode == 2
