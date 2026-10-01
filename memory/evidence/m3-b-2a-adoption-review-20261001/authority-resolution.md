# Existing authority path — bounded lookup

結果：不需要新增 reviewer type、認證制度或 approval gate；可使用當前人類指令作為明確採納來源。尚未將原 candidate 判成 current 或 mutation。

## 1. What existing rules actually require

`governance/MEMORY_SURFACE_AUTHORITY_CONTRACT.md:108` 要求 current / reviewed、authority-qualified reviewer、可追溯且覆蓋最新有效證據與 substantive transition、無未調和後續變化，以及可判定的 coverage。
同文件 L365–410 拒絕 self-attested-only、unqualified 或 unknown reviewer authority。這要求有外部可追溯來源，不能讓作者自行宣告 qualified。

在本輪搜尋的 agent-readable governance / memory_pipeline / skill 文件中，沒有另外找到 Memory reviewer 的資格註冊、指定第三人、GitHub APPROVED 或 certificate 制度。
這是 bounded lookup 結果，不是全 repo 或 human-only 文件不存在額外要求的證明。沒有讀 HUMAN-OVERSIGHT。

`memory_pipeline/active_task_supersession.py:55` 明確允許 `authority_source=current_human_instruction` 或 `approved_change`；L561–571 檢查來源名稱與非空 source_anchor。L548–556 仍要求各 eligibility predicates。
這是既有資料接入邊界，不是 runtime 自動認證 reviewer；不能只填合法 token 就證明 authority。
此案例是 legacy paragraph 退位，不會呼叫 R1 或補造 predecessor identity。

## 2. Who / what can satisfy the present decision

- 本 agent 已獲人類指定的 M3-b-2A 技術查證與採納審查範圍，可交付有依據的技術結論。這本身不是作者自行接受 candidate。
- 最小既有路徑：owner 讀取此 exact candidate / patch 與已完成的 scoped review，明確接受這個 bounded current interpretation，並保留該人類指令的來源。
- 此操作解讀依據當前人類指令可作 authority source、Memory 的 review / anchor 條件，以及現有 owner 對 scope 的權限；不是新增 reviewer 角色或普遍豁免。
- 若 owner 委派既有 reviewer，必須明確可追溯至本 work item 與採納判定範圍；不推定「有任意技術 reviewer」就有 current adoption 權限。
- 舊 PR #108 工程審查、原 canonical checkpoint、Slice 2 模擬 R1 authority，以及 fresh-agent 可讀性報告，各自只證明其範圍，不能自動接受本輪 exact retirement patch。

不把 `SOLO_OWNER_MERGE_AUTHORITY_CONTRACT.md` 的 PR merge predicates 移植到 Memory adoption；此輪沒有 PR 或 merge decision。該文件的適用範圍在 L22。

## 3. Acceptance evidence — no new schema

沿用人類指令 / 已核准變更與既有 scoped review artifact，記錄：

1. 誰接受、接受時點、可回追的人類訊息或 approved-change 來源；不得由 agent 代造人類接受。
2. Exact candidate 路徑與 bytes identity：`proposed-active-task.md` SHA-256 `61db7bbb3494c0ad5b2af156e39cdfbd9b72e9301a4d86c0207b670d6fd80df4`，以及對應 `proposed-change.patch`。
3. 判定內容與範圍：M3-b-2A engineering checkpoint 已 merge，指定 legacy L61–64 僅作歷史；沒有其他 work item / M3-b-2B / Gate 3 資格推論。
4. 所引用的 review.md、PR #108 / main anchor 與 exact original preservation，及審查後有無新的衝突。
5. 若接受後正式操作，實際 outcome 與必要 canonical record 仍需按原 MEMORY_PROTOCOL 處理；操作不得新增 active-task 摘要或改變 mutation scope。

上述為如何引用既有證據的說明，不新增 required machine fields、validator 或 gate。只寫 `APPROVED` 不足以代替來源與範圍。

## 4. Conditional authorization

Owner 已限定：只處理 M3-b-2A、五項成立才 mutation。若明確的人類接受補足本輪 exact current-adoption authority，且事實、candidate / target bytes 與保存條件仍成立，原有條件式 mutation 授權足以用於這一小筆操作，不需再索取同一個 scope 的第二次許可。

現有訊息只有分析／查明 authority 的指令，不能代造 owner 已接受 exact patch 的聲明。因此本輪保持凍結、不修改正式入口。
若 candidate 漂移、正式 target 已改變、evidence 衝突或 mutation scope 擴張，就不在原條件式授權內。
Commit / push / 其他工作仍不在本輪授權範圍。

## 5. Correction to earlier framing

前輪的「缺合格 reviewer acceptance」應理解成缺少此 exact candidate 的有來源接受，而不是已證明必須另找第三人或新增 reviewer qualification 流程。
現有 contract 沒有提供可引用的 Memory credential registry；不能自行把沒有 registry 升成新的硬 gate。
採納權限的實際流程成本尚未量測；本輪不宣稱架構缺陷或規則已被修改。

DONE：既有條件、可用來源、接受證據與條件式授權的關係已釐清；候選與正式檔案維持不變。
