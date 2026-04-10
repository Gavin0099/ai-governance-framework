# Kernel Driver Adapter 摘要

> Domain: `kernel-driver`
> Status: active summary
> Target: low-token adapter view for `Kernel-Driver-Contract`
> Primary sources:
> - `Kernel-Driver-Contract/contract.yaml`
> - `Kernel-Driver-Contract/AGENTS.md`
> - `Kernel-Driver-Contract/KERNEL_DRIVER_CHECKLIST.md`
> - `Kernel-Driver-Contract/KERNEL_DRIVER_ARCHITECTURE.md`
> - `Kernel-Driver-Contract/rules/kernel-driver/safety.md`

---

## 核心安全模型

`Kernel-Driver-Contract` 是一條 Windows kernel-mode driver governance slice。

它的核心模型**不是**一般化的「C correctness」，而是：

- **fact-gated driver reasoning**：每個變更必須宣告並保住 IRQL、ownership、與 lifetime 假設
- **lifecycle / state-invariant enforcement**：driver 的 add、start、stop、remove、surprise-remove、cleanup、cancel path 必須全部被視為 first-class behavior
- **18 個 hard-stop safety checks**：由 `irql_safety_validator`、`pageable_section_validator`、與其他 validator 持守

---

## Hard-Stop 安全不變量

### IRQL 邊界（`irql_safety_validator`）

- 在可能高於 `PASSIVE_LEVEL` 的 context（ISR、DPC、completion routine、high-IRQL dispatch）中，**不得**執行 pageable、blocking、或 wait-based operation
- 不得假設 callback 一定跑在 `PASSIVE_LEVEL`；必須明確宣告所需 IRQL，或明確 defer work
- 任何碰到 ISR、DPC、completion routine、work-item、或 dispatch code 的 refactor，都必須保住 high-IRQL 與 passive-level work 之間的 handoff
- 若 task 改變了 locking 或 callback flow，review evidence 必須說明 IRQL 行為仍然安全

**已知 FP 模式（設計決定）**：
- KD-002：structured scan payload 無 dispatch fn 時 fallback 掃 driver_code → 誤報；`is_structured_scan` 判斷避免
- KD-003：PASSIVE_LEVEL function 的 KeWaitForSingleObject → 誤報；proxy scan 空 dispatch bucket 不觸發

### 記憶體邊界（`memory-boundary`）

- 所有 user-mode input、IOCTL payload、DMA buffer、MDL、mapped memory 必須視為 **hostile boundary**
- 在 dereference 或 copy 前，先驗證 buffer length、structure size、與 pointer 假設；不得信任外部提供的 length
- 任何碰到 DMA、MDL、mapped view、或 shared memory 的變更，必須保住 ownership、lifetime、與 cleanup symmetry
- refactor 不得隱藏或削弱防止 use-after-free、double-free、stale mapping、memory-corruption 的檢查

### Cleanup 與 Unwind（`cleanup-unwind`）

- partial initialization 的 failure path 必須釋放所有已取得的 resource（對稱 unwind）
- unload、device-remove、surprise-remove、cancel path 是 **first-class behavior**，不是 best-effort
- refactor 必須保住 rollback order、object ownership、lock-release symmetry
- review evidence 應說明 halfway failure、cleanup、teardown 在變更後仍然安全

### Pageable Section（`pageable_section_validator`）

- pageable code（`PAGED_CODE()`）不得在 DISPATCH_LEVEL 或更高的 IRQL 被呼叫
- 重構不得把原本 nonpaged 的 path 移入 pageable section，或反之
- 已知 ReDoS 模式：header 中 struct 定義觸發 `_FUNC_OPENER` catastrophic backtracking → 加 `PAGED_CODE()` short-circuit 避免

---

## IRP 與 Completion Routine

- IRP completion routine 在 caller context（DISPATCH_LEVEL 或更高）執行；不得有 blocking 行為
- 每個函式須宣告 `irp_compl`（是否為 IRP completion routine）；classified_functions + irp_completion_code bucket 分開追蹤
- IRP 的 IoCompleteRequest 與 IoMarkIrpPending 對稱性必須明確保住
- 若 refactor 改變 IRP flow，必須說明 pending/complete/cancel 三條路徑的 ownership 轉移

---

## AI 行為約束（此 domain 工作時的必要要求）

1. 每次變更必須明確宣告 IRQL 假設：哪個 path 在哪個 IRQL 跑
2. 不得在沒有 fact-based evidence 的情況下宣稱「IRQL safe」
3. 看到 ISR、DPC、completion routine 相關 code，必須停下來問清楚 lifecycle
4. cleanup path 不是 optional；partial init failure 必須有對稱的 unwind
5. memory safety check 不得在 refactor 中被靜默削弱（即使行為看起來未變）

---

## Evidence 要求摘要

| 變更類型 | 必要 evidence |
|---|---|
| ISR / DPC / completion routine | IRQL 宣告 + handoff 說明 |
| Cleanup / unload / remove | halfway failure path 說明 + lock symmetry |
| Memory / buffer / DMA | validation coverage 說明 + ownership lifetime |
| Pageable section 修改 | IRQL context 確認 + PAGED_CODE() 覆蓋確認 |
| IRP flow 改變 | pending/complete/cancel 三路徑說明 |

---

## 一句話結論

Kernel Driver 的核心 invariant 是：**在正確的 IRQL 做正確的事，並在任何退出路徑上都做到對稱 cleanup。** 此 summary 取代全量 contract 注入，保留 reviewer / runtime 真正需要的 domain shape。
