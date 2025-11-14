#!/usr/bin/env python3
"""
用語集投稿の状態管理モジュール

このモジュールは、用語集（spells/potions）の投稿履歴を管理し、
重複投稿を防ぐために使用されます。

状態はGitHub Gistに保存され、すべての用語を投稿したらリセットされます。
"""

import os
import json
import random
from typing import Dict, List, Optional, Set
from datetime import datetime
from pathlib import Path

import requests


class StateManager:
    """用語集投稿の状態を管理するクラス"""

    def __init__(self, gist_id: Optional[str] = None, github_token: Optional[str] = None):
        """
        初期化

        Args:
            gist_id: GitHub Gist ID（環境変数 GLOSSARY_STATE_GIST_ID から取得可能）
            github_token: GitHub Personal Access Token（環境変数 GIST_TOKEN または GITHUB_TOKEN から取得可能）
        """
        self.gist_id = gist_id or os.getenv('GLOSSARY_STATE_GIST_ID')
        self.github_token = github_token or os.getenv('GIST_TOKEN') or os.getenv('GITHUB_TOKEN')
        self.state = self._load_state()

    def _load_state(self) -> Dict:
        """
        GitHub Gistから状態を読み込む

        Returns:
            状態データ。Gistが存在しない場合は空の状態を返す
        """
        if not self.gist_id or not self.github_token:
            print("Warning: GitHub Gist設定がありません。ローカルファイルを使用します。")
            return self._load_local_state()

        try:
            url = f"https://api.github.com/gists/{self.gist_id}"
            headers = {
                "Authorization": f"token {self.github_token}",
                "Accept": "application/vnd.github.v3+json"
            }
            response = requests.get(url, headers=headers, timeout=10)

            if response.status_code == 200:
                gist_data = response.json()
                state_content = gist_data['files']['glossary_state.json']['content']
                return json.loads(state_content)
            elif response.status_code == 404:
                print("Gistが見つかりません。新しい状態を作成します。")
                return self._create_initial_state()
            else:
                print(f"Warning: Gist読み込みエラー（ステータス: {response.status_code}）")
                return self._load_local_state()

        except Exception as e:
            print(f"Warning: Gist読み込み中にエラーが発生しました: {e}")
            return self._load_local_state()

    def _load_local_state(self) -> Dict:
        """
        ローカルファイルから状態を読み込む（フォールバック）

        Returns:
            状態データ
        """
        project_root = Path(__file__).parent.parent
        state_file = project_root / 'data' / 'glossary_state.json'

        if state_file.exists():
            with open(state_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        else:
            return self._create_initial_state()

    def _create_initial_state(self) -> Dict:
        """
        初期状態を作成

        Returns:
            初期状態データ
        """
        return {
            "posted_spells": [],
            "posted_potions": [],
            "last_spell_posted": None,
            "last_potion_posted": None,
            "last_updated": datetime.utcnow().isoformat() + "Z",
            "cycle_count": {
                "spells": 0,
                "potions": 0
            }
        }

    def _save_state(self):
        """状態をGitHub Gistまたはローカルファイルに保存"""
        self.state['last_updated'] = datetime.utcnow().isoformat() + "Z"

        if not self.gist_id or not self.github_token:
            self._save_local_state()
            return

        try:
            url = f"https://api.github.com/gists/{self.gist_id}"
            headers = {
                "Authorization": f"token {self.github_token}",
                "Accept": "application/vnd.github.v3+json"
            }
            data = {
                "files": {
                    "glossary_state.json": {
                        "content": json.dumps(self.state, indent=2, ensure_ascii=False)
                    }
                }
            }
            response = requests.patch(url, headers=headers, json=data, timeout=10)

            if response.status_code == 200:
                print("✓ 状態をGistに保存しました")
            else:
                print(f"Warning: Gist保存エラー（ステータス: {response.status_code}）")
                self._save_local_state()

        except Exception as e:
            print(f"Warning: Gist保存中にエラーが発生しました: {e}")
            self._save_local_state()

    def _save_local_state(self):
        """ローカルファイルに状態を保存（フォールバック）"""
        project_root = Path(__file__).parent.parent
        state_file = project_root / 'data' / 'glossary_state.json'

        # data ディレクトリが存在しない場合は作成
        state_file.parent.mkdir(parents=True, exist_ok=True)

        with open(state_file, 'w', encoding='utf-8') as f:
            json.dump(self.state, f, indent=2, ensure_ascii=False)
        print(f"✓ 状態をローカルファイルに保存しました: {state_file}")

    def get_available_items(self, category: str, all_items: List[Dict]) -> List[Dict]:
        """
        投稿可能なアイテムのリストを取得

        Args:
            category: 'spell' または 'potion'
            all_items: すべてのアイテムのリスト

        Returns:
            まだ投稿していないアイテムのリスト。すべて投稿済みの場合はリセットして全アイテムを返す
        """
        posted_key = f"posted_{category}s"
        posted_ids = set(self.state.get(posted_key, []))
        all_ids = {item['id'] for item in all_items}

        # まだ投稿していないアイテムを抽出
        available_ids = all_ids - posted_ids

        # すべて投稿済みの場合はリセット
        if not available_ids:
            print(f"✓ すべての{category}を投稿しました。サイクルをリセットします。")
            self.state[posted_key] = []
            self.state['cycle_count'][f"{category}s"] += 1
            available_ids = all_ids

        return [item for item in all_items if item['id'] in available_ids]

    def mark_as_posted(self, category: str, item_id: str):
        """
        アイテムを投稿済みとしてマーク

        Args:
            category: 'spell' または 'potion'
            item_id: アイテムのID
        """
        posted_key = f"posted_{category}s"
        last_posted_key = f"last_{category}_posted"

        if item_id not in self.state[posted_key]:
            self.state[posted_key].append(item_id)

        self.state[last_posted_key] = {
            "id": item_id,
            "timestamp": datetime.utcnow().isoformat() + "Z"
        }

        self._save_state()

    def get_random_available_item(self, category: str, all_items: List[Dict]) -> Optional[Dict]:
        """
        投稿可能なアイテムからランダムに1つ選択

        Args:
            category: 'spell' または 'potion'
            all_items: すべてのアイテムのリスト

        Returns:
            選択されたアイテム。利用可能なアイテムがない場合はNone
        """
        available = self.get_available_items(category, all_items)

        if not available:
            return None

        return random.choice(available)

    def get_stats(self) -> Dict:
        """
        投稿統計を取得

        Returns:
            統計情報の辞書
        """
        return {
            "spells": {
                "posted": len(self.state.get('posted_spells', [])),
                "cycles": self.state.get('cycle_count', {}).get('spells', 0),
                "last_posted": self.state.get('last_spell_posted')
            },
            "potions": {
                "posted": len(self.state.get('posted_potions', [])),
                "cycles": self.state.get('cycle_count', {}).get('potions', 0),
                "last_posted": self.state.get('last_potion_posted')
            },
            "last_updated": self.state.get('last_updated')
        }


def create_gist(github_token: str, description: str = "Potterpedia Bot Glossary State") -> str:
    """
    新しいGistを作成（初回セットアップ用）

    Args:
        github_token: GitHub Personal Access Token
        description: Gistの説明

    Returns:
        作成されたGistのID

    Raises:
        Exception: Gist作成に失敗した場合
    """
    url = "https://api.github.com/gists"
    headers = {
        "Authorization": f"token {github_token}",
        "Accept": "application/vnd.github.v3+json"
    }

    initial_state = {
        "posted_spells": [],
        "posted_potions": [],
        "last_spell_posted": None,
        "last_potion_posted": None,
        "last_updated": datetime.utcnow().isoformat() + "Z",
        "cycle_count": {
            "spells": 0,
            "potions": 0
        }
    }

    data = {
        "description": description,
        "public": False,  # プライベートGist
        "files": {
            "glossary_state.json": {
                "content": json.dumps(initial_state, indent=2, ensure_ascii=False)
            }
        }
    }

    response = requests.post(url, headers=headers, json=data, timeout=10)

    if response.status_code == 201:
        gist_data = response.json()
        gist_id = gist_data['id']
        print(f"✓ Gistを作成しました: {gist_id}")
        print(f"  URL: {gist_data['html_url']}")
        print(f"\n環境変数に以下を追加してください:")
        print(f"GLOSSARY_STATE_GIST_ID={gist_id}")
        return gist_id
    else:
        raise Exception(f"Gist作成に失敗しました: {response.status_code} - {response.text}")


if __name__ == '__main__':
    """
    スタンドアロン実行時の動作（初回セットアップ用）
    """
    import sys
    from dotenv import load_dotenv

    load_dotenv()

    if len(sys.argv) > 1 and sys.argv[1] == 'create-gist':
        # Gist作成モード
        token = os.getenv('GIST_TOKEN') or os.getenv('GITHUB_TOKEN')
        if not token:
            print("Error: GIST_TOKEN または GITHUB_TOKEN 環境変数が設定されていません")
            sys.exit(1)

        try:
            gist_id = create_gist(token)
            print(f"\n✓ セットアップ完了")
        except Exception as e:
            print(f"✗ エラー: {e}")
            sys.exit(1)

    else:
        # 状態確認モード
        manager = StateManager()
        stats = manager.get_stats()

        print("=== 用語集投稿状態 ===\n")
        print(f"呪文:")
        print(f"  投稿済み: {stats['spells']['posted']} 個")
        print(f"  サイクル数: {stats['spells']['cycles']} 周")
        if stats['spells']['last_posted']:
            print(f"  最終投稿: {stats['spells']['last_posted']['timestamp']}")

        print(f"\nポーション:")
        print(f"  投稿済み: {stats['potions']['posted']} 個")
        print(f"  サイクル数: {stats['potions']['cycles']} 周")
        if stats['potions']['last_posted']:
            print(f"  最終投稿: {stats['potions']['last_posted']['timestamp']}")

        print(f"\n最終更新: {stats['last_updated']}")
