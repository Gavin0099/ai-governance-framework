# C# Native Boundary

- Native interop must stay behind an explicit adapter or boundary interface.
- `DllImport` or native handle management must not leak into domain logic.
- Resource ownership, disposal, and error translation must be explicit and reviewable.
