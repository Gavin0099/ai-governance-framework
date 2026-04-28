#!/bin/bash
# 一鍵部署治理架構到目標專案
# 用法: ./deploy_to_memory.sh [目標專案路徑]
#       省略路徑時使用當前目錄

set -e

# 取得腳本所在目錄 (ai-governance-framework repo)
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# 目標專案路徑 (預設: 當前目錄)
TARGET="${1:-$(pwd)}"

echo "🚀 開始部署治理架構..."
echo "   來源: $SCRIPT_DIR"
echo "   目標: $TARGET"
echo ""

# 確認目標目錄存在
if [ ! -d "$TARGET" ]; then
    echo "❌ 錯誤: 目標目錄不存在: $TARGET"
    exit 1
fi

# 確認來源 governance/ 存在
if [ ! -d "$SCRIPT_DIR/governance" ]; then
    echo "❌ 錯誤: 找不到來源 governance/ 目錄"
    echo "   請確認從 ai-governance-framework repo 執行此腳本"
    exit 1
fi

# 備份現有 governance/ (如果存在)
if [ -d "$TARGET/governance" ]; then
    BACKUP="$TARGET/governance_backup_$(date +%Y%m%d_%H%M%S)"
    echo "📦 備份現有 governance/ → $BACKUP"
    cp -r "$TARGET/governance" "$BACKUP"
fi

# 部署 governance/ (8 大法典)
echo "📝 部署 governance/ (8 大法典)..."
cp -r "$SCRIPT_DIR/governance" "$TARGET/"

# 部署 governance_tools/
echo "🔧 部署 governance_tools/..."
cp -r "$SCRIPT_DIR/governance_tools" "$TARGET/"
chmod +x "$TARGET/governance_tools/"*.py

# 部署 docs/
echo "📚 部署 docs/..."
mkdir -p "$TARGET/docs"
if [ -f "$SCRIPT_DIR/docs/INTEGRATION_GUIDE.md" ]; then
    cp "$SCRIPT_DIR/docs/INTEGRATION_GUIDE.md" "$TARGET/docs/"
fi

# 建立 PLAN.md (如果不存在)
if [ ! -f "$TARGET/PLAN.md" ]; then
    echo "📋 建立 PLAN.md 起始模板..."
    cat > "$TARGET/PLAN.md" << 'EOF'
# PLAN.md — [專案名稱]

> **專案類型**: [類型]
> **技術棧**: [語言/框架]
> **複雜度**: L1 / L2 / L3
> **預計工期**: [開始] ~ [結束]

---

## 📋 專案目標

[一句話描述專案要達成什麼，≤100 字]

**Bounded Context**:
- [此專案負責的核心功能 1]
- [此專案負責的核心功能 2]

**不負責**:
- [明確排除的功能 1]

---

## 🏗️ 當前階段

```
階段進度:
├─ [🔄] Phase A: [階段名稱]       (進行中)
└─ [⏳] Phase B: [階段名稱]       (待開始)
```

**當前 Phase**: **Phase A - [階段名稱]**

---

## 📦 Phase 詳細規劃

### Phase A: [階段名稱] (進行中 🔄)

**目標**: [一句話]

**任務清單**:
```
├─ [🔄] 1. [任務名稱]        ← 當前進行中
└─ [⏳] 2. [任務名稱]
```

**Gate 條件**:
- [ ] [驗收條件 1]
- [ ] [驗收條件 2]

---

## 🔥 本週聚焦 (當前 Sprint)

**Sprint 1** ([日期範圍])

**目標**: [本週要達成什麼]

**任務清單** (≤5 項):
- [ ] [任務 1] (預計 Xh)
- [ ] [任務 2] (預計 Xh)

**下一步**:
1. [下一步動作]

**當前阻礙**: 無

**需要決策**: 無

---

## 📊 待辦清單 (Backlog)

### 高優先 (P0)
- [ ] [任務描述]

### 中優先 (P1)
- [ ] [任務描述]

### 低優先 (P2)
- [ ] [任務描述]

---

## 🚫 不要做 (Anti-Goals)

❌ **Phase A 禁止**:
- 不要 [禁止事項] ([理由])

---

## 🤖 AI 協作規則

**AI 在實作任何功能前，必須確認**:

1. ✅ 這項任務在「本週聚焦」或「下一步」中嗎?
2. ✅ 是否符合當前 Phase 的範圍?
3. ✅ 是否在「不要做」清單中?

**如果不符合上述條件**:
- 先詢問是否調整 PLAN
- 不要自行決定優先級
- 提供明確的選項 (A/B/C)

---

## 🎯 Gate 與驗收標準

### Phase A Gate

**功能完整性**:
- [ ] [驗收條件]

**代碼品質**:
- [ ] Unit test 覆蓋率 ≥ 80%

**文檔完整性**:
- [ ] Public API 有註解

---

## 📅 里程碑

| 里程碑 | 目標日期 | 狀態 | 交付物 |
|---|---|---|---|
| M1: [名稱] | YYYY/MM/DD | 🔄 | [交付物] |

---

## 🔄 變更歷史

| 日期 | 變更內容 | 原因 |
|---|---|---|
| YYYY/MM/DD | 專案啟動 | - |
EOF
    echo "   ✅ 已建立 PLAN.md 模板，請填寫專案資訊"
else
    echo "   ⏭️  PLAN.md 已存在，跳過"
fi

echo ""
echo "✅ 部署完成! 目錄結構:"
echo ""
echo "$TARGET/"
echo "├── PLAN.md              ← 填寫你的專案計畫 ⭐"
echo "├── governance/          ← 8 大法典 (勿修改)"
echo "├── governance_tools/    ← 自動化工具"
echo "└── docs/                ← 整合指南"
echo ""
echo "🧪 驗證安裝:"
echo "  python $TARGET/governance_tools/memory_janitor.py --check"
echo ""
echo "📋 下一步:"
echo "  1. 編輯 $TARGET/PLAN.md，填寫專案資訊"
echo "  2. 告訴 AI 讀取 governance/ 下的治理文件"
echo ""
