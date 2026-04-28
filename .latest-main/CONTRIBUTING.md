# 貢獻指南

感謝你考慮為 AI Governance Framework 做出貢獻! 🎉

---

## 🤝 貢獻方式

### 1. 回報問題 (Bug Reports)

如果你發現問題,請 [開啟 Issue](https://github.com/GavinWu672/ai-governance-framework/issues/new) 並包含:

- **問題描述**: 清楚描述發生了什麼
- **重現步驟**: 如何重現這個問題
- **預期行為**: 你期望發生什麼
- **實際行為**: 實際發生了什麼
- **環境資訊**: OS, AI 版本等

### 2. 建議新功能 (Feature Requests)

有好點子? [開啟 Issue](https://github.com/GavinWu672/ai-governance-framework/issues/new) 並說明:

- **功能描述**: 你想要什麼功能
- **使用場景**: 為什麼需要這個功能
- **預期效果**: 這個功能如何幫助使用者

### 3. 改善文件 (Documentation)

文件永遠可以更好! 你可以:

- 修正錯字或語法錯誤
- 補充遺漏的資訊
- 新增範例或教學
- 翻譯文件 (英文版)

### 4. 分享案例 (Case Studies)

使用這個框架完成專案? [分享你的經驗](https://github.com/GavinWu672/ai-governance-framework/discussions/new)!

我們歡迎:
- 實際專案案例
- 遇到的挑戰與解決方案
- PLAN.md 範例
- 最佳實踐

---

## 🔧 Pull Request 流程

### 步驟 1: Fork 專案

在 GitHub 點擊 "Fork" 按鈕

### 步驟 2: Clone 到本地

```bash
git clone https://github.com/YOUR_USERNAME/ai-governance-framework.git
cd ai-governance-framework
```

### 步驟 3: 建立 Branch

```bash
git checkout -b feature/amazing-feature
# 或
git checkout -b fix/bug-description
# 或
git checkout -b docs/improve-readme
```

### 步驟 4: 進行修改

- 遵循現有的代碼風格
- 保持 commit 訊息清晰
- 更新相關文件

### 步驟 5: Commit

```bash
git add .
git commit -m "feat: Add amazing feature"
```

**Commit 訊息規範**:
- `feat:` - 新功能
- `fix:` - 修復問題
- `docs:` - 文件修改
- `style:` - 格式調整
- `refactor:` - 重構
- `test:` - 測試相關
- `chore:` - 其他雜項

### 步驟 6: Push

```bash
git push origin feature/amazing-feature
```

### 步驟 7: 開啟 Pull Request

1. 到你的 Fork 專案頁面
2. 點擊 "Compare & pull request"
3. 填寫 PR 描述
4. 提交 PR

---

## 📋 PR Checklist

- [ ] 程式碼可以正常運行
- [ ] 已更新相關文件
- [ ] Commit 訊息清晰明確
- [ ] 沒有新增不必要的檔案
- [ ] 遵循現有的專案結構

---

## 🙏 感謝你的貢獻!

每一個貢獻都讓這個專案變得更好。❤️
---

## Claude Skills

This repo also includes Claude-local skills under [`.claude/skills/`](./.claude/skills/) with an index at [`.claude/README.md`](./.claude/README.md).

If you add or refine a repo-local skill:

- keep the skill narrow and workflow-specific
- write trigger logic into `SKILL.md` frontmatter `description`
- keep detailed commands and gotchas in `references/`
- add `assets/` only when reusable templates are genuinely useful
- avoid duplicating large sections of `README.md`
