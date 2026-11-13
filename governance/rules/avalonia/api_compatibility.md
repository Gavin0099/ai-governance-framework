# Avalonia API Compatibility

## API 相容性要求

- 新增或移植 Avalonia UI 時，先確認目標專案引用的 Avalonia 套件與版本。XAML、控制項和事件處理須使用該版本支援的 API。
- WPF 專用的控制項、`DependencyProperty`、`Style.Triggers` 與 `ControlTemplate.Triggers` 不可直接搬入 Avalonia UI。依需求選用 Avalonia 控制項、屬性系統、樣式 selector、pseudo-class 或 binding。共用的 .NET 介面（例如 `System.Windows.Input.ICommand`）可照常使用。
- 移植 MFC UI 時，將 message map、控制項通知與資料交換對應到目標 Avalonia 版本支援的 event、command 或 binding。

參考 [Avalonia WPF 遷移指南](https://docs.avaloniaui.net/docs/migration/wpf/) 與 [Avalonia 11 遷移指南](https://v11.docs.avaloniaui.net/docs/get-started/wpf/)。
