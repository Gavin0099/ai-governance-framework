# Governance Revision — 2026-03-20

## 摘要

這次 revision 的目標，是在保留 hard safety 與 architecture boundary 的前提下，降低低風險工程工作的 workflow friction。

這次更新主要回應兩個 recurring failure mode：

- governance 對 build、test、review、commit preparation、governance retrospective 這類相鄰工程工作過度容易 stop
- governance 沒有明確要求 legacy refactor、rollback、unstable historical commit 等情境先做 baseline validation

---

## 這次改了什麼

### 1. Agent identity 與 scope

core governance 現在把 assistant 視為：

> governance-first coding agent

而不是純 reviewer。

這代表：

- `PLAN.md` 仍負責 planned feature scope
- bounded adjacent engineering work 預設在正常範圍內
- 只有越過 hard boundary 時才需要停止或升級

現在被視為正常相鄰工程工作的例子包括：

- build
- test
- debugging
- review
- commit preparation
- governance analysis
- documentation sync

### 2. Decision model 與 baseline discipline

revision 也明確收斂了另一個問題：

> 對 legacy refactor、rollback、unstable historical commit 這類情境，原本沒有強制 baseline validation，容易讓後續 failure 難以歸因。

因此這次更新後，對以下情境應先做 baseline validation：

- legacy refactor
- rollback
- unstable historical commit
- 歷史狀態不乾淨、難以判斷 drift 來源的工作樹

---

## 這次沒有改什麼

這次 revision 不是全面放寬治理。  
它沒有改變：

- hard safety stop
- architecture gate
- authority precedence
- high-risk task 的 stricter discipline

因此這次更新應被理解成：

> 把原本太容易阻擋正常低風險工程工作的地方收斂回合理邊界，
> 而不是把治理本身放鬆掉。

---

## 影響

這次 revision 之後：

- 低風險正常工程工作更接近「可預期可做」
- 不再每次都像例外放行
- 對高風險或歷史不穩定情境，反而更明確要求 baseline、validation、可追溯 evidence

---

## 一句話結論

2026-03-20 的 governance revision，不是在弱化治理，而是在保留 hard boundary 的前提下，降低相鄰低風險工程工作的不必要摩擦，並把 legacy / unstable context 的 baseline discipline 正式寫清楚。
