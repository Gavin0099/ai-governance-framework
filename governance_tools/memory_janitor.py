#!/usr/bin/env python3
"""
🧹 Memory Janitor - 記憶壓力監控與安全守護程式
Priority: 8 (Memory Stewardship)

功能:
1. 監控 memory/01_active_task.md 行數
2. 當超過閾值時產出 fail-closed 指引
3. 阻止未經 verified archive + replacement-state cutover 的舊 cleanup 路徑

設計原則:
- 不自動壓縮或改寫 active memory
- 未證明安全 cutover 時拒絕舊 cleanup 路徑
- archive/manifest.json 僅供既有記錄讀寫，不代表 cleanup authority
- 產出人類可讀的稽核報告
"""

import os
import re
import json
from pathlib import Path
from datetime import datetime
from typing import Tuple, List, Dict


class UnsafeCleanupBlocked(RuntimeError):
    """Legacy automatic cleanup cannot prove a safe archive/cutover boundary."""


class MemoryJanitor:
    """記憶掃除執行器"""
    
    # 閾值設定
    HOT_MEMORY_SOFT_LIMIT = 180  # 軟限制:產出警告
    HOT_MEMORY_HARD_LIMIT = 200  # 硬限制:建議掃除
    HOT_MEMORY_CRITICAL = 250    # 緊急限制:強制停止

    HOT_MEMORY_SOFT_SIZE_LIMIT = 8000
    HOT_MEMORY_HARD_SIZE_LIMIT = 10000
    HOT_MEMORY_CRITICAL_SIZE_LIMIT = 12000

    UNSAFE_CLEANUP_MESSAGE = (
        "自動掃除已 fail closed：目前路徑無法證明 verified archive 與 "
        "replacement-state cutover，active memory 未修改。請另行授權並驗證 "
        "archive + replacement-state cutover；不要重試舊的 --clean 或 --execute。"
    )
    
    def __init__(self, memory_root: Path):
        """
        Args:
            memory_root: memory/ 資料夾根目錄路徑
        """
        self.memory_root = Path(memory_root)
        self.active_task_file = self.memory_root / "01_active_task.md"
        self.archive_dir = self.memory_root / "archive"
        
    def check_hot_memory_status(self) -> Tuple[int, int, str]:
        """
        檢查熱記憶狀態
        
        Returns:
            (行數, 字元數, 狀態碼)
            狀態碼: "SAFE" | "WARNING" | "CRITICAL" | "EMERGENCY"
        """
        if not self.active_task_file.exists():
            return 0, 0, "SAFE"
        
        with open(self.active_task_file, 'r', encoding='utf-8') as f:
            content = f.read()
            line_count = len(content.splitlines())
            char_count = len(content)
        
        if line_count >= self.HOT_MEMORY_CRITICAL or char_count >= self.HOT_MEMORY_CRITICAL_SIZE_LIMIT:
            return line_count, char_count, "EMERGENCY"
        elif line_count >= self.HOT_MEMORY_HARD_LIMIT or char_count >= self.HOT_MEMORY_HARD_SIZE_LIMIT:
            return line_count, char_count, "CRITICAL"
        elif line_count >= self.HOT_MEMORY_SOFT_LIMIT or char_count >= self.HOT_MEMORY_SOFT_SIZE_LIMIT:
            return line_count, char_count, "WARNING"
        else:
            return line_count, char_count, "SAFE"
    
    def generate_warning_message(self, line_count: int, char_count: int, status: str) -> str:
        """產出警告訊息 (供 AI 在回應末尾顯示)"""
        if status == "EMERGENCY":
            return (
                f"🚨 **熱記憶緊急超限** ({line_count}/200 行, {char_count}/10000 字元) - "
                "停止增加 active memory；自動掃除已 fail closed，需另行驗證 "
                "archive + replacement-state cutover"
            )
        elif status == "CRITICAL":
            return (
                f"⚠️ **熱記憶超過硬限制** ({line_count}/200 行, {char_count}/10000 字元) - "
                "自動掃除已 fail closed；需另行驗證 archive + replacement-state cutover"
            )
        elif status == "WARNING":
            return (
                f"⚠️ 熱記憶接近上限 ({line_count}/200 行, {char_count}/10000 字元)，"
                "可在自然中斷點評估 verified archive + replacement-state cutover"
            )
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
        line_count, char_count, status = self.check_hot_memory_status()
        archivable = self.analyze_archivable_content()
        
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        report = f"""# 🧹 記憶掃除計畫
**執行時間**: {timestamp}
**當前狀態**: {status} ({line_count} 行, {char_count} 字元)

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
            report += (
                "**停止增加 active memory**；自動掃除已 fail closed，"
                "需另行驗證 archive + replacement-state cutover\n"
            )
        elif status == "CRITICAL":
            report += (
                "自動掃除已 fail closed；需另行驗證 archive + "
                "replacement-state cutover\n"
            )
        elif status == "WARNING":
            report += "在下一個自然中斷點評估 verified archive + replacement-state cutover\n"
        else:
            report += "目前狀態良好,無需掃除\n"
        
        return report
    
    def _load_manifest(self) -> dict:
        """載入 manifest.json（不存在則回傳空結構）。"""
        manifest_path = self.archive_dir / "manifest.json"
        if manifest_path.exists():
            try:
                with open(manifest_path, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except (json.JSONDecodeError, IOError):
                pass
        return {"version": "1.0", "archives": []}

    def _save_manifest(self, manifest: dict) -> None:
        """寫入 manifest.json。"""
        self.archive_dir.mkdir(parents=True, exist_ok=True)
        manifest_path = self.archive_dir / "manifest.json"
        with open(manifest_path, 'w', encoding='utf-8') as f:
            json.dump(manifest, f, ensure_ascii=False, indent=2)

    def execute_cleanup(self, dry_run: bool = True) -> str:
        """
        拒絕舊的自動掃除路徑，直到另行證明安全 cutover。

        Args:
            dry_run: True = 回報 blocked 狀態；不修改任何檔案

        Returns:
            不存在 active memory 時的說明，或 dry-run blocked 報告。

        Raises:
            UnsafeCleanupBlocked: 真實 cleanup 一律 fail closed。
        """
        if not self.active_task_file.exists():
            return "⚠️ active_task.md 不存在,無需掃除"

        if dry_run:
            return f"[BLOCKED] {self.UNSAFE_CLEANUP_MESSAGE}"

        raise UnsafeCleanupBlocked(self.UNSAFE_CLEANUP_MESSAGE)


def main():
    """CLI 入口"""
    import argparse
    import sys

    # Windows 終端機的 UTF-8 相容性
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")

    parser = argparse.ArgumentParser(description="Memory Janitor - 記憶掃除工具")
    parser.add_argument('--memory-root', default='./memory', help='memory/ 目錄路徑')
    parser.add_argument('--check', action='store_true', help='僅檢查狀態')
    parser.add_argument('--plan', action='store_true', help='產出掃除計畫')
    parser.add_argument('--execute', action='store_true', help='舊 cleanup 入口（安全性不足時 fail closed）')
    parser.add_argument('--clean', action='store_true', help=argparse.SUPPRESS)
    parser.add_argument('--dry-run', action='store_true', help='模擬執行 (不實際修改檔案)')
    parser.add_argument('--manifest', action='store_true', help='顯示 archive/manifest.json 內容')
    parser.add_argument('--format', choices=['human', 'json'], default='human', help='輸出格式 (預設: human)')

    args = parser.parse_args()

    janitor = MemoryJanitor(Path(args.memory_root))

    if args.execute or args.clean:
        try:
            result = janitor.execute_cleanup(dry_run=args.dry_run)
        except UnsafeCleanupBlocked as exc:
            print(str(exc), file=sys.stderr)
            raise SystemExit(2) from exc
        print(result)

    elif args.check:
        line_count, char_count, status = janitor.check_hot_memory_status()
        warning = janitor.generate_warning_message(line_count, char_count, status)
        if args.format == 'json':
            print(json.dumps({
                "status": status,
                "line_count": line_count,
                "char_count": char_count,
                "soft_limit": janitor.HOT_MEMORY_SOFT_LIMIT,
                "hard_limit": janitor.HOT_MEMORY_HARD_LIMIT,
                "critical": janitor.HOT_MEMORY_CRITICAL,
                "soft_size_limit": janitor.HOT_MEMORY_SOFT_SIZE_LIMIT,
                "hard_size_limit": janitor.HOT_MEMORY_HARD_SIZE_LIMIT,
                "critical_size_limit": janitor.HOT_MEMORY_CRITICAL_SIZE_LIMIT,
            }, ensure_ascii=False))
        else:
            print(f"狀態: {status} ({line_count} 行, {char_count} 字元)")
            if warning:
                print(warning)

    elif args.plan:
        if args.format == 'json':
            line_count, char_count, status = janitor.check_hot_memory_status()
            archivable = janitor.analyze_archivable_content()
            recommendation_map = {
                "EMERGENCY": "verified_archive_and_replacement_state_cutover_required",
                "CRITICAL": "verified_archive_and_replacement_state_cutover_required",
                "WARNING": "manual_cutover_review_at_next_break",
                "SAFE": "no_action_needed",
            }
            print(json.dumps({
                "status": status,
                "line_count": line_count,
                "char_count": char_count,
                "soft_limit": janitor.HOT_MEMORY_SOFT_LIMIT,
                "hard_limit": janitor.HOT_MEMORY_HARD_LIMIT,
                "critical": janitor.HOT_MEMORY_CRITICAL,
                "soft_size_limit": janitor.HOT_MEMORY_SOFT_SIZE_LIMIT,
                "hard_size_limit": janitor.HOT_MEMORY_HARD_SIZE_LIMIT,
                "critical_size_limit": janitor.HOT_MEMORY_CRITICAL_SIZE_LIMIT,
                "archivable": {
                    "completed_tasks": len(archivable["completed_tasks"]),
                    "obsolete_decisions": len(archivable["obsolete_decisions"]),
                    "archived_references": len(archivable["archived_references"]),
                },
                "recommendation": recommendation_map.get(status, "unknown"),
            }, ensure_ascii=False))
        else:
            plan = janitor.create_archive_plan()
            print(plan)

    elif args.manifest:
        manifest = janitor._load_manifest()
        if args.format == 'json':
            print(json.dumps(manifest, ensure_ascii=False, indent=2))
        else:
            archives = manifest.get("archives", [])
            if not archives:
                print("(尚無歸檔紀錄)")
            else:
                print(f"📚 Archive Manifest — {len(archives)} 筆紀錄\n")
                for entry in archives:
                    print(f"  [{entry['datetime']}] {entry['archive_file']}")
                    print(f"    {entry['original_lines']} → {entry['new_lines']} 行 | {entry['reason']}")

    else:
        # 預設行為:檢查並提示
        line_count, char_count, status = janitor.check_hot_memory_status()
        if status != "SAFE":
            plan = janitor.create_archive_plan()
            print(plan)
        else:
            print(f"✅ 熱記憶狀態良好 ({line_count} 行, {char_count} 字元)")


if __name__ == "__main__":
    main()
