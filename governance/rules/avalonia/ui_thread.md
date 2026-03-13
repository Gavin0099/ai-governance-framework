# Avalonia UI Thread

- UI control mutation and `PropertyChanged` side effects must run on `Dispatcher.UIThread` or an equivalent safe boundary.
- View models should not hide cross-thread UI repair logic as a convenience shortcut.
- If a flow depends on UI-thread affinity, tests should make that dependency visible.
