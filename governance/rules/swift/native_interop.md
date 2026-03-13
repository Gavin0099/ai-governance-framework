# Swift Native Interop

- Objective-C bridging and native platform APIs must remain behind explicit boundaries when they affect domain logic.
- Unsafe pointer or unmanaged resource handling must document ownership and cleanup rules.
- Platform capability checks should not silently leak into higher-level business rules.
