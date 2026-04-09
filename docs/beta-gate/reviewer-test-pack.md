# Reviewer Test Pack — Beta Gate Condition 2

> 版本：1.1
> 建立：2026-03-30
> 更新：2026-04-08
> 適用：author-side test operator
> 不要在 reviewer 開始前把這份文件給他

---

## Part 1 — 你在測什麼

這份文件定義的是作者端如何跑一次 cold-start reviewer run。

reviewer 在開始前**不會**拿到這份文件。

reviewer 的起始條件由 `reviewer-test-brief.md` 定義：

- GitHub repo URL
- 一句 framing
- 不提供 file pointer
- 不提供作者導讀

---

## Part 2 — 目的

這份 pack 的作用，是讓作者端以一致方式執行 reviewer run，並保留可比較的 run record。

它不是給 reviewer 的教學文件；它是作者端的測試操作包。

---

## 一句話結論

`Reviewer Test Pack` 的工作，是把 beta-gate reviewer run 變成一致、可重播、可比較的作者端測試流程，而不是臨場 improvisation。
