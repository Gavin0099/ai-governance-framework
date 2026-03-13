# C# Threading Safety

- UI state changes must occur on the correct UI thread or dispatcher boundary.
- Do not treat `async void` as an acceptable default outside explicit event-handler boundaries.
- Cross-thread mutation without a synchronization strategy is a governance violation, not a style issue.
