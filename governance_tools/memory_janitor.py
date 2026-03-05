#!/usr/bin/env python3
"""
🧹 Memory Janitor - 自動記憶掃除守護程式
Priority: 8 (Memory Stewardship)

功能:
1. 監控 memory/01_active_task.md 行數
2. 當超過閾值時產出掃除建議
3. 自動將過期內容歸檔到 memory/archive/

設計原則:
- 完全自動化,無需人工介入
- 保留原始檔案,僅移動 (append-only)
- 產出人類可讀的稽核報告
"""

import os
import re
from pathlib import Path
from datetime import datetime
from typing import Tuple, List, Dict


class MemoryJanitor:
    """記憶掃除執行器"""
    
    # 閾值設定
    HOT_MEMORY_SOFT_LIMIT = 180  # 軟限制:產出警告
    HOT_MEMORY_HARD_LIMIT = 200  # 硬限制:建議掃除
    HOT_MEMORY_CRITICAL = 250    # 緊急限制:強制停止
    
    def __init__(self, memory_root: Path):
        """
        Args:
            memory_root: memory/ 資料夾根目錄路徑
        """
        self.memory_root = Path(memory_root)
        self.active_task_file = self.memory_root / "01_active_task.md"
        self.archive_dir = self.memory_root / "archive"
        self.archive_dir.mkdir(exist_ok=True)
        
    def check_hot_memory_status(self) -> Tuple[int, str]:
        """
        檢查熱記憶狀態
        
        Returns:
            (行數, 狀態碼)
            狀態碼: "SAFE" | "WARNING" | "CRITICAL" | "EMERGENCY"
        """
        if not self.active_task_file.exists():
            return 0, "SAFE"
        
        with open(self.active_task_file, 'r', encoding='utf-8') as f:
            line_count = sum(1 for _ in f)
        
        if line_count >= self.HOT_MEMORY_CRITICAL:
            return line_count, "EMERGENCY"
        elif line_count >= self.HOT_MEMORY_HARD_LIMIT:
            return line_count, "CRITICAL"
        elif line_count >= self.HOT_MEMORY_SOFT_LIMIT:
            return line_count, "WARNING"
        else:
            return line_count, "SAFE"
    
    def generate_warning_message(self, line_count: int, status: str) -> str:
        """產出警告訊息 (供 AI 在回應末尾顯示)"""
        if status == "EMERGENCY":
            return f"🚨 **熱記憶緊急超限** ({line_count}/200 行) - **立即停止任務,強制執行掃除**"
        elif status == "CRITICAL":
            return f"⚠️ **熱記憶超過硬限制** ({line_count}/200 行) - 建議執行 `python memory_janitor.py --clean`"
        elif status == "WARNING":
            return f"⚠️ 熱記憶接近上限 ({line_count}/200 行),建議儘快掃除"
        else:
            return ""
    
    def analyze_archivable_content(self) -> Dict[str, List[str]]:
        """
        分析可歸檔的內容區塊
        
        Returns:
            {
                "completed_tasks": ["## Task 1", "## Task 2"],
                "obsolete_decisions": ["- [Decision] ...", ...],
                "archived_references": ["See ADR-0001", ...]
            }
        """
        if not self.active_task_file.exists():
            return {"completed_tasks": [], "obsolete_decisions": [], "archived_references": []}
        
        with open(self.active_task_file, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # 使用簡單的啟發式規則
        completed_tasks = re.findall(r'##\s+.*?\[x\].*?(?=##|\Z)', content, re.DOTALL)
        obsolete_patterns = [
            r'~~.*?~~',  # 刪除線標記的過期內容
            r'\(Superseded.*?\)',  # 標記為被取代的決策
        ]
        
        obsolete_decisions = []
        for pattern in obsolete_patterns:
            obsolete_decisions.extend(re.findall(pattern, content))
        
        # 尋找 ADR 引用 (表示已正式文件化,可從熱記憶移除)
        archived_references = re.findall(r'ADR-\d{4}', content)
        
        return {
            "completed_tasks": completed_tasks,
            "obsolete_decisions": obsolete_decisions,
            "archived_references": list(set(archived_references))
        }
    
    def create_archive_plan(self) -> str:
        """
        產出歸檔計畫 (Markdown 格式,供人工確認)
        
        Returns:
            Markdown 格式的掃除計畫報告
        """
        line_count, status = self.check_hot_memory_status()
        archivable = self.analyze_archivable_content()
        
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        report = f"""# 🧹 記憶掃除計畫
**執行時間**: {timestamp}
**當前狀態**: {status} ({line_count} 行)

---

## 📊 可歸檔內容分析

### ✅ 已完成任務 ({len(archivable['completed_tasks'])})
"""
        for task in archivable['completed_tasks'][:5]:  # 只顯示前5個
            preview = task[:100].replace('\n', ' ')
            report += f"- {preview}...\n"
        
        report += f"""
### 🗑️ 過期決策 ({len(archivable['obsolete_decisions'])})
"""
        for decision in archivable['obsolete_decisions'][:5]:
            report += f"- {decision}\n"
        
        report += f"""
### 📚 已歸檔引用 ({len(archivable['archived_references'])})
"""
        for ref in archivable['archived_references']:
            report += f"- {ref}\n"
        
        report += f"""
---

## 🎯 建議行動

"""
        if status == "EMERGENCY":
            report += "**立即停止當前任務** → 人工審核並執行掃除 → 重新開始對話\n"
        elif status == "CRITICAL":
            report += "建議執行: `python memory_janitor.py --execute`\n"
        elif status == "WARNING":
            report += "建議在下一個自然中斷點執行掃除\n"
        else:
            report += "目前狀態良好,無需掃除\n"
        
        return report
    
    def execute_cleanup(self, dry_run: bool = True) -> str:
        """
        執行實際掃除 (將內容移至 archive/)
        
        Args:
            dry_run: True = 僅模擬,不實際移動檔案
        
        Returns:
            執行報告
        """
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        archive_file = self.archive_dir / f"active_task_{timestamp}.md"
        
        if dry_run:
            return f"[模擬模式] 將建立歸檔檔案: {archive_file}"
        
        # 實際執行歸檔
        if self.active_task_file.exists():
            with open(self.active_task_file, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # 保留檔案頭部 (前20行) + "## Next Steps" 區塊
            lines = content.split('\n')
            header = '\n'.join(lines[:20])
            
            # 尋找 Next Steps
            next_steps_match = re.search(r'##\s+Next Steps.*?(?=##|\Z)', content, re.DOTALL)
            next_steps = next_steps_match.group(0) if next_steps_match else ""
            
            # 新的精簡版 active_task
            new_content = f"""{header}

---
*[歸檔於 {timestamp}]*

{next_steps}
"""
            
            # 寫入歸檔
            with open(archive_file, 'w', encoding='utf-8') as f:
                f.write(content)
            
            # 更新 active_task
            with open(self.active_task_file, 'w', encoding='utf-8') as f:
                f.write(new_content)
            
            return f"✅ 掃除完成\n- 歸檔: {archive_file}\n- 新熱記憶大小: {len(new_content.split(chr(10)))} 行"
        
        return "⚠️ active_task.md 不存在,無需掃除"


def main():
    """CLI 入口"""
    import argparse
    
    parser = argparse.ArgumentParser(description="Memory Janitor - 記憶掃除工具")
    parser.add_argument('--memory-root', default='./memory', help='memory/ 目錄路徑')
    parser.add_argument('--check', action='store_true', help='僅檢查狀態')
    parser.add_argument('--plan', action='store_true', help='產出掃除計畫')
    parser.add_argument('--execute', action='store_true', help='執行實際掃除')
    parser.add_argument('--dry-run', action='store_true', help='模擬執行 (不實際修改檔案)')
    
    args = parser.parse_args()
    
    janitor = MemoryJanitor(Path(args.memory_root))
    
    if args.check:
        line_count, status = janitor.check_hot_memory_status()
        warning = janitor.generate_warning_message(line_count, status)
        print(f"狀態: {status} ({line_count} 行)")
        if warning:
            print(warning)
    
    elif args.plan:
        plan = janitor.create_archive_plan()
        print(plan)
    
    elif args.execute:
        result = janitor.execute_cleanup(dry_run=args.dry_run)
        print(result)
    
    else:
        # 預設行為:檢查並提示
        line_count, status = janitor.check_hot_memory_status()
        if status != "SAFE":
            plan = janitor.create_archive_plan()
            print(plan)
        else:
            print(f"✅ 熱記憶狀態良好 ({line_count} 行)")


if __name__ == "__main__":
    main()
