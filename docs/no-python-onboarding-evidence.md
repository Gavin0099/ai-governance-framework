# No-Python Onboarding Evidence Template

> 當環境中 `python`、`python3`、`py` 都不可用時，使用這份模板。
> 「不可用」可以是 `command not found`，也可以是像 `No installed Python found!` 這類 launcher 訊息。
> 每一欄都要填。完成後請另存成 `docs/no-python-evidence-<YYYY-MM-DD>.md`。
> 這是一份正式 onboarding artifact，不是 workaround 筆記。

---

## 1. 環境記錄

```text
日期：
作業系統：
使用的 shell / terminal：

嘗試過的命令（請貼精確輸出，或填 "command not found"）：
  python --version：
  python3 --version：
  py --version：
```

---

## 1b. Repo identity 檢查

**填第 2～7 節前，先完成這一節。若任一檔案找不到，請停止，並在第 6 節記錄 failure。**

在你正在檢查的 repo 中，找到以下兩個檔案並確認存在：

```text
File 1：onboarding entrypoint
  你看到的相對路徑（例如 start_session.md 或 docs/start_session.md）：
  確認存在（Y / N / cannot find）：
  檔案第一個 heading 或第一句話：

File 2：drift checker
  你看到的相對路徑：
  確認存在（Y / N / cannot find）：
  第一行 --help 或 opening docstring 說它做什麼：
```

若任一檔案缺失，或內容與第 2～7 節描述的流程不符，代表：

- 你可能在錯的 repo
- 或這是個不完整 adoption

在這個問題解決前，不要繼續填第 2～7 節。

---

## 2. Entrypoint 驗證

閱讀 `README.md`，回答：

```text
這個 framework 是做什麼的？一句話說明：

README.md 說 onboarding 第一個要打開的檔案是什麼？

你有找到那個檔案嗎？ Y / N
如果是 N，你找了哪些地方？最後看到的是什麼？
```

---

## 3. Adoption path 驗證

閱讀 `start_session.md`，回答：

```text
canonical adoption command 是什麼？

它用的是哪個 tool？（請寫腳本名稱，不要只寫 "python"）

adoption 會在 target repo 產出什麼？（至少寫一個檔案或 artifact）

如果 Python 不可用，文件中有沒有 fallback adoption path？ Y / N
如果有，它是什麼？需要什麼前提？
```

---

## 4. Minimum session flow 驗證

閱讀 `start_session.md`，回答：

```text
minimum governance session flow 依序有哪些步驟：
1.
2.
3.
4.

哪一個步驟必須靠執行才能驗證？

哪些步驟可以只靠閱讀驗證？
```

---

## 5. Drift check 驗證

閱讀 `README.md` 或 `governance_tools/README.md`，回答：

```text
哪個命令用來檢查 governance drift？

它檢查的是什麼？（一句話描述行為，不是重貼命令）

這個 tool 在 repo 裡哪個位置？
```

---

## 6. Blocker 記錄

```text
在哪一個步驟開始必須執行才能繼續？

失敗的精確命令：

精確錯誤輸出（或 "command not found"）：

文件裡有沒有寫 recovery path？ Y / N
如果有，是什麼？
如果沒有，文件在哪裡就斷掉了？
```

---

## 7. Onboarding verdict

```text
Task 1：理解這個 framework 是做什麼的：         Y / N / Partial
Task 2：理解 adoption 怎麼運作：               Y / N / Partial
Task 3：描述 minimum session flow：            Y / N / Partial
Task 4：找到 drift checker：                   Y / N / Partial

建議的下一步解法：
```

---

## Artifact validity

完成版要算 Route B onboarding artifact，必須滿足：

- 七個 section 都填完，不能留空
- 第 6 節記錄的是精確失敗，不是意譯
- 第 7 節有具體 next step，不能只寫「安裝 Python」

若模板有空欄，或第 7 節只寫「安裝 Python」，都不算完成。
