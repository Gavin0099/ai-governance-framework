# No-Python Onboarding 證據

> 若 `python` / `python3` / `py` 三者都回傳
> 指令找不到（`command not found`）或 `No installed Python found!`（py launcher），
> 請填寫此表，存為 `docs/no-python-evidence-<YYYY-MM-DD>.md`，
> 作為 onboarding artifact，記錄 workaround 效果。

---

## 1. 確認指令

```text
執行環境（shell / terminal）：
執行時間（盡量記錄，以利 "command not found" 判斷）：
  python --version
  python3 --version
  py --version
```

---

## 1b. Repo identity 確認

**（選項 2：若無法安裝 Python，需先確認 repo 基本可讀性後再決定 6 項 failure）**

請確認以下兩個 repo 基本識別項目的可讀性：

```text
File 1：onboarding entrypoint
  檔案路徑（如 start_session.md 或 docs/start_session.md）：
  確認結果：Y / N / cannot find
  確認方式：標題或 heading 是否可辨識：

File 2：drift checker
  檔案路徑：
  確認結果：Y / N / cannot find
  確認方式：--help 或 opening docstring 開頭是否可讀：
```

若以上兩項都無法確認，選項 2 的「可繼續嗎」欄位應填「否」：
- 無法識別 repo
- 無法繼續 adoption

若可以確認，繼續填寫選項 2 的其他項目：

---

## 2. Entrypoint 確認

請查閱 `README.md`，填寫：

```text
framework 的用途是否可讀（主入口可辨識）：
README.md 的 onboarding 是否有指向可理解的入口步驟：

是否有任何 Python 相關的步驟：Y / N
若有，N 狀況下，請記錄這些步驟是否有替代說明：
```

---

## 3. Adoption path 確認

請查閱 `start_session.md`，填寫：

```text
canonical adoption command 是否可讀：

使用的 tool（記錄指令格式）：
adoption 對 target repo 是否有說明如何產生 artifact：
若 Python 不可用，是否有明確 fallback adoption path：Y / N
若無，請記錄目前採用的替代方式：
```

---

## 4. Minimum session flow 確認

請查閱 `start_session.md`，填寫：

```text
minimum governance session flow 大致步驟：
1.
2.
3.
4.

是否有任何步驟要求 Python：
是否有任何步驟的替代方式有明確說明：
```

---

## 5. Drift check 確認

請查閱 `README.md` 或 `governance_tools/README.md`，填寫：

```text
如何執行 governance drift 確認：
執行方式是否可理解：
是否有替代方式可行：

使用 tool 或 repo 的可讀狀態：
```

---

## 6. Blocker 確認

```text
哪些步驟因為無法繼續而停止：

替代方式是否嘗試過：

錯誤訊息（如 "command not found"）：

是否有任何沒有 Python 的 recovery path：Y / N
若有，請記錄說明：
若無，請標記哪個環節需要修正：
```

---

## 7. Onboarding verdict

```text
Task 1：瞭解 framework 的用途是否可讀：        Y / N / Partial
Task 2：瞭解 adoption 的步驟是否可讀：         Y / N / Partial
Task 3：完成 minimum session flow：            Y / N / Partial
Task 4：執行 drift checker：                   Y / N / Partial

整體結論：是否可繼續？
```

---

## Artifact validity

此表作為 Route B onboarding artifact，有效條件：

- 每個 section 都已填寫或標記無法填寫
- 第 6 項確認已記錄 blocker 性質
- 第 7 項給出 next step 決定（是否需要 Python）

注意：若第 7 項結論是「需要 Python」，請確認後重新啟動流程。
