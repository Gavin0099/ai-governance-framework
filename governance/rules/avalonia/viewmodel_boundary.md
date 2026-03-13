# Avalonia ViewModel Boundary

- View models coordinate presentation state; they must not become an unbounded integration layer for I/O or platform logic.
- Native calls, filesystem access, and process launch behavior belong behind services or adapters.
- Headless testability is a governance concern: UI behavior should remain observable without full manual interaction.
