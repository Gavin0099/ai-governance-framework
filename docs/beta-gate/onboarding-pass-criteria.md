# Onboarding Pass Criteria

> 更新日期：2026-03-30
> 定位：Beta Gate condition 2 / human self-serve track

---

## 目的

這份文件定義 human self-serve onboarding 何時算通過。

這條 gate 關心的是：

> 一個外部 reviewer 在不靠作者口頭補充、也不靠 AI 幫忙的情況下，能不能理解 framework 的基本入口、關鍵 distinction 與最小操作路徑。

---

## 核心問題

這個 gate 不是在問 framework 功能強不強，而是在問：

- reviewer 能不能找到 repo root 與正確入口
- reviewer 能不能理解 adopt / drift / runtime flow 的基本差異
- reviewer 能不能說出 framework governance 與 consuming repo governance 的差別
- reviewer 能不能產出最小 governance artifact

---

## Pass Criteria

### CP1：找到正確入口

**Observable**

reviewer 能在合理時間內找到 repo root 與主要入口文件。

### CP2：理解 adopt path

**Observable**

reviewer 能說出 adopt、drift checker、runtime path 的角色，而不是把整個 framework 當成一堆零散 scripts。

### CP3：理解核心 distinction

**Observable**

reviewer 至少能說出以下幾個 distinction：

- framework governance vs project governance
- `governance_tools/` vs `runtime_hooks/`
- domain contract vs rule pack

### CP4：知道如何檢查 governance health

**Observable**

reviewer 知道要看 `governance_drift_checker`、onboarding artifacts 或其他基礎 health signal，而不是只依賴 README 印象。

### CP5：能產出最小 artifact

**Observable**

reviewer 至少能完成一條最小治理路徑，例如：

- adopt
- drift check
- 最小 session flow
- 或其他能留下 evidence 的 onboarding artifact

---

## 通過規則

| Score | Outcome |
|------|---------|
| 3+ of 5 | Pass |
| 2 of 5 | Fail |
| 0-1 of 5 | Fail / entry path not established |

### Override

若 `CP5`（artifact production）失敗，通常應視為 automatic fail，因為這代表 reviewer 雖然看得懂部分概念，卻還無法沿著 intended path 形成可驗證 evidence。

---

## 常見失敗類型

- reviewer 找不到正確入口
- reviewer 混淆 framework 與 consuming repo 的責任
- reviewer 看得懂概念，但走不出最小操作路徑
- reviewer 只能靠作者補充才能完成 onboarding

---

## 一句話

`Onboarding Pass Criteria` 關心的不是 reviewer 是否大致理解，而是他是否真的能沿著 intended path 完成一個最小、可驗證的 self-serve onboarding。
