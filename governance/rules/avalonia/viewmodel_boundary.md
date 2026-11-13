# Avalonia ViewModel Boundary

- ViewModel 的職責是協調 presentation state；它不應變成無邊界的 I/O 或 platform logic integration layer。
- native call、filesystem access、與 process launch 行為應放在 service 或 adapter 後面。
- headless testability 是 governance concern：UI behavior 應能在不靠完整人工互動的情況下被觀測。

## MVVM 實作建議

- 已採用 MVVM 的模組，建議沿用既有的屬性通知與命令慣例，並確認繫結值及命令可用狀態會隨相關狀態更新。手寫與 source generator 皆可，由專案選擇實作方式與套件。
- 焦點、動畫與拖曳等純 View 互動可留在 code-behind。
