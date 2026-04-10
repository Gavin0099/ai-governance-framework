# DBL First Slice Adversarial Intent

> 更新日期：2026-03-31

這份文件用來說明為什麼 first-slice DBL 必須接受 adversarial / gaming 測試。

關鍵問題不是「surface 有沒有欄位」，而是：

> 當 formal presence 已存在時，這個 slice 能不能避免 reviewer 被 pseudo-presence 或 semantic insufficiency 誤導？

first slice 若只會檢查 presence，會出現兩種風險：

- 有文件就被當成 precondition satisfied
- limitation record 被誤讀成 capability claim

因此 adversarial intent 的重點是：

- 測 formal presence 是否足以騙過 gate
- 測 insufficiency case 是否能暴露 current slice 的限制
- 測 reviewer 是否能指出這是 limitation proof，而不是 adequacy proof

這一刀的目標不是把 first slice 做成 full semantic engine，而是誠實測出：

- 它目前能防哪些 gaming pattern
- 哪些 pseudo-compliance 仍會漏過
- 後續要不要擴 slice，應根據哪種 failure mode 決定
