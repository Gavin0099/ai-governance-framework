#!/usr/bin/env python3
"""
📋 Linear Integrator - Linear API 自動整合工具
Priority: 9 (Productivity Tooling)

功能:
1. 從 memory/01_active_task.md 解析任務
2. 自動建立對應的 Linear Issue
3. 雙向同步狀態 (Linear ↔ active_task)

設計原則:
- Linear-First: 優先使用 Linear 作為 Source of Truth
- 審計可追溯: 每個操作都記錄在 memory/03_knowledge_base.md
- 錯誤優雅降級: API 失敗時不影響本地工作流
"""

import os
import re
import json
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional
import urllib.request
import urllib.error


class LinearClient:
    """Linear GraphQL API 客戶端"""
    
    API_ENDPOINT = "https://api.linear.app/graphql"
    
    def __init__(self, api_key: Optional[str] = None):
        """
        Args:
            api_key: Linear API Key (如未提供,從環境變數讀取)
        """
        self.api_key = api_key or os.getenv("LINEAR_API_KEY")
        if not self.api_key:
            raise ValueError(
                "LINEAR_API_KEY 未設定\n"
                "請設定環境變數: export LINEAR_API_KEY='your_key_here'\n"
                "或在 ~/.bashrc 中加入此行"
            )
    
    def _graphql_request(self, query: str, variables: Optional[Dict] = None) -> Dict:
        """
        執行 GraphQL 請求
        
        Args:
            query: GraphQL 查詢字串
            variables: 查詢變數
        
        Returns:
            API 回應 (dict)
        
        Raises:
            urllib.error.HTTPError: API 請求失敗
        """
        payload = {
            "query": query,
            "variables": variables or {}
        }
        
        headers = {
            "Content-Type": "application/json",
            "Authorization": self.api_key
        }
        
        request = urllib.request.Request(
            self.API_ENDPOINT,
            data=json.dumps(payload).encode('utf-8'),
            headers=headers,
            method='POST'
        )
        
        try:
            with urllib.request.urlopen(request) as response:
                return json.loads(response.read().decode('utf-8'))
        except urllib.error.HTTPError as e:
            error_body = e.read().decode('utf-8')
            raise Exception(f"Linear API 錯誤 ({e.code}): {error_body}")
    
    def create_issue(
        self,
        title: str,
        description: str,
        team_id: str,
        priority: int = 2,  # 0=None, 1=Urgent, 2=High, 3=Medium, 4=Low
        labels: Optional[List[str]] = None
    ) -> Dict:
        """
        建立 Linear Issue
        
        Args:
            title: Issue 標題
            description: Issue 描述 (支援 Markdown)
            team_id: Team ID (可從 Linear URL 取得)
            priority: 優先級 (0-4)
            labels: 標籤列表
        
        Returns:
            {
                "id": "issue_uuid",
                "url": "https://linear.app/team/issue/XXX-123",
                "identifier": "XXX-123"
            }
        """
        query = """
        mutation CreateIssue($input: IssueCreateInput!) {
            issueCreate(input: $input) {
                success
                issue {
                    id
                    identifier
                    url
                }
            }
        }
        """
        
        variables = {
            "input": {
                "title": title,
                "description": description,
                "teamId": team_id,
                "priority": priority,
                "labelIds": labels or []
            }
        }
        
        result = self._graphql_request(query, variables)
        
        if result.get("data", {}).get("issueCreate", {}).get("success"):
            issue = result["data"]["issueCreate"]["issue"]
            return {
                "id": issue["id"],
                "url": issue["url"],
                "identifier": issue["identifier"]
            }
        else:
            errors = result.get("errors", [])
            raise Exception(f"建立 Issue 失敗: {errors}")
    
    def get_team_info(self) -> List[Dict]:
        """
        取得所有 Team 資訊
        
        Returns:
            [
                {"id": "team_uuid", "name": "Engineering", "key": "ENG"},
                ...
            ]
        """
        query = """
        query {
            teams {
                nodes {
                    id
                    name
                    key
                }
            }
        }
        """
        
        result = self._graphql_request(query)
        return result.get("data", {}).get("teams", {}).get("nodes", [])
    
    def update_issue_status(self, issue_id: str, state_id: str) -> bool:
        """
        更新 Issue 狀態
        
        Args:
            issue_id: Issue UUID
            state_id: 狀態 UUID (可從 Linear 介面取得)
        
        Returns:
            成功/失敗
        """
        query = """
        mutation UpdateIssue($id: String!, $input: IssueUpdateInput!) {
            issueUpdate(id: $id, input: $input) {
                success
            }
        }
        """
        
        variables = {
            "id": issue_id,
            "input": {"stateId": state_id}
        }
        
        result = self._graphql_request(query, variables)
        return result.get("data", {}).get("issueUpdate", {}).get("success", False)


class LinearIntegrator:
    """Linear 與本地 memory/ 的雙向同步協調器"""
    
    def __init__(self, memory_root: Path, linear_client: LinearClient):
        self.memory_root = Path(memory_root)
        self.active_task_file = self.memory_root / "01_active_task.md"
        self.knowledge_base_file = self.memory_root / "03_knowledge_base.md"
        self.linear = linear_client
    
    def parse_active_task(self) -> List[Dict]:
        """
        從 01_active_task.md 解析待辦任務
        
        Returns:
            [
                {
                    "title": "Task title",
                    "description": "Task details",
                    "is_completed": False,
                    "linear_id": None  # 如果已同步則有 ID
                },
                ...
            ]
        """
        if not self.active_task_file.exists():
            return []
        
        with open(self.active_task_file, 'r', encoding='utf-8') as f:
            content = f.read()
        
        tasks = []
        
        # 匹配 "- [ ] Task description" 或 "- [x] Task description"
        task_pattern = r'- \[([ x])\] (.+?)(?:\n|$)'
        
        for match in re.finditer(task_pattern, content):
            is_completed = match.group(1) == 'x'
            task_text = match.group(2)
            
            # 檢查是否已有 Linear ID (格式: [LINEAR:XXX-123])
            linear_match = re.search(r'\[LINEAR:([A-Z]+-\d+)\]', task_text)
            linear_id = linear_match.group(1) if linear_match else None
            
            # 移除 Linear ID 標記,取得乾淨的標題
            clean_title = re.sub(r'\[LINEAR:[A-Z]+-\d+\]', '', task_text).strip()
            
            tasks.append({
                "title": clean_title,
                "description": clean_title,  # 簡化版,可擴充為讀取詳細描述
                "is_completed": is_completed,
                "linear_id": linear_id
            })
        
        return tasks
    
    def sync_task_to_linear(
        self,
        task: Dict,
        team_id: str,
        priority: int = 2
    ) -> Optional[str]:
        """
        同步單一任務到 Linear
        
        Args:
            task: parse_active_task() 回傳的任務物件
            team_id: Linear Team ID
            priority: 優先級
        
        Returns:
            Linear Issue Identifier (e.g., "ENG-123") 或 None (如失敗)
        """
        if task.get("linear_id"):
            print(f"⏭️  任務已同步: {task['title']} [{task['linear_id']}]")
            return task['linear_id']
        
        try:
            result = self.linear.create_issue(
                title=task['title'],
                description=task['description'],
                team_id=team_id,
                priority=priority
            )
            
            identifier = result['identifier']
            print(f"✅ 建立 Linear Issue: {identifier} - {task['title']}")
            print(f"   URL: {result['url']}")
            
            # 記錄到 knowledge_base
            self._log_sync_event(task['title'], identifier, result['url'])
            
            return identifier
            
        except Exception as e:
            print(f"❌ 同步失敗: {task['title']}")
            print(f"   錯誤: {e}")
            return None
    
    def update_active_task_with_linear_ids(self, task_id_mapping: Dict[str, str]):
        """
        將 Linear ID 寫回 01_active_task.md
        
        Args:
            task_id_mapping: {"Task title": "ENG-123", ...}
        """
        if not self.active_task_file.exists():
            return
        
        with open(self.active_task_file, 'r', encoding='utf-8') as f:
            content = f.read()
        
        for task_title, linear_id in task_id_mapping.items():
            # 尋找對應的任務行並加上 [LINEAR:XXX-123] 標記
            pattern = rf'(- \[ \] {re.escape(task_title)})(?!\[LINEAR:)'
            replacement = rf'\1 [LINEAR:{linear_id}]'
            content = re.sub(pattern, replacement, content)
        
        with open(self.active_task_file, 'w', encoding='utf-8') as f:
            f.write(content)
        
        print(f"✅ 已更新 {len(task_id_mapping)} 個任務的 Linear ID")
    
    def _log_sync_event(self, task_title: str, linear_id: str, url: str):
        """記錄同步事件到 knowledge_base"""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        log_entry = f"""
### Linear Sync: {task_title} ({timestamp})
- **Linear ID**: [{linear_id}]({url})
- **Status**: Created
"""
        
        # Append 到 knowledge_base (如果檔案不存在則建立)
        with open(self.knowledge_base_file, 'a', encoding='utf-8') as f:
            f.write(log_entry)


def main():
    """CLI 入口"""
    import argparse
    
    parser = argparse.ArgumentParser(description="Linear Integrator - Linear API 整合工具")
    parser.add_argument('--memory-root', default='./memory', help='memory/ 目錄路徑')
    parser.add_argument('--list-teams', action='store_true', help='列出所有 Team')
    parser.add_argument('--sync', action='store_true', help='同步所有未完成任務到 Linear')
    parser.add_argument('--team-id', help='Linear Team ID (用於 --sync)')
    parser.add_argument('--priority', type=int, default=2, help='優先級 (0-4, 預設 2=High)')
    
    args = parser.parse_args()
    
    try:
        linear = LinearClient()
        integrator = LinearIntegrator(Path(args.memory_root), linear)
        
        if args.list_teams:
            teams = linear.get_team_info()
            print("📋 可用的 Teams:")
            for team in teams:
                print(f"  - {team['name']} (Key: {team['key']}, ID: {team['id']})")
        
        elif args.sync:
            if not args.team_id:
                print("❌ 錯誤: 請使用 --team-id 指定 Team")
                print("   提示: 先執行 --list-teams 查看可用的 Team ID")
                return
            
            tasks = integrator.parse_active_task()
            incomplete_tasks = [t for t in tasks if not t['is_completed'] and not t['linear_id']]
            
            print(f"📊 找到 {len(incomplete_tasks)} 個未同步的任務")
            
            task_id_mapping = {}
            for task in incomplete_tasks:
                linear_id = integrator.sync_task_to_linear(
                    task,
                    team_id=args.team_id,
                    priority=args.priority
                )
                if linear_id:
                    task_id_mapping[task['title']] = linear_id
            
            if task_id_mapping:
                integrator.update_active_task_with_linear_ids(task_id_mapping)
        
        else:
            parser.print_help()
    
    except ValueError as e:
        print(f"❌ 設定錯誤: {e}")
    except Exception as e:
        print(f"❌ 執行錯誤: {e}")


if __name__ == "__main__":
    main()
