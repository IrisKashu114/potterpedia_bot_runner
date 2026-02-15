#!/usr/bin/env python3
"""
X (Twitter) 投稿スクリプト

このスクリプトは誕生日・命日・イベント・用語集のツイートを投稿します。

使用例:
    # 今日の誕生日・命日・イベントを投稿（Dry-run）
    python scripts/posting/post_tweet.py --dry-run today

    # 特定の日付のイベントを投稿
    python scripts/posting/post_tweet.py event 1998-05-02

    # ランダムに呪文を投稿
    python scripts/posting/post_tweet.py spell

    # ランダムにポーションを投稿
    python scripts/posting/post_tweet.py potion

    # ランダムに魔法生物を投稿
    python scripts/posting/post_tweet.py creature

    # ランダムに用語集（呪文・ポーション・魔法生物）を投稿
    python scripts/posting/post_tweet.py glossary

    # テスト投稿
    python scripts/posting/post_tweet.py test "テストツイート"
"""

import random
import sys
from datetime import datetime
from pathlib import Path
from typing import Optional

# Import centralized config - must be before scripts imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from scripts.utils.data_loader import load_data_file
from scripts.posting.twitter_client import XPoster
from config import (
    CALENDAR_DIR,
    GLOSSARY_DIR,
    GLOSSARY_CATEGORIES,
    TWEET_MAX_LENGTH,
    get_category_display_name,
)

# 状態管理モジュールをインポート
try:
    from scripts.sync.state_manager import StateManager
    STATE_MANAGEMENT_AVAILABLE = True
except ImportError:
    STATE_MANAGEMENT_AVAILABLE = False
    print("Warning: state_manager.py が見つかりません。状態管理機能は無効です。")

# ============================================================
# 定数定義
# ============================================================

# データファイルパス (using CALENDAR_DIR and GLOSSARY_DIR from config)
# Calendar files (date-based tweets)
BIRTHDAYS_FILE = CALENDAR_DIR / 'birthdays.json'
DEATHDAYS_FILE = CALENDAR_DIR / 'deathdays.json'
EVENTS_FILE = CALENDAR_DIR / 'events.json'

# Glossary files (random glossary tweets)
SPELLS_FILE = GLOSSARY_DIR / 'spells.json'
POTIONS_FILE = GLOSSARY_DIR / 'potions.json'
CREATURES_FILE = GLOSSARY_DIR / 'creatures.json'
OBJECTS_FILE = GLOSSARY_DIR / 'objects.json'
LOCATIONS_FILE = GLOSSARY_DIR / 'locations.json'
ORGANIZATIONS_FILE = GLOSSARY_DIR / 'organizations.json'
CONCEPTS_FILE = GLOSSARY_DIR / 'concepts.json'
CHARACTERS_FILE = GLOSSARY_DIR / 'characters.json'

# 用語集カテゴリリスト (now using config)
# GLOSSARY_CATEGORIES is already imported from config

# カテゴリー情報のマッピング
# Build from config to maintain compatibility
_CATEGORY_FILE_MAPPING = {
    'spell': SPELLS_FILE,
    'potion': POTIONS_FILE,
    'creature': CREATURES_FILE,
    'object': OBJECTS_FILE,
    'location': LOCATIONS_FILE,
    'organization': ORGANIZATIONS_FILE,
    'concept': CONCEPTS_FILE,
    'character': CHARACTERS_FILE,
}

CATEGORY_CONFIG_LOCAL = {
    category: {
        'file': _CATEGORY_FILE_MAPPING[category],
        'display_name': get_category_display_name(category),
    }
    for category in GLOSSARY_CATEGORIES
}

# ツイート最大文字数（全角半角関係なく140字）
# TWEET_MAX_LENGTH is already imported from config


def post_birthday(date_str: str, dry_run: bool = False) -> bool:
    """
    指定した日付の誕生日ツイートを投稿

    Args:
        date_str: 日付文字列（YYYY-MM-DD形式）
        dry_run: Trueの場合、実際には投稿せずログ出力のみ

    Returns:
        投稿成功時はTrue
    """
    # データファイル読み込み
    data = load_data_file(BIRTHDAYS_FILE)

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
    # データファイル読み込み
    data = load_data_file(DEATHDAYS_FILE)

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
    # データファイル読み込み
    data = load_data_file(EVENTS_FILE)

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


def post_glossary_item(
    category: str,
    item_id: Optional[str] = None,
    dry_run: bool = False,
    use_state: bool = True
) -> bool:
    """
    用語集アイテムを投稿（汎用関数）

    Args:
        category: カテゴリー（'spell', 'potion', 'creature', 'object', 'location', 'organization', 'concept', 'character'）
        item_id: 特定のアイテムID（UUIDまたはslug）。Noneの場合はランダム選択
        dry_run: Trueの場合、実際には投稿せずログ出力のみ
        use_state: 状態管理を使用するかどうか（重複投稿防止）

    Returns:
        投稿成功時はTrue
    """
    # カテゴリー設定を取得
    if category not in CATEGORY_CONFIG_LOCAL:
        print(f"無効なカテゴリーです: {category}")
        return False

    config = CATEGORY_CONFIG_LOCAL[category]
    data_file = config['file']
    display_name = config['display_name']

    # データファイル読み込み
    data = load_data_file(data_file)

    # アイテムを選択
    if item_id:
        # ID指定の場合、該当するアイテムを検索
        matches = [
            entry for entry in data['data']
            if entry.get('id') == item_id or entry.get('slug') == item_id
        ]
        if not matches:
            print(f"指定されたID（{item_id}）の{display_name}が見つかりません")
            return False
        entry = matches[0]
    else:
        # ランダム選択（状態管理を使用する場合は未投稿のものから選択）
        if use_state and STATE_MANAGEMENT_AVAILABLE:
            state_manager = StateManager()
            entry = state_manager.get_random_available_item(category, data['data'])
            if not entry:
                print(f"利用可能な{display_name}がありません")
                return False
        else:
            entry = random.choice(data['data'])

    # ツイート投稿
    poster = XPoster(dry_run=dry_run)
    result = poster.post_tweet(entry['tweet_text_ja'])

    if result:
        print(f"✓ {display_name}: {entry.get('name_ja') or entry.get('name_en')}")

        # 投稿成功時、状態を更新
        if use_state and STATE_MANAGEMENT_AVAILABLE and not dry_run:
            state_manager = StateManager()
            state_manager.mark_as_posted(category, entry['id'])

        return True
    return False


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
    return post_glossary_item('spell', spell_id, dry_run, use_state)


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
    return post_glossary_item('potion', potion_id, dry_run, use_state)


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
    return post_glossary_item('creature', creature_id, dry_run, use_state)


def post_object(object_id: Optional[str] = None, dry_run: bool = False, use_state: bool = True) -> bool:
    """
    魔法道具ツイートを投稿

    Args:
        object_id: 特定の魔法道具ID（UUIDまたはslug）。Noneの場合はランダム選択
        dry_run: Trueの場合、実際には投稿せずログ出力のみ
        use_state: 状態管理を使用するかどうか（重複投稿防止）

    Returns:
        投稿成功時はTrue
    """
    return post_glossary_item('object', object_id, dry_run, use_state)


def post_location(location_id: Optional[str] = None, dry_run: bool = False, use_state: bool = True) -> bool:
    """
    場所ツイートを投稿

    Args:
        location_id: 特定の場所ID（UUIDまたはslug）。Noneの場合はランダム選択
        dry_run: Trueの場合、実際には投稿せずログ出力のみ
        use_state: 状態管理を使用するかどうか（重複投稿防止）

    Returns:
        投稿成功時はTrue
    """
    return post_glossary_item('location', location_id, dry_run, use_state)


def post_organization(organization_id: Optional[str] = None, dry_run: bool = False, use_state: bool = True) -> bool:
    """
    組織ツイートを投稿

    Args:
        organization_id: 特定の組織ID（UUIDまたはslug）。Noneの場合はランダム選択
        dry_run: Trueの場合、実際には投稿せずログ出力のみ
        use_state: 状態管理を使用するかどうか（重複投稿防止）

    Returns:
        投稿成功時はTrue
    """
    return post_glossary_item('organization', organization_id, dry_run, use_state)


def post_concept(concept_id: Optional[str] = None, dry_run: bool = False, use_state: bool = True) -> bool:
    """
    魔法概念ツイートを投稿

    Args:
        concept_id: 特定の魔法概念ID（UUIDまたはslug）。Noneの場合はランダム選択
        dry_run: Trueの場合、実際には投稿せずログ出力のみ
        use_state: 状態管理を使用するかどうか（重複投稿防止）

    Returns:
        投稿成功時はTrue
    """
    return post_glossary_item('concept', concept_id, dry_run, use_state)


def post_character(character_id: Optional[str] = None, dry_run: bool = False, use_state: bool = True) -> bool:
    """
    キャラクタープロフィールツイートを投稿

    Args:
        character_id: 特定のキャラクターID（UUIDまたはslug）。Noneの場合はランダム選択
        dry_run: Trueの場合、実際には投稿せずログ出力のみ
        use_state: 状態管理を使用するかどうか（重複投稿防止）

    Returns:
        投稿成功時はTrue
    """
    return post_glossary_item('character', character_id, dry_run, use_state)


def post_glossary(dry_run: bool = False) -> bool:
    """
    用語集（呪文・ポーション・魔法生物・魔法道具・場所・組織・魔法概念・キャラクター）をランダムに投稿

    Args:
        dry_run: Trueの場合、実際には投稿せずログ出力のみ

    Returns:
        投稿成功時はTrue
    """
    # エントリ数に基づく重み付きランダムでカテゴリを選択
    weights = []
    for cat in GLOSSARY_CATEGORIES:
        config = CATEGORY_CONFIG_LOCAL[cat]
        try:
            data = load_data_file(config['file'])
            weights.append(len(data.get('data', [])))
        except (FileNotFoundError, Exception):
            weights.append(0)

    # 全カテゴリのエントリ数が0の場合はフォールバック
    if sum(weights) == 0:
        print("警告: すべてのカテゴリのエントリ数が0です。均等選択にフォールバックします。")
        category = random.choice(GLOSSARY_CATEGORIES)
    else:
        category = random.choices(GLOSSARY_CATEGORIES, weights=weights, k=1)[0]
        total = sum(weights)
        cat_weight = weights[GLOSSARY_CATEGORIES.index(category)]
        print(f"重み付き選択: {category} ({cat_weight}/{total}件, {cat_weight/total*100:.1f}%)")

    if category == 'spell':
        print("カテゴリ: 呪文")
        return post_spell(dry_run=dry_run)
    elif category == 'potion':
        print("カテゴリ: ポーション")
        return post_potion(dry_run=dry_run)
    elif category == 'creature':
        print("カテゴリ: 魔法生物")
        return post_creature(dry_run=dry_run)
    elif category == 'object':
        print("カテゴリ: 魔法道具")
        return post_object(dry_run=dry_run)
    elif category == 'location':
        print("カテゴリ: 場所")
        return post_location(dry_run=dry_run)
    elif category == 'organization':
        print("カテゴリ: 組織")
        return post_organization(dry_run=dry_run)
    elif category == 'concept':
        print("カテゴリ: 魔法概念")
        return post_concept(dry_run=dry_run)
    else:
        print("カテゴリ: キャラクター")
        return post_character(dry_run=dry_run)


def main() -> None:
    """
    メイン関数 - コマンドライン引数を解析してツイート投稿処理を実行
    """
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

    # objectコマンド
    object_parser = subparsers.add_parser(
        'object',
        help='魔法道具ツイートを投稿（ランダムまたはID指定）'
    )
    object_parser.add_argument(
        '--id',
        dest='object_id',
        help='特定の魔法道具ID（UUID）を指定'
    )

    # locationコマンド
    location_parser = subparsers.add_parser(
        'location',
        help='場所ツイートを投稿（ランダムまたはID指定）'
    )
    location_parser.add_argument(
        '--id',
        dest='location_id',
        help='特定の場所ID（UUID）を指定'
    )

    # organizationコマンド
    organization_parser = subparsers.add_parser(
        'organization',
        help='組織ツイートを投稿（ランダムまたはID指定）'
    )
    organization_parser.add_argument(
        '--id',
        dest='organization_id',
        help='特定の組織ID（UUID）を指定'
    )

    # conceptコマンド
    concept_parser = subparsers.add_parser(
        'concept',
        help='魔法概念ツイートを投稿（ランダムまたはID指定）'
    )
    concept_parser.add_argument(
        '--id',
        dest='concept_id',
        help='特定の魔法概念ID（UUID）を指定'
    )

    # characterコマンド
    character_parser = subparsers.add_parser(
        'character',
        help='キャラクタープロフィールツイートを投稿（ランダムまたはID指定）'
    )
    character_parser.add_argument(
        '--id',
        dest='character_id',
        help='特定のキャラクターID（UUID）を指定'
    )

    # glossaryコマンド
    subparsers.add_parser(
        'glossary',
        help='用語集（呪文・ポーション・魔法生物・魔法道具・場所・組織・魔法概念・キャラクター）をランダムに投稿'
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

        elif args.command == 'object':
            post_object(object_id=args.object_id, dry_run=args.dry_run)

        elif args.command == 'location':
            post_location(location_id=args.location_id, dry_run=args.dry_run)

        elif args.command == 'organization':
            post_organization(organization_id=args.organization_id, dry_run=args.dry_run)

        elif args.command == 'concept':
            post_concept(concept_id=args.concept_id, dry_run=args.dry_run)

        elif args.command == 'character':
            post_character(character_id=args.character_id, dry_run=args.dry_run)

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
