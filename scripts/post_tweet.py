#!/usr/bin/env python3
"""
X (Twitter) 投稿スクリプト

このスクリプトは誕生日・命日・イベント・用語集のツイートを投稿します。

使用例:
    # 今日の誕生日・命日・イベントを投稿（Dry-run）
    python scripts/post_tweet.py --dry-run today

    # 特定の日付のイベントを投稿
    python scripts/post_tweet.py event 1998-05-02

    # ランダムに呪文を投稿
    python scripts/post_tweet.py spell

    # ランダムにポーションを投稿
    python scripts/post_tweet.py potion

    # ランダムに魔法生物を投稿
    python scripts/post_tweet.py creature

    # ランダムに用語集（呪文・ポーション・魔法生物）を投稿
    python scripts/post_tweet.py glossary

    # テスト投稿
    python scripts/post_tweet.py test "テストツイート"
"""

import os
import sys
import json
import random
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict, Any

import tweepy
from dotenv import load_dotenv

# 状態管理モジュールをインポート
try:
    from state_manager import StateManager
    STATE_MANAGEMENT_AVAILABLE = True
except ImportError:
    STATE_MANAGEMENT_AVAILABLE = False
    print("Warning: state_manager.py が見つかりません。状態管理機能は無効です。")


class XPoster:
    """X (Twitter) への投稿を管理するクラス"""

    def __init__(self, dry_run: bool = False):
        """
        初期化

        Args:
            dry_run: Trueの場合、実際には投稿せずログ出力のみ
        """
        self.dry_run = dry_run
        self.client = None

        if not dry_run:
            self._setup_client()

    def _setup_client(self):
        """X APIクライアントのセットアップ"""
        # 環境変数の読み込み
        load_dotenv()

        # 必須の環境変数をチェック
        required_vars = [
            'X_API_KEY',
            'X_API_KEY_SECRET',
            'X_ACCESS_TOKEN',
            'X_ACCESS_TOKEN_SECRET'
        ]

        missing_vars = [var for var in required_vars if not os.getenv(var)]
        if missing_vars:
            raise ValueError(
                f"必要な環境変数が設定されていません: {', '.join(missing_vars)}\n"
                f".envファイルを作成してください（.env.exampleを参考に）"
            )

        # Tweepy v2 クライアントの作成
        try:
            self.client = tweepy.Client(
                bearer_token=os.getenv('X_BEARER_TOKEN'),
                consumer_key=os.getenv('X_API_KEY'),
                consumer_secret=os.getenv('X_API_KEY_SECRET'),
                access_token=os.getenv('X_ACCESS_TOKEN'),
                access_token_secret=os.getenv('X_ACCESS_TOKEN_SECRET')
            )
            print("✓ X APIクライアントの初期化に成功しました")
        except Exception as e:
            raise Exception(f"X APIクライアントの初期化に失敗しました: {e}")

    def post_tweet(self, text: str) -> Optional[Dict[str, Any]]:
        """
        ツイートを投稿

        Args:
            text: 投稿するテキスト

        Returns:
            投稿成功時はレスポンスデータ、失敗時はNone
        """
        if self.dry_run:
            print(f"\n[DRY RUN] 以下の内容を投稿します:")
            print(f"{'='*50}")
            print(text)
            print(f"{'='*50}")
            print(f"文字数: {len(text)} 文字")
            return {"dry_run": True, "text": text}

        try:
            # ツイート文字数チェック（Xは280文字まで、日本語は全角1文字=1文字）
            if len(text) > 280:
                raise ValueError(f"ツイートが長すぎます（{len(text)}文字 > 280文字）")

            # ツイート投稿
            response = self.client.create_tweet(text=text)

            print(f"✓ ツイートの投稿に成功しました")
            print(f"  ID: {response.data['id']}")

            return response.data

        except tweepy.TweepyException as e:
            print(f"✗ ツイートの投稿に失敗しました: {e}", file=sys.stderr)
            return None
        except Exception as e:
            print(f"✗ 予期しないエラーが発生しました: {e}", file=sys.stderr)
            return None


def load_data_file(file_path: Path) -> Dict[str, Any]:
    """JSONデータファイルを読み込む"""
    if not file_path.exists():
        raise FileNotFoundError(f"データファイルが見つかりません: {file_path}")

    with open(file_path, 'r', encoding='utf-8') as f:
        return json.load(f)


def post_birthday(date_str: str, dry_run: bool = False) -> bool:
    """
    指定した日付の誕生日ツイートを投稿

    Args:
        date_str: 日付文字列（YYYY-MM-DD形式）
        dry_run: Trueの場合、実際には投稿せずログ出力のみ

    Returns:
        投稿成功時はTrue
    """
    # プロジェクトルートディレクトリを取得
    project_root = Path(__file__).parent.parent
    birthdays_file = project_root / 'data' / 'posts' / 'birthdays.json'

    # データファイル読み込み
    data = load_data_file(birthdays_file)

    # 該当する誕生日を検索
    target_date = datetime.strptime(date_str, '%Y-%m-%d')
    date_key = f"{target_date.month:02d}-{target_date.day:02d}"

    matches = [
        entry for entry in data['data']
        if entry['birthday'].endswith(date_key)
    ]

    if not matches:
        print(f"指定した日付（{date_str}）の誕生日データが見つかりません")
        return False

    # ツイート投稿
    poster = XPoster(dry_run=dry_run)
    success = True

    for entry in matches:
        result = poster.post_tweet(entry['tweet_text_ja'])
        if result is None:
            success = False

    return success


def post_deathday(date_str: str, dry_run: bool = False) -> bool:
    """
    指定した日付の命日ツイートを投稿

    Args:
        date_str: 日付文字列（YYYY-MM-DD形式）
        dry_run: Trueの場合、実際には投稿せずログ出力のみ

    Returns:
        投稿成功時はTrue
    """
    # プロジェクトルートディレクトリを取得
    project_root = Path(__file__).parent.parent
    deathdays_file = project_root / 'data' / 'posts' / 'deathdays.json'

    # データファイル読み込み
    data = load_data_file(deathdays_file)

    # 該当する命日を検索
    target_date = datetime.strptime(date_str, '%Y-%m-%d')
    date_key = f"{target_date.month:02d}-{target_date.day:02d}"

    matches = [
        entry for entry in data['data']
        if entry['deathday'].endswith(date_key)
    ]

    if not matches:
        print(f"指定した日付（{date_str}）の命日データが見つかりません")
        return False

    # ツイート投稿
    poster = XPoster(dry_run=dry_run)
    success = True

    for entry in matches:
        result = poster.post_tweet(entry['tweet_text_ja'])
        if result is None:
            success = False

    return success


def post_event(date_str: str, dry_run: bool = False) -> bool:
    """
    指定した日付のイベントツイートを投稿

    Args:
        date_str: 日付文字列（YYYY-MM-DD形式）
        dry_run: Trueの場合、実際には投稿せずログ出力のみ

    Returns:
        投稿成功時はTrue
    """
    # プロジェクトルートディレクトリを取得
    project_root = Path(__file__).parent.parent
    events_file = project_root / 'data' / 'posts' / 'events.json'

    # データファイル読み込み
    data = load_data_file(events_file)

    # 該当するイベントを検索
    target_date = datetime.strptime(date_str, '%Y-%m-%d')
    date_key = f"{target_date.month:02d}-{target_date.day:02d}"

    matches = [
        entry for entry in data['data']
        if entry['event_date'].endswith(date_key)
    ]

    if not matches:
        print(f"指定した日付（{date_str}）のイベントデータが見つかりません")
        return False

    # ツイート投稿
    poster = XPoster(dry_run=dry_run)
    success = True

    for entry in matches:
        result = poster.post_tweet(entry['tweet_text_ja'])
        if result is None:
            success = False

    return success


def post_today(dry_run: bool = False, categories: Optional[list] = None) -> bool:
    """
    今日の誕生日・命日・イベントツイートを投稿

    Args:
        dry_run: Trueの場合、実際には投稿せずログ出力のみ
        categories: 投稿するカテゴリーのリスト。Noneの場合はすべて投稿
                   例: ['birthday', 'deathday', 'event']

    Returns:
        投稿成功時はTrue
    """
    # デフォルトではすべてのカテゴリーを投稿
    if categories is None:
        categories = ['birthday', 'deathday', 'event']

    today = datetime.now().strftime('%Y-%m-%d')
    print(f"今日の日付: {today}")
    print(f"投稿カテゴリー: {', '.join(categories)}")

    success = True

    # 誕生日ツイート
    if 'birthday' in categories:
        print("\n=== 誕生日ツイート ===")
        if not post_birthday(today, dry_run=dry_run):
            print("該当なし")

    # 命日ツイート
    if 'deathday' in categories:
        print("\n=== 命日ツイート ===")
        if not post_deathday(today, dry_run=dry_run):
            print("該当なし")

    # イベントツイート
    if 'event' in categories:
        print("\n=== イベントツイート ===")
        if not post_event(today, dry_run=dry_run):
            print("該当なし")

    return success


def post_spell(spell_id: Optional[str] = None, dry_run: bool = False, use_state: bool = True) -> bool:
    """
    呪文ツイートを投稿

    Args:
        spell_id: 特定の呪文ID（UUIDまたはslug）。Noneの場合はランダム選択
        dry_run: Trueの場合、実際には投稿せずログ出力のみ
        use_state: 状態管理を使用するかどうか（重複投稿防止）

    Returns:
        投稿成功時はTrue
    """
    # プロジェクトルートディレクトリを取得
    project_root = Path(__file__).parent.parent
    spells_file = project_root / 'data' / 'posts' / 'spells.json'

    # データファイル読み込み
    data = load_data_file(spells_file)

    # 呪文を選択
    if spell_id:
        # ID指定の場合、該当する呪文を検索
        matches = [
            entry for entry in data['data']
            if entry.get('id') == spell_id or entry.get('slug') == spell_id
        ]
        if not matches:
            print(f"指定されたID（{spell_id}）の呪文が見つかりません")
            return False
        entry = matches[0]
    else:
        # ランダム選択（状態管理を使用する場合は未投稿のものから選択）
        if use_state and STATE_MANAGEMENT_AVAILABLE:
            state_manager = StateManager()
            entry = state_manager.get_random_available_item('spell', data['data'])
            if not entry:
                print("利用可能な呪文がありません")
                return False
        else:
            entry = random.choice(data['data'])

    # ツイート投稿
    poster = XPoster(dry_run=dry_run)
    result = poster.post_tweet(entry['tweet_text_ja'])

    if result:
        print(f"✓ 呪文: {entry.get('name_ja') or entry.get('name_en')}")

        # 投稿成功時、状態を更新
        if use_state and STATE_MANAGEMENT_AVAILABLE and not dry_run:
            state_manager = StateManager()
            state_manager.mark_as_posted('spell', entry['id'])

        return True
    return False


def post_potion(potion_id: Optional[str] = None, dry_run: bool = False, use_state: bool = True) -> bool:
    """
    ポーションツイートを投稿

    Args:
        potion_id: 特定のポーションID（UUIDまたはslug）。Noneの場合はランダム選択
        dry_run: Trueの場合、実際には投稿せずログ出力のみ
        use_state: 状態管理を使用するかどうか（重複投稿防止）

    Returns:
        投稿成功時はTrue
    """
    # プロジェクトルートディレクトリを取得
    project_root = Path(__file__).parent.parent
    potions_file = project_root / 'data' / 'posts' / 'potions.json'

    # データファイル読み込み
    data = load_data_file(potions_file)

    # ポーションを選択
    if potion_id:
        # ID指定の場合、該当するポーションを検索
        matches = [
            entry for entry in data['data']
            if entry.get('id') == potion_id or entry.get('slug') == potion_id
        ]
        if not matches:
            print(f"指定されたID（{potion_id}）のポーションが見つかりません")
            return False
        entry = matches[0]
    else:
        # ランダム選択（状態管理を使用する場合は未投稿のものから選択）
        if use_state and STATE_MANAGEMENT_AVAILABLE:
            state_manager = StateManager()
            entry = state_manager.get_random_available_item('potion', data['data'])
            if not entry:
                print("利用可能なポーションがありません")
                return False
        else:
            entry = random.choice(data['data'])

    # ツイート投稿
    poster = XPoster(dry_run=dry_run)
    result = poster.post_tweet(entry['tweet_text_ja'])

    if result:
        print(f"✓ ポーション: {entry.get('name_ja') or entry.get('name_en')}")

        # 投稿成功時、状態を更新
        if use_state and STATE_MANAGEMENT_AVAILABLE and not dry_run:
            state_manager = StateManager()
            state_manager.mark_as_posted('potion', entry['id'])

        return True
    return False


def post_creature(creature_id: Optional[str] = None, dry_run: bool = False, use_state: bool = True) -> bool:
    """
    魔法生物ツイートを投稿

    Args:
        creature_id: 特定の魔法生物ID（UUIDまたはslug）。Noneの場合はランダム選択
        dry_run: Trueの場合、実際には投稿せずログ出力のみ
        use_state: 状態管理を使用するかどうか（重複投稿防止）

    Returns:
        投稿成功時はTrue
    """
    # プロジェクトルートディレクトリを取得
    project_root = Path(__file__).parent.parent
    creatures_file = project_root / 'data' / 'posts' / 'creatures.json'

    # データファイル読み込み
    data = load_data_file(creatures_file)

    # 魔法生物を選択
    if creature_id:
        # ID指定の場合、該当する魔法生物を検索
        matches = [
            entry for entry in data['data']
            if entry.get('id') == creature_id or entry.get('slug') == creature_id
        ]
        if not matches:
            print(f"指定されたID（{creature_id}）の魔法生物が見つかりません")
            return False
        entry = matches[0]
    else:
        # ランダム選択（状態管理を使用する場合は未投稿のものから選択）
        if use_state and STATE_MANAGEMENT_AVAILABLE:
            state_manager = StateManager()
            entry = state_manager.get_random_available_item('creature', data['data'])
            if not entry:
                print("利用可能な魔法生物がありません")
                return False
        else:
            entry = random.choice(data['data'])

    # ツイート投稿
    poster = XPoster(dry_run=dry_run)
    result = poster.post_tweet(entry['tweet_text_ja'])

    if result:
        print(f"✓ 魔法生物: {entry.get('name_ja') or entry.get('name_en')}")

        # 投稿成功時、状態を更新
        if use_state and STATE_MANAGEMENT_AVAILABLE and not dry_run:
            state_manager = StateManager()
            state_manager.mark_as_posted('creature', entry['id'])

        return True
    return False


def post_glossary(dry_run: bool = False) -> bool:
    """
    用語集（呪文・ポーション・魔法生物）をランダムに投稿

    Args:
        dry_run: Trueの場合、実際には投稿せずログ出力のみ

    Returns:
        投稿成功時はTrue
    """
    # ランダムにカテゴリを選択
    category = random.choice(['spell', 'potion', 'creature'])

    if category == 'spell':
        print("カテゴリ: 呪文")
        return post_spell(dry_run=dry_run)
    elif category == 'potion':
        print("カテゴリ: ポーション")
        return post_potion(dry_run=dry_run)
    else:
        print("カテゴリ: 魔法生物")
        return post_creature(dry_run=dry_run)


def main():
    """メイン関数"""
    import argparse

    parser = argparse.ArgumentParser(
        description='Potterpedia Bot - X (Twitter) 投稿スクリプト'
    )

    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='実際には投稿せず、投稿内容をログ出力のみ'
    )

    subparsers = parser.add_subparsers(dest='command', help='実行するコマンド')

    # todayコマンド
    today_parser = subparsers.add_parser(
        'today',
        help='今日の誕生日・命日・イベントツイートを投稿'
    )
    today_parser.add_argument(
        '--categories',
        nargs='+',
        choices=['birthday', 'deathday', 'event'],
        help='投稿するカテゴリーを指定（複数可）。指定しない場合はすべて投稿'
    )

    # birthdayコマンド
    birthday_parser = subparsers.add_parser(
        'birthday',
        help='指定した日付の誕生日ツイートを投稿'
    )
    birthday_parser.add_argument(
        'date',
        help='日付（YYYY-MM-DD形式）'
    )

    # deathdayコマンド
    deathday_parser = subparsers.add_parser(
        'deathday',
        help='指定した日付の命日ツイートを投稿'
    )
    deathday_parser.add_argument(
        'date',
        help='日付（YYYY-MM-DD形式）'
    )

    # eventコマンド
    event_parser = subparsers.add_parser(
        'event',
        help='指定した日付のイベントツイートを投稿'
    )
    event_parser.add_argument(
        'date',
        help='日付（YYYY-MM-DD形式）'
    )

    # spellコマンド
    spell_parser = subparsers.add_parser(
        'spell',
        help='呪文ツイートを投稿（ランダムまたはID指定）'
    )
    spell_parser.add_argument(
        '--id',
        dest='spell_id',
        help='特定の呪文ID（UUID）を指定'
    )

    # potionコマンド
    potion_parser = subparsers.add_parser(
        'potion',
        help='ポーションツイートを投稿（ランダムまたはID指定）'
    )
    potion_parser.add_argument(
        '--id',
        dest='potion_id',
        help='特定のポーションID（UUID）を指定'
    )

    # creatureコマンド
    creature_parser = subparsers.add_parser(
        'creature',
        help='魔法生物ツイートを投稿（ランダムまたはID指定）'
    )
    creature_parser.add_argument(
        '--id',
        dest='creature_id',
        help='特定の魔法生物ID（UUID）を指定'
    )

    # glossaryコマンド
    subparsers.add_parser(
        'glossary',
        help='用語集（呪文・ポーション・魔法生物）をランダムに投稿'
    )

    # testコマンド
    test_parser = subparsers.add_parser(
        'test',
        help='テスト用テキストをツイート'
    )
    test_parser.add_argument(
        'text',
        help='投稿するテキスト'
    )

    args = parser.parse_args()

    # コマンドが指定されていない場合はヘルプを表示
    if not args.command:
        parser.print_help()
        return

    try:
        if args.command == 'today':
            post_today(dry_run=args.dry_run, categories=args.categories)

        elif args.command == 'birthday':
            post_birthday(args.date, dry_run=args.dry_run)

        elif args.command == 'deathday':
            post_deathday(args.date, dry_run=args.dry_run)

        elif args.command == 'event':
            post_event(args.date, dry_run=args.dry_run)

        elif args.command == 'spell':
            post_spell(spell_id=args.spell_id, dry_run=args.dry_run)

        elif args.command == 'potion':
            post_potion(potion_id=args.potion_id, dry_run=args.dry_run)

        elif args.command == 'creature':
            post_creature(creature_id=args.creature_id, dry_run=args.dry_run)

        elif args.command == 'glossary':
            post_glossary(dry_run=args.dry_run)

        elif args.command == 'test':
            poster = XPoster(dry_run=args.dry_run)
            poster.post_tweet(args.text)

    except Exception as e:
        print(f"✗ エラーが発生しました: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == '__main__':
    main()
