# Beta Gate Failure Mode Catalog

> 更新日期：2026-03-30

---

## 目的

這份 catalog 用來整理 beta gate 階段已經觀測到的主要 failure mode。

它的用途不是累積抱怨，而是幫 reviewer、maintainer 與 framework 作者更快回答：

- 這次 fail 屬於哪一類
- failure 發生在哪一層
- 是否可重現
- 最小修正路徑是什麼

---

## 使用方式

每個 failure mode 應至少包含：

- failure 編號
- 觸發場景
- 觀測現象
- 為什麼這是 gate blocker 或重要 warning
- 最小修正方向

如果某個問題無法穩定重現，應標成 observation / pending，而不是過早升格成 canonical failure mode。

---

## FM-001：No-Python Execution Block

**來源**：R2 reviewer run，2026-03-30

**現象**

reviewer 在 target 環境缺少 Python 時，無法走完預期的治理工具執行路徑。

**為什麼重要**

這代表 framework 的最低操作前提沒有被清楚表達，會直接阻斷 onboarding 與 evidence production。

**最小修正方向**

- 把 entrypoint / prerequisites 說清楚
- 提供 fallback path 或 Route B 證據收集方式
- 避免 reviewer 在最初步驟就卡死

---

## Catalog 的角色

`Beta Gate Failure Mode Catalog` 是 reviewer-facing 的 failure reference，不是新的 authority layer。

它的作用是讓 failure 更容易被命名、重現與修正，而不是用來替代原始 runtime / reviewer artifact。

---

## 一句話

這份 catalog 的目標是讓 beta gate failure 從零散事件，變成可重建、可比較、可修正的 failure inventory。
