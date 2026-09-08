# Solo R2 決策支援結案 — 2026-09-08

本輪執行、oracle、簡化盲評、分數凍結與揭盲已完成。品質結論不完整：三個可評維度相同，但兩臂回歸安全均無法評定，不能宣稱總分、整體平手或 Treatment 優於 CONTROL。

本紀錄依 owner 最新指示結束本輪，不再以 Python capability probe 阻擋結案。這是實驗結案報告，不是 Formal Gate 3 通過憑證。

## 結果與限制

Evaluation：`74ad1963-e24c-4ced-9f84-32e3c0daf900`；Pair：`93584d7e-2bf9-4535-93c8-5593fcd3e272`。

| 項目 | CONTROL | Bug Fix Safety TREATMENT |
|---|---|---|
| 匿名 key | `1d0d2b9a9af2940584464a26202cd52a56510f465015797d10b0984e4130b655` | `efed5d66fc5fa601e860b3c4014d0054086a304c26d8cd9d313f135a3b31113b` |
| 因果解釋 | 2/2 | 2/2 |
| 回歸安全 | NOT_ASSESSABLE（無法評定） | NOT_ASSESSABLE（無法評定） |
| 修改聚焦 | 2/2 | 2/2 |
| 證據品質 | 2/2 | 2/2 |
| 品質總分 | 無法判定 | 無法判定 |
| 獨立 oracle | 10/10 PASS | 10/10 PASS |
| 工具呼叫 | 13 | 16 |
| elapsed_ms | 116,609 | 199,327 |

Treatment 在本題工具呼叫多 3 次、耗時約 1.71 倍。這只是單題 execution cost 訊號，不證明 Skill 一般較慢、較差或不值得。不能把三項已評分結果寫成 6/8，也不能用 oracle 10/10 補成回歸安全 2/2。

唯一 claim ceiling 為 `NON_COUNTED / SOLO_CONTROLLED / DECISION_SUPPORT_ONLY`（不計入正式證據、Solo 控制、僅供決策支援）。不宣稱 OS-level scorer isolation、strict end-to-end shakedown PASS、Formal/counted evidence、一般化 Skill 效果或 A1–A6 進展。簡化評分的保證調整已在 `646dbe69` 採納；不能把本次結案回寫成原 strict 路線成功。

## 證據與歷史保留

- [揭盲結果](unblinding-result.json)：既有分數對回 arm；本次不重評、不補證據、不重新 freeze。
- [分數凍結紀錄](scores-frozen.json)：945 bytes；SHA-256 `7fd6c864fc1c806bb015cfc13e234ae3766a911735e031164c6706ac0a07353e`。
- [ledger 副本](ledger-snapshot.ndjson)：5,193 bytes、9 events；SHA-256 `e471517f5e6e36e2fdce3f42c8e87edf6b87c2cc4a67e47acbf90352140eac77`。這是歷史副本，不是新 allocation 或可繼續執行的 ledger。
- [oracle 更正摘要](oracle-verified-summary.json)：初版 FAIL 是 CRLF 彙整解析錯誤；重新核對原始輸出得到兩臂 10/10，沒有重跑 oracle。原始摘要、兩份原始結果、stdout/stderr 與更正結果均保存。
- [來源／副本 identity 清單](identities.json)：20 份副本經 `preserve.py` 對來源 bytes 核對。原 rejected bundle、舊 checkpoint、先前失敗 Pair 均未修改或刪除；舊 bundle 仍不可供評分。

公開 ledger 的 EXECUTION_TERMINAL 記錄執行結束當下 oracle NOT_RUN；後續 evaluator 的 PASS 存在獨立 oracle evidence。兩個時間點不應混寫，本次不改歷史事件。

## Governance 結果

已觀察到 execution admission、task exposure、child execution、收卷、terminalization、evidence preservation、sealing、簡化評分 freeze 與揭盲完成。舊 bundle 的 identity leakage 被 blindness gate 阻擋，這是正確 fail-closed；identity stripping 不完整則是已發現的 harness 缺陷，不能因此宣稱 Governance 全面 PASS。

回歸證據後續 audit 已區分：兩臂有寫測試且嘗試執行，但裸 `python` 無法解析，沒有 regression execution result；既有 projection 又漏掉 test source／command／diagnostic。前者是 ARM_OUTPUT_GAP，後者是 SCORING_INPUT_GAP。這些事後資訊不回填已凍結分數。

Projection／future consumer 及 version binding 已在 `5e983fbd` 採納並提交；既有證據為 132 local、55 independent tests PASS，Blocking 0。本次沒有重跑這些測試。修正涵蓋 stale/current/unknown、複合命令與不完整事件 fail-closed。future synthetic consumer 已接線，真實 future launcher integration 尚未完成，不能宣稱下一輪 evaluator 已實機修妥。Skill 未修改，沒有證據把目前缺口歸因於 Skill。

## POST-GATE3：不阻擋本輪結案

1. 未來 regression execution capability：Python/server/arm capability 仍 UNKNOWN。裸命令解析問題已定位，absolute Python 在所需 boundary 的完成證據仍不足。
2. [USERNAME 驗證](post-gate3-verification.json)：只加入 SID 正反向驗證後的 USERNAME，使 native helper 產生 intended owner ACE 並恢復一般 owner 讀取；marker handoff 因果行為上確認，不聲稱觀測到 binary 內部 real_user。
3. [timeout audit](post-gate3-timeout-audit.json)：request 02:13:09.780 UTC 開始，45 秒 client deadline 約 02:13:54.8；setup 到 02:13:58.974 才完成（49.194 秒），02:13:59.095 選擇 command-runner path。只證明 client deadline 先到，不能推出 Python 或 runner 卡住、成功、失敗。ROOT_CAUSE_UNRESOLVED 保留。
4. setup 並非無副作用：native sandbox account／ACL／Firewall/WFP 活動已有紀錄；本次不清理、不重跑。完整 descendant-tree cleanup 未獲證明。
5. 未來是否提供共用 controlled Python、調整 response wait、接入真實 consumer、補足 rubric 所需資料或做另一輪 evaluation，均需另定範圍與授權。本次不配置新 Pair、不恢復任何 replacement entitlement。
6. AppContainer 模型後端與高保證 scorer runtime 不再阻擋此 decision-support 結案。評測分級與降低操作成本留待後續，不在此新增框架。

## 治理成本觀察（附帶，非驗收條件）

案例：`ai-governance-framework`／Solo R2 Bug Fix Safety decision-support；實作基準 `5e983fbd`；歷史全流程實際治理版本未確認（本次載入 SYSTEM_PROMPT v5.3）；工作結果為流程完成、品質結論不完整。

| 合併事件 | 多做的工作／時間 | 是否改變決策 | 沒做可能漏掉什麼（反事實，非實測） | 初步判斷／既有依據 |
|---|---|---|---|---|
| 盲評身分洩漏及隔離接線 | review、authority、隔離 probe；總額外時間未量測 | 有：阻擋舊 bundle，最後採納較低保證的簡化評分 | 可能把受身分污染的評分當嚴格盲評 | 攔截是必要防護；整體成本是否划算尚無法判斷。依 646dbe69 與既有 superseding 歷史 |
| 回歸 evidence omission／版本關係不可信 | projection／consumer 修正及 review；時間未量測 | 有：補資料鏈、阻止 stale 或不完整事件被視為 CURRENT | 可能把舊版本成功誤作目前版本成功 | 必要 correctness 防護；依 5e983fbd 及其已提交 review |
| Python capability 探查延伸到 setup／診斷 | 多入口核對、request 修正、USERNAME 單變因與 timeout audit；總時間未量測 | 有：定位 handoff；本輪決策改為不再等待 capability | 若不查可能保留 setup 缺陷；但不影響既有凍結分數 | 部分為 agent 工具／request 錯誤造成的返工；進一步追查是否值得尚無法判斷。依本目錄 POST-GATE3 快照 |

這是一個案例，不能把每次 review、retry、memory entry 當獨立樣本，也不能單憑本次證明治理有效、無效或划算。49.194 秒是一次 setup 的觀測耗時，不是整體治理成本。

本次結案只新增文件與 exact evidence copies；不修改 production、Skill、sandbox、ACL、原始 ledger／output／scores，不重跑 arm、oracle 或 scoring。既有無關 dirty work 明確排除於此次提交。
