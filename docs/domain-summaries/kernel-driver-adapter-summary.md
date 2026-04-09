# Kernel-Driver Domain Adapter Summary

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

## Overview

`Kernel-Driver-Contract` 是一條 Windows kernel-driver governance slice。

它的核心模型不是一般化的「C correctness」，而是：

- fact-gated driver reasoning
- lifecycle / state-invariant enforcement
- 對 IRQL、ISR/DPC、IRP、sync primitive、static-analysis、unit-test boundary 的 hard-stop safety rules

---

## 一句話結論

這份 summary 的用途，是在不重送整份 rich contract 的情況下，保留 reviewer / runtime 真正需要的 kernel-driver domain shape。
