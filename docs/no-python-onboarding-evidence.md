# No-Python Onboarding 驗證

> 當目標環境沒有 `python` / `python3` / `py` 可用時的 onboarding 證據收集方式
> 適用情境：shell / terminal 直接回報 `command not found` 或 `No installed Python found!`
> 建議輸出：`docs/no-python-evidence-<YYYY-MM-DD>.md`

---

## 目的

這份文件定義在 **沒有 Python 可直接執行** 的環境中，如何仍然留下可 review 的 onboarding evidence。

它要解決的不是「立刻修好環境」，而是：

- framework 是否有被正確理解
- adoption 路徑是否仍可被重建
- blocker 是否被清楚記錄
- 是否存在可行的 fallback / next step

---

## 1. 確認實際 blocker

先記錄最基本的 shell 現象：

```text
python --version
python3 --version
py --version
```

如果都失敗，至少要保留：

- 實際錯誤訊息
- 失敗時間
- 使用的 shell / terminal 類型

---

## 2. 確認 repo identity 與最小入口

即使沒有 Python，reviewer 仍應能確認：

- repo 是 framework repo，而不是 consuming repo
- repo 內的 onboarding entrypoint 是什麼
- drift / runtime / adopt 大致位於哪一層

最小檢查項：

### File 1：Onboarding entrypoint

- 能否找到 `README.md` 或 `docs/start_session.md`
- 入口文件是否存在：`Y / N / cannot find`
- 入口文件是否足以看出 onboarding 起點

### File 2：Drift checker / governance health 路徑

- 能否定位 `governance_drift_checker`
- 文件中是否能看出用途與位置
- 若看不到，是否明確記為 discoverability gap

---

## 3. 檢查 README 是否足以支撐理解

至少確認：

- framework 的定位是否可看出
- onboarding 基本路徑是否可看出
- 沒有 Python 時，是否仍能理解下一步應做什麼

可用簡單 verdict 記：

- `Y`
- `N`
- `Partial`

---

## 4. 檢查 adoption path 是否可被重建

即使無法實際執行，也應能回答：

- canonical adoption command / path 大致是什麼
- 哪些工具本來應該被跑
- target repo 端原本應產出哪些 artifact
- 若 Python 不可用，是否有 fallback adoption path

---

## 5. 檢查 minimum session flow 是否仍可描述

即使不能執行，也應能說出 minimum governance session flow 的輪廓，例如：

1. session start
2. pre-task boundary / drift / baseline health
3. task execution evidence
4. session closeout / artifacts

如果這些完全說不出來，代表 blocker 不只是缺 Python，而是 onboarding surface 本身也不夠清楚。

---

## 6. 檢查 drift / governance health 路徑

應至少確認：

- reviewer 是否知道要看 governance drift
- reviewer 是否知道對應工具或文件在哪裡
- 沒有 Python 時，這一段會卡在哪裡

這一步的重點是區分：

- 單純執行 blocker
- 與 framework 可理解性缺口

---

## 7. 記錄 blocker 與 recovery path

至少留下：

- 目前 blocker 是什麼
- blocker 是否完全阻斷 onboarding
- 是否存在 recovery path
- 下一步是環境修復、fallback adoption，還是改文件入口

---

## 8. Onboarding Verdict

可用最小表格收斂：

```text
Task 1: framework 定位是否可讀             Y / N / Partial
Task 2: adoption 路徑是否可重建            Y / N / Partial
Task 3: minimum session flow 是否可描述    Y / N / Partial
Task 4: drift checker 路徑是否可定位       Y / N / Partial
```

最後再寫一句總結：

- 這次是 execution blocker
- 還是 onboarding surface 失敗
- 或兩者同時存在

---

## Artifact validity

一份合格的 `Route B` onboarding artifact，至少應滿足：

- 各 section 有具體觀察，不是泛泛描述
- blocker 有被清楚命名
- next step 有明確指向
- 不會把「缺 Python」誤說成 framework 整體失敗

---

## 一句話

這份 no-Python evidence 的目的，不是替代正常 onboarding，而是在執行條件缺失時，仍保留一條可 review、可診斷、可比較的 onboarding 證據路徑。
