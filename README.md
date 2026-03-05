# AI Governance Framework

> 從「餵指令」到「定規則」— 讓 AI 不再每次都重頭理解你的專案

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Version](https://img.shields.io/badge/version-1.0.0-blue.svg)](https://github.com/GavinWu1991/ai-governance-framework/releases)
[![PRs Welcome](https://img.shields.io/badge/PRs-welcome-brightgreen.svg)](http://makeapullrequest.com)

---

## 🎯 這是什麼?

一套完整的 **AI 協作治理框架**，基於「**建築師轉型理論**」，讓 AI 從「被動執行」升級為「主動協作」。

### 核心問題

```diff
- ❌ 沒有治理:
-    你: 幫我加個功能
-    AI: 好的 (立刻做，可能打亂計畫)
-    → AI 不知道優先級
-    → AI 會過早優化
-    → 對話越長越失控

+ ✅ 有治理:
+    你: 幫我加個功能
+    AI: 我看到 PLAN.md 本週目標是 A、B、C
+        這個功能不在清單中。要調整計畫嗎?
+    → AI 主動確認優先級
+    → AI 防止違反計畫
+    → AI 建議下一步
```

---

## 🏗️ 建築師轉型理論

**核心類比**:

| 軟體開發 | 建築工地 | 治理文件 |
|---------|---------|---------|
| 代碼 (Code) | 磚塊與水泥 | — |
| 架構 (Architecture) | 樑柱與地基 | ARCHITECTURE.md |
| AI Agent | 數位工頭 | — |
| 治理文件 | 施工規範書 | 8 大法典 |

> **價值主張**:  
> AI 的出現，不是為了取代工程師，  
> 而是為了讓工程師專注於「架構設計」，  
> 重新拿回屬於建築師的尊嚴。

---

## 📦 8 大法典 (完整治理架構)

```
🧠 意識層
  └─ SYSTEM_PROMPT.md     — AI 的身份與禁忌

📋 規劃層
  └─ PLAN.md              — 專案施工計畫 (今天蓋哪層樓) ⭐ 核心

⚙️ 執行層
  ├─ AGENT.md             — 任務執行流程
  ├─ ARCHITECTURE.md      — 架構紅線 (承重牆)
  └─ NATIVE-INTEROP.md    — 跨平台規範

✅ 品質層
  ├─ REVIEW_CRITERIA.md   — 代碼審查標準
  └─ TESTING.md           — 測試策略

🛑 安全閥
  └─ HUMAN-OVERSIGHT.md   — 強制停機機制
```

### 建築類比對照表

| 治理文件 | 建築工地 | 作用 |
|---------|---------|------|
| SYSTEM_PROMPT.md | 建築師資格證 | 誰有資格指揮工頭? |
| **PLAN.md** | **施工計畫表** | **今天蓋哪層樓?** ⭐ |
| ARCHITECTURE.md | 建築設計圖 | 承重牆在哪? 不能動! |
| AGENT.md | 施工規範書 | 怎麼砌磚? 流程是什麼? |
| REVIEW_CRITERIA.md | 品質驗收標準 | 磚砌得夠直嗎? |
| HUMAN-OVERSIGHT.md | 緊急停工令 | 發現問題立刻停! |
| TESTING.md | 工地安全檢查 | 怎麼驗收? |
| NATIVE-INTEROP.md | 材料規格 | 水泥、磚塊的標準 |

---

## 🚀 快速開始

### 1. 克隆專案

```bash
git clone https://github.com/GavinWu672/ai-governance-framework.git
cd ai-governance-framework
```

### 2. 部署到你的專案

```bash
# 複製治理文件到你的專案根目錄
cp -r governance /path/to/your/project/

# 或使用部署腳本
./deploy_to_memory.sh
```

### 3. 告訴 AI 讀取治理文件

**第一次對話**:
```
請閱讀 governance/ 目錄下的所有治理文件:

1. SYSTEM_PROMPT.md - 了解你的身份與禁忌
2. PLAN.md - 了解專案規劃格式規範 ⭐ 最重要
3. AGENT.md - 了解任務執行流程
4. ARCHITECTURE.md - 了解架構紅線
5. HUMAN-OVERSIGHT.md - 了解何時必須停止

特別注意 PLAN.md 的「AI 協作規則」§3.7:
實作任何功能前，必須先檢查:
- 是否在「本週聚焦」中?
- 是否在「不要做」清單中?
```

### 4. 為你的專案建立 PLAN.md

```bash
# 閱讀 PLAN.md 規範
cat governance/PLAN.md

# 根據規範為你的專案建立 PLAN
# 參考 governance/PLAN.md 中的範例
```

---

## 💡 PLAN.md — 最重要的文件

**PLAN.md** 是治理架構的核心，定義了「AI 今天該做什麼」。

### 為什麼需要 PLAN.md?

```
沒有 PLAN.md = 工頭不知道今天該蓋哪層樓

有了 PLAN.md:
  ✅ AI 知道「當前階段」是什麼
  ✅ AI 知道「本週目標」vs「待辦清單」
  ✅ AI 會主動提醒「這不在計畫中」
  ✅ AI 能建議「下一步該做什麼」
```

### 核心結構

```markdown
# PLAN.md

## 📋 專案目標
[一句話 + Bounded Context]

## 🏗️ 當前階段
├─ [✓] Phase A: 基礎架構 (完成)
├─ [🔄] Phase B: 核心功能 (進行中)
└─ [⏳] Phase C: 整合測試 (待開始)

## 🔥 本週聚焦
- [ ] 任務 1 (4h)
- [ ] 任務 2 (6h)
- [ ] 任務 3 (4h)

## 🚫 不要做 (Anti-Goals)
❌ Phase B 禁止:
- 不要提前優化效能 (Phase C 才做)
- 不要實作連線池

## 🤖 AI 協作規則
AI 實作任何功能前，必須確認:
1. ✅ 在「本週聚焦」中嗎?
2. ✅ 在「不要做」清單中嗎?
3. ✅ 如果都不符合，詢問是否調整計畫
```

### PLAN.md 實際案例

#### 場景 1: AI 主動確認優先級 ⭐⭐⭐⭐⭐

```
User: 幫我加個忘記密碼功能

AI: 我看到 PLAN.md 本週聚焦是:
    - 完成使用者登入
    - 實作基本 CRUD
    - 整合第三方 API
    
    「忘記密碼」不在清單中。
    
    選項:
    A) 先完成本週目標，再處理忘記密碼
    B) 調整計畫，將忘記密碼加入本週目標
    
    你希望如何處理?
```

**價值**: AI 主動提醒優先級，防止計畫失控! ✅

#### 場景 2: AI 防止過早優化 ⭐⭐⭐⭐⭐

```
User: 幫我優化一下效能

AI: 我檢查了 PLAN.md，當前階段是「Phase B: 核心功能」。
    
    Phase B 的「不要做」清單中有:
    ❌ 不要提前優化效能 (Phase C 才做)
    
    建議:
    - 如果效能問題嚴重影響開發，可以處理
    - 如果只是想提前優化，建議先完成 Phase B Gate
    
    你確定要現在優化效能嗎?
```

**價值**: AI 防止過早優化，遵守開發階段! ✅

#### 場景 3: AI 主動建議下一步 ⭐⭐⭐⭐⭐

```
User: 登入功能做完了

AI: 太好了! 我看 PLAN.md 的「下一步」是:
    - 實作基本資料 CRUD
    - 整合第三方 API
    
    我建議先實作 CRUD，因為它是基礎功能。
    
    要我開始實作 User 資料的 CRUD 嗎?
```

**價值**: AI 主動推進專案，不需要你每次想下一步! ✅

---

## 🛠️ 專案結構

```
ai-governance-framework/
├── README.md                    ← 你正在看的檔案
├── LICENSE                      ← MIT 授權
├── deploy_to_memory.sh         ← 部署腳本
│
├── governance/                  ← 8 大法典
│   ├── SYSTEM_PROMPT.md        ← AI 身份與禁忌
│   ├── PLAN.md                 ← 專案規劃規範 ⭐ 核心
│   ├── AGENT.md                ← 任務執行流程
│   ├── ARCHITECTURE.md         ← 架構紅線 (承重牆)
│   ├── REVIEW_CRITERIA.md      ← 代碼審查標準
│   ├── HUMAN-OVERSIGHT.md      ← 強制停機機制
│   ├── TESTING.md              ← 測試策略
│   └── NATIVE-INTEROP.md       ← 跨平台規範
│
├── governance_tools/            ← 輔助工具
│   └── README.md               ← 工具說明
│
├── docs/                        ← 文件與教學
│   └── INTEGRATION_GUIDE.md    ← 整合指南
│
└── archive/                     ← 歷史版本
```

---

## 📚 文件導覽

### 核心文件 (必讀)

- **[PLAN.md](governance/PLAN.md)** ⭐ - 專案規劃治理規範 (最重要!)
- **[SYSTEM_PROMPT.md](governance/SYSTEM_PROMPT.md)** - AI 身份定義
- **[AGENT.md](governance/AGENT.md)** - 任務執行流程
- **[ARCHITECTURE.md](governance/ARCHITECTURE.md)** - 架構紅線
- **[HUMAN-OVERSIGHT.md](governance/HUMAN-OVERSIGHT.md)** - 強制停機

### 整合指南

- **[整合指南](docs/INTEGRATION_GUIDE.md)** - 如何整合到現有專案

### 工具

- **[deploy_to_memory.sh](deploy_to_memory.sh)** - 部署腳本
- **[governance_tools/](governance_tools/)** - 輔助工具集

---

## 🤝 貢獻

歡迎貢獻! 

### 貢獻方式

- 🐛 [回報問題](https://github.com/GavinWu1991/ai-governance-framework/issues)
- 💡 [建議新功能](https://github.com/GavinWu1991/ai-governance-framework/issues)
- 📝 改善文件
- 🎯 [分享你的案例](https://github.com/GavinWu1991/ai-governance-framework/discussions)

### 貢獻指南

1. Fork 這個專案
2. 建立你的 feature branch (`git checkout -b feature/AmazingFeature`)
3. Commit 你的變更 (`git commit -m 'Add some AmazingFeature'`)
4. Push 到 branch (`git push origin feature/AmazingFeature`)
5. 開啟 Pull Request

---

## 💬 常見問題 (FAQ)

### Q: 這個框架適合我的專案嗎?

**適合** ✅:
- 複雜專案 (多 Phase 開發)
- 團隊協作 (需要同步優先級)
- 長期專案 (需要階段管理)
- AI 協作開發 (想讓 AI 主動協作)

**不適合** ❌:
- 一次性腳本 (過度設計)
- 超簡單專案 (L1 以下)

### Q: PLAN.md 放哪裡?

**專案根目錄**，與 README.md 同層:

```
myproject/
├── README.md
├── PLAN.md          ← 這裡
├── governance/      ← 8 大法典
└── src/
```

### Q: 多久更新一次 PLAN.md?

- **本週聚焦**: 每週更新 (Sprint)
- **當前階段**: 每 Phase 更新
- **變更歷史**: 每次修改都記錄

### Q: AI 不遵守 PLAN.md 怎麼辦?

1. 檢查 PLAN.md 格式是否符合 [規範](governance/PLAN.md)
2. 明確告訴 AI:「請遵守 PLAN.md 的 AI 協作規則 §3.7」
3. 在對話開頭重申規則

### Q: 我該從哪個文件開始?

**推薦順序**:
1. 📖 閱讀本 README
2. 📋 閱讀 [PLAN.md](governance/PLAN.md) 規範
3. 🚀 使用 `deploy_to_memory.sh` 部署
4. ✍️ 為你的專案建立第一份 PLAN.md

---

## 📖 延伸閱讀

### 理論基礎

- [建築師轉型理論](docs/architecture-theory.md) - 從搬磚工到建築師
- [治理 vs Prompting](docs/governance-vs-prompting.md) - 為什麼治理比 Prompt 重要

### 實踐指南

- [PLAN.md 完整指南](governance/PLAN.md) - 專案規劃治理規範
- [整合現有專案](docs/INTEGRATION_GUIDE.md) - 如何整合到現有工作流程

### 相關資源

- [Claude.ai 官方文件](https://docs.claude.com)
- [Prompt Engineering 最佳實踐](https://docs.claude.com/en/docs/build-with-claude/prompt-engineering/overview)

---

## 📄 授權

本專案採用 MIT 授權條款 - 查看 [LICENSE](LICENSE) 了解詳情

```
MIT License

Copyright (c) 2026 GavinWu

Permission is hereby granted, free of charge...
```

---

## 🙏 致謝

- 感謝所有在開發過程中提供反饋的朋友們
- 靈感來源: Domain-Driven Design, Test-Driven Development
- 建築師類比: 致敬所有真正的建築師與工程師

---

## 📧 聯絡

- **作者**: GavinWu (吳瑞益)
- **GitHub**: [@GavinWu1991](https://github.com/GavinWu1991)
- **Discussions**: [專案討論區](https://github.com/GavinWu1991/ai-governance-framework/discussions)
- **Issues**: [問題追蹤](https://github.com/GavinWu1991/ai-governance-framework/issues)

---

## 🌟 Star History

如果這個專案對你有幫助，請給個 Star ⭐

[![Star History Chart](https://api.star-history.com/svg?repos=GavinWu1991/ai-governance-framework&type=Date)](https://star-history.com/#GavinWu1991/ai-governance-framework&Date)

---

## 📌 快速連結

- [🚀 快速開始](#-快速開始)
- [📦 8 大法典](#-8-大法典-完整治理架構)
- [💡 PLAN.md 說明](#-planmd--最重要的文件)
- [🛠️ 專案結構](#%EF%B8%8F-專案結構)
- [🤝 貢獻指南](#-貢獻)
- [💬 常見問題](#-常見問題-faq)

---

**從今天開始，定義你的底線 — 包括「今天該做什麼」** 🏗️

---

<p align="center">
Made with ❤️ by <a href="https://github.com/GavinWu1991">GavinWu</a>
</p>
