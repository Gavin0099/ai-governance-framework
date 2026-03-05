#!/bin/bash
# 一鍵部署治理架構整合包到 memory/ 層

set -e  # 遇到錯誤立即停止

echo "🚀 開始部署治理架構整合包..."

# 檢查目標目錄
if [ ! -d "memory" ]; then
    echo "❌ 錯誤: 當前目錄下找不到 memory/ 資料夾"
    echo "   請在專案根目錄執行此腳本"
    exit 1
fi

# 備份現有 SYSTEM_PROMPT.md
if [ -f "memory/governance/SYSTEM_PROMPT.md" ]; then
    BACKUP_FILE="memory/governance/SYSTEM_PROMPT_$(date +%Y%m%d_%H%M%S)_backup.md"
    echo "📦 備份現有 SYSTEM_PROMPT.md → $BACKUP_FILE"
    cp memory/governance/SYSTEM_PROMPT.md "$BACKUP_FILE"
fi

# 部署更新後的核心文件
echo "📝 部署 SYSTEM_PROMPT.md v5.2..."
cp governance_integration_package/SYSTEM_PROMPT_v5.2.md \
   memory/governance/SYSTEM_PROMPT.md

# 建立工具目錄
echo "🔧 建立 governance_tools/ 目錄..."
mkdir -p memory/governance_tools

# 部署工具腳本
echo "📋 複製工具腳本..."
cp governance_integration_package/governance_tools/memory_janitor.py \
   memory/governance_tools/
cp governance_integration_package/governance_tools/linear_integrator.py \
   memory/governance_tools/
cp governance_integration_package/README.md \
   memory/governance_tools/

# 設定執行權限
chmod +x memory/governance_tools/*.py

# 建立文件目錄
echo "📚 建立 docs/ 目錄..."
mkdir -p memory/docs

# 部署整合指南
echo "📖 複製整合指南..."
cp governance_integration_package/INTEGRATION_GUIDE.md \
   memory/docs/

# 建立歸檔目錄
echo "🗂️  建立 archive/ 目錄..."
mkdir -p memory/archive

# 驗證部署
echo ""
echo "✅ 部署完成! 目錄結構:"
echo ""
echo "memory/"
echo "├── governance/"
echo "│   ├── SYSTEM_PROMPT.md (v5.2) ✨"
echo "│   └── ... (其他 6 個治理文件)"
echo "├── governance_tools/ ✨"
echo "│   ├── README.md"
echo "│   ├── memory_janitor.py"
echo "│   └── linear_integrator.py"
echo "├── docs/ ✨"
echo "│   └── INTEGRATION_GUIDE.md"
echo "├── 00_master_plan.md"
echo "├── 01_active_task.md"
echo "├── 02_tech_stack.md"
echo "├── 03_knowledge_base.md"
echo "└── archive/ ✨"
echo ""
echo "🧪 驗證安裝:"
echo "  python memory/governance_tools/memory_janitor.py --check"
echo ""
echo "📚 詳細文件:"
echo "  memory/docs/INTEGRATION_GUIDE.md"
echo ""
