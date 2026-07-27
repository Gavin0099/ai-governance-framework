---
layout: home

hero:
  name: "AI Governance"
  text: "工程證據與交接 Wiki"
  tagline: "讓 AI coding agent 的邊界、證據與宣稱可被審核。它管理的是工程過程的可信度，不把治理包裝成模型能力提升。"
  actions:
    - theme: brand
      text: 從核心概念開始
      link: /core-concepts
    - theme: alt
      text: 查看 Repo 即時摘要
      link: /generated/repository-status

features:
  - title: 邊界可見
    details: 在執行前說清楚 allowed scope、forbidden scope、DONE 與非目標。
  - title: 證據可查
    details: 把測試、artifact、receipt 與實際 commit 綁定，避免摘要取代證據。
  - title: 宣稱受限
    details: test pass 不自動等於 production safe；report-only 也不冒充 enforcement。
  - title: 交接可延續
    details: 下一個 Agent 或同事能知道改了什麼、驗證到哪裡、下一步從哪裡開始。
---

<p class="wiki-kicker">Positioning / 定位</p>

## 先回答最重要的問題

這個 framework 目前最可信的價值，不是讓 AI 突然更會 debug 或設計演算法，而是降低三種工程風險：

<div class="scope-strip">
  <div class="scope-card status-established">
    <strong>範圍失控</strong>
    <p>限制 Agent 順手重構、擴張需求或修改未授權檔案。</p>
  </div>
  <div class="scope-card status-established">
    <strong>證據失真</strong>
    <p>區分真的執行過、只有文字宣稱，以及證據綁定的是哪個版本。</p>
  </div>
  <div class="scope-card status-established">
    <strong>交接斷裂</strong>
    <p>讓跨 session、跨 Agent、跨同事的接手有可追溯起點。</p>
  </div>
</div>

<div class="claim-boundary">
  <p><strong>Claim ceiling：</strong>這是 audit framework，不是 security boundary；它讓繞過變得可見與可歸因，但不能阻止蓄意繞過工具鏈的 Agent。</p>
</div>

## 能力成熟度要分開讀

<div class="truth-grid">
  <div class="truth-card status-established">
    <strong>目前較成熟</strong>
    <p>Task contract、scope discipline、artifact evidence、claim ceiling、receipt、memory 與 reviewer handoff。</p>
  </div>
  <div class="truth-card status-partial">
    <strong>部分成立</strong>
    <p>Hooks、validators、F-7、consumer adoption 與 selective fail-closed；成立範圍取決於實際接線。</p>
  </div>
  <div class="truth-card status-unproven">
    <strong>尚未證明</strong>
    <p>普遍提高 coding outcome、降低 defect rate、縮短開發時間，或收益穩定大於治理成本。</p>
  </div>
  <div class="truth-card status-unproven">
    <strong>不應宣稱</strong>
    <p>AI 語義正確、production safety、不可繞過、所有 consumer 已完整導入，或已達 G4。</p>
  </div>
</div>

## 依你的角色選入口

<div class="route-grid">
  <div class="route-card">
    <strong>我要理解這套框架</strong>
    <p>先看<a href="./core-concepts">核心概念</a>與<a href="./architecture">系統架構</a>，理解 guidance、report-only 與 enforcement 的差異。</p>
  </div>
  <div class="route-card">
    <strong>我要導入到工程 Repo</strong>
    <p>從<a href="./adoption">Consumer 導入</a>開始；先分類 repo 角色，再決定可自動化到哪裡。</p>
  </div>
  <div class="route-card">
    <strong>我要讓 Agent 接手工作</strong>
    <p>看<a href="./workflow">Agent 工作流程</a>，把 DONE、驗證、commit 與 non-claims 串成一條可交接路徑。</p>
  </div>
  <div class="route-card">
    <strong>我要判斷它是否真的有用</strong>
    <p>看<a href="./evidence">證據邊界</a>；不要用工具數量、session 數或 receipt 數代替 outcome。</p>
  </div>
</div>

## Repository 如何和 Wiki 同步

`main` 是唯一內容來源。每次更新後，GitHub Actions 會：

1. 只讀取公開 allowlist 中的 Markdown 與 Skill metadata。
2. 重新產生 [Repository 自動摘要](./generated/repository-status)。
3. 建置 VitePress 靜態站。
4. 將建置產物部署到 GitHub Pages。

`memory/`、`artifacts/`、receipts 與 transcripts 不在網站來源 allowlist 內。網站是 repo 的公開投影，不是另一套治理真相。
