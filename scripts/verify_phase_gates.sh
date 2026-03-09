#!/bin/bash
# verify_phase_gates.sh — 驗證 Phase Gate 條件
#
# 用法:
#   bash scripts/verify_phase_gates.sh
#
# 退出碼:
#   0 = 全部 Gate 通過
#   1 = 至少一項 Gate 未通過
#
# 用途:
#   讓 Phase 完成的宣告從「人工 [✓]」變成「機器可驗證」。
#   建議在 git push 前或 CI 中執行。

set -euo pipefail

PASS=0
FAIL=0

ok()   { echo "  ✅ $1"; }
fail() { echo "  ❌ $1"; FAIL=$((FAIL + 1)); }
info() { echo ""; echo "── $1 ──────────────────────────────"; }

echo "╔══════════════════════════════════════════╗"
echo "║   Phase Gate Verification                ║"
echo "╚══════════════════════════════════════════╝"

# ── Gate 1: 單元測試 ─────────────────────────────────────────
info "Gate 1 / 單元測試"
if python -m pytest tests/ -q --tb=short 2>&1; then
    ok "pytest 通過"
    PASS=$((PASS + 1))
else
    fail "pytest 失敗 — 請修復後再宣告 Phase 完成"
fi

# ── Gate 2: PLAN.md 新鮮度 ───────────────────────────────────
info "Gate 2 / PLAN.md 新鮮度"
PLAN_OUTPUT=$(python governance_tools/plan_freshness.py --format json) || true
PLAN_STATUS=$(echo "$PLAN_OUTPUT" | python3 -c \
    "import json,sys; r=json.load(sys.stdin); print(r['status'])")
PLAN_DAYS=$(echo "$PLAN_OUTPUT" | python3 -c \
    "import json,sys; r=json.load(sys.stdin); print(r.get('days_since_update','?'))")

if [ "$PLAN_STATUS" = "CRITICAL" ] || [ "$PLAN_STATUS" = "ERROR" ]; then
    fail "PLAN.md $PLAN_STATUS (${PLAN_DAYS}d) — 請更新後再宣告完成"
elif [ "$PLAN_STATUS" = "STALE" ]; then
    echo "  ⚠️  PLAN.md STALE (${PLAN_DAYS}d) — 建議更新，但不阻擋"
    ok "Gate 通過（警告）"
    PASS=$((PASS + 1))
else
    ok "PLAN.md $PLAN_STATUS (${PLAN_DAYS}d)"
    PASS=$((PASS + 1))
fi

# ── Gate 3: Governance tools 可執行 ─────────────────────────
info "Gate 3 / 工具可執行性"
TOOLS=(
    "contract_validator.py"
    "plan_freshness.py"
    "memory_janitor.py"
    "state_generator.py"
)
ALL_OK=1
for tool in "${TOOLS[@]}"; do
    if python "governance_tools/$tool" --help > /dev/null 2>&1; then
        ok "$tool"
    else
        fail "$tool --help 失敗"
        ALL_OK=0
    fi
done
if [ "$ALL_OK" -eq 1 ]; then
    PASS=$((PASS + 1))
fi

# ── Gate 4: 治理文件完整性 ───────────────────────────────────
info "Gate 4 / 治理文件完整性"
DOCS=(
    "governance/SYSTEM_PROMPT.md"
    "governance/AGENT.md"
    "governance/ARCHITECTURE.md"
    "governance/HUMAN-OVERSIGHT.md"
    "governance/REVIEW_CRITERIA.md"
    "governance/TESTING.md"
    "governance/NATIVE-INTEROP.md"
    "governance/PLAN.md"
    "PLAN.md"
)
DOCS_OK=1
for doc in "${DOCS[@]}"; do
    if [ -f "$doc" ]; then
        ok "$doc 存在"
    else
        fail "$doc 缺失"
        DOCS_OK=0
    fi
done
if [ "$DOCS_OK" -eq 1 ]; then
    PASS=$((PASS + 1))
fi

# ── 摘要 ─────────────────────────────────────────────────────
echo ""
echo "══════════════════════════════════════════"
TOTAL=$((PASS + FAIL))
echo "  結果: ${PASS}/${TOTAL} Gates 通過"

if [ "$FAIL" -eq 0 ]; then
    echo "  🎉 全部通過 — Phase 完成條件滿足"
    exit 0
else
    echo "  🚨 $FAIL 項未通過 — 請修復後再宣告 Phase 完成"
    exit 1
fi
