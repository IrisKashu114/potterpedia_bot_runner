#!/usr/bin/env python3
"""
用語集投稿の状態管理モジュール

このモジュールは、用語集（spells/potions/creatures）の投稿履歴を管理し、
重複投稿を防ぐために使用されます。

状態はGitHub Gistに保存され、すべての用語を投稿したらリセットされます。
"""

import json
import os
import random
import shutil
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional

import requests

# Import centralized config
sys.path.insert(0, str(Path(__file__).parent.parent.parent))
from config import (
    DATA_DIR,
    PRODUCTION_DIR,
    GLOSSARY_SUBDIR,
    STATE_FILE_NAME,
    GIST_FILE_NAME,
    GIST_API_TIMEOUT,
    GIST_API_MAX_RETRIES,
    GIST_API_RETRY_DELAY,
    GIST_API_RETRY_BACKOFF,
    MAX_CYCLE_COUNT,
    TIMESTAMP_PAST_TOLERANCE_YEARS,
    TIMESTAMP_FUTURE_TOLERANCE_MINUTES,
    CATEGORY_CONFIG,
)


# エラークラス定義
class GistAPIError(Exception):
    """Gist API操作に関する基底エラークラス"""
    pass


class GistAuthenticationError(GistAPIError):
    """Gist API認証エラー (401, 403)"""
    pass


class GistNotFoundError(GistAPIError):
    """Gist が見つからない (404)"""
    pass


class GistRateLimitError(GistAPIError):
    """Gist API レート制限エラー (429)"""
    def __init__(self, message: str, retry_after: Optional[int] = None):
        super().__init__(message)
        self.retry_after = retry_after


class GistNetworkError(GistAPIError):
    """ネットワーク接続エラー"""
    pass


class GistTimeoutError(GistAPIError):
    """タイムアウトエラー"""
    pass


class GistServerError(GistAPIError):
    """Gist API サーバーエラー (5xx)"""
    pass


# カテゴリ設定 (now using config)
# CATEGORY_CONFIG is already imported from config
# Note: The config version uses singular form keys like 'spell', 'potion'
# We need to convert to plural form for this script
CATEGORY_CONFIG_PLURAL = {
    config['plural']: {
        'singular': config['singular'],
        'display_name': config['display_name']
    }
    for config in CATEGORY_CONFIG.values()
    if config['type'] == 'glossary'
}

# ファイルパス設定 (now using config)
# DATA_DIR, PRODUCTION_DIR, GLOSSARY_SUBDIR, STATE_FILE_NAME, GIST_FILE_NAME are imported from config

# 検証設定 (now using config)
# MAX_CYCLE_COUNT, TIMESTAMP_PAST_TOLERANCE_YEARS, TIMESTAMP_FUTURE_TOLERANCE_MINUTES imported from config

# API設定 (now using config)
# GIST_API_TIMEOUT, GIST_API_MAX_RETRIES, GIST_API_RETRY_DELAY, GIST_API_RETRY_BACKOFF imported from config


class StateValidator:
    """状態データの検証を行うクラス"""

    def __init__(self, state: Dict, gist_id: Optional[str] = None, github_token: Optional[str] = None):
        """
        初期化

        Args:
            state: 検証対象の状態データ
            gist_id: GitHub Gist ID（同期状態検証に使用）
            github_token: GitHub Personal Access Token（同期状態検証に使用）
        """
        self.state = state
        self.gist_id = gist_id
        self.github_token = github_token

    def validate(
        self,
        verbose: bool = False,
        fix: bool = False,
        category: Optional[str] = None,
        report_file: Optional[str] = None,
        load_gist_state_func: Optional[callable] = None,
        save_state_func: Optional[callable] = None
    ) -> Dict:
        """
        状態データの整合性を検証

        Args:
            verbose: 詳細情報を表示
            fix: 軽微な問題を自動修正（例: 孤立IDの削除）
            category: 特定のカテゴリのみ検証（'spells', 'potions', 'creatures'）
            report_file: 検証レポートの出力先ファイルパス
            load_gist_state_func: Gist状態を読み込む関数（同期状態検証用）
            save_state_func: 状態を保存する関数（自動修正用）

        Returns:
            検証結果の辞書:
            {
                "valid": bool,
                "timestamp": str,
                "checks": {
                    "id_existence": {"passed": bool, "issues": [...]},
                    "cycle_counts": {"passed": bool, "issues": [...]},
                    "timestamps": {"passed": bool, "issues": [...]},
                    "structure": {"passed": bool, "issues": [...]},
                    "consistency": {"passed": bool, "issues": [...]},
                    "sync_status": {"passed": bool, "issues": [...]}
                },
                "summary": {
                    "total_checks": int,
                    "passed": int,
                    "failed": int,
                    "warnings": int
                }
            }
        """
        print("=== 状態検証 ===\n")

        # 検証するカテゴリを決定
        categories_to_check = [category] if category else list(CATEGORY_CONFIG_PLURAL.keys())

        # 検証実行
        validation_result = {
            "valid": True,
            "timestamp": datetime.now(timezone.utc).isoformat().replace('+00:00', 'Z'),
            "checks": {},
            "summary": {
                "total_checks": 0,
                "passed": 0,
                "failed": 0,
                "warnings": 0
            }
        }

        # データ構造検証
        structure_result = self.validate_structure(verbose=verbose)
        validation_result["checks"]["structure"] = structure_result
        validation_result["summary"]["total_checks"] += 1
        if structure_result["passed"]:
            validation_result["summary"]["passed"] += 1
        else:
            validation_result["summary"]["failed"] += 1
            validation_result["valid"] = False

        # ID存在チェック
        id_result = self.validate_ids(categories_to_check, verbose=verbose, fix=fix, save_state_func=save_state_func)
        validation_result["checks"]["id_existence"] = id_result
        validation_result["summary"]["total_checks"] += 1
        if id_result["passed"]:
            validation_result["summary"]["passed"] += 1
        else:
            validation_result["summary"]["failed"] += 1
            validation_result["valid"] = False

        # サイクルカウント検証
        cycle_result = self.validate_cycle_counts(categories_to_check, verbose=verbose)
        validation_result["checks"]["cycle_counts"] = cycle_result
        validation_result["summary"]["total_checks"] += 1
        if cycle_result["passed"]:
            validation_result["summary"]["passed"] += 1
        else:
            validation_result["summary"]["failed"] += 1
            validation_result["valid"] = False

        # タイムスタンプ検証
        timestamp_result = self.validate_timestamps(verbose=verbose)
        validation_result["checks"]["timestamps"] = timestamp_result
        validation_result["summary"]["total_checks"] += 1
        if timestamp_result["passed"]:
            validation_result["summary"]["passed"] += 1
        elif timestamp_result.get("warning"):
            validation_result["summary"]["warnings"] += 1
        else:
            validation_result["summary"]["failed"] += 1
            validation_result["valid"] = False

        # 論理的整合性検証
        consistency_result = self.validate_consistency(categories_to_check, verbose=verbose)
        validation_result["checks"]["consistency"] = consistency_result
        validation_result["summary"]["total_checks"] += 1
        if consistency_result["passed"]:
            validation_result["summary"]["passed"] += 1
        else:
            validation_result["summary"]["failed"] += 1
            validation_result["valid"] = False

        # Gist-ローカル同期状態検証
        sync_result = self.validate_sync_status(verbose=verbose, load_gist_state_func=load_gist_state_func)
        validation_result["checks"]["sync_status"] = sync_result
        validation_result["summary"]["total_checks"] += 1
        if sync_result["passed"]:
            validation_result["summary"]["passed"] += 1
        elif sync_result.get("warning"):
            validation_result["summary"]["warnings"] += 1

        # 結果出力
        self._print_validation_result(validation_result, verbose=verbose)

        # レポート生成
        if report_file:
            self._generate_validation_report(validation_result, report_file)

        return validation_result

    def validate_structure(self, verbose: bool = False) -> Dict:
        """
        データ構造の検証

        Args:
            verbose: 詳細情報を表示

        Returns:
            検証結果
        """
        issues = []

        # 必須フィールドの存在チェック
        required_fields = {
            'posted_spells': list,
            'posted_potions': list,
            'posted_creatures': list,
            'last_spell_posted': (dict, type(None)),
            'last_potion_posted': (dict, type(None)),
            'last_creature_posted': (dict, type(None)),
            'last_updated': str,
            'cycle_count': dict
        }

        # 旧バージョンのstateではcreaturesがない可能性があるため警告のみ
        optional_fields = {'posted_creatures', 'last_creature_posted'}

        for field, expected_type in required_fields.items():
            if field not in self.state:
                if field in optional_fields or (field == 'cycle_count' and 'creatures' not in self.state.get('cycle_count', {})):
                    # 警告のみ（古いstateファイル）
                    if verbose:
                        print(f"  ⚠️  フィールド '{field}' が存在しません（古いバージョン）")
                else:
                    issues.append(f"必須フィールド '{field}' が存在しません")
            elif not isinstance(self.state[field], expected_type):
                issues.append(f"フィールド '{field}' の型が不正です（期待: {expected_type}, 実際: {type(self.state[field])}）")

        # cycle_count の内容チェック
        if 'cycle_count' in self.state and isinstance(self.state['cycle_count'], dict):
            for category in CATEGORY_CONFIG_PLURAL.keys():
                if category not in self.state['cycle_count']:
                    if category in ['creatures', 'objects', 'locations', 'organizations', 'concepts'] and verbose:
                        # 新しいカテゴリは古いバージョンにはない可能性がある
                        print(f"  ⚠️  cycle_count に '{category}' が存在しません（古いバージョン）")
                    elif category not in ['creatures', 'objects', 'locations', 'organizations', 'concepts']:
                        issues.append(f"cycle_count に '{category}' が存在しません")
                elif not isinstance(self.state['cycle_count'][category], (int, float)):
                    issues.append(f"cycle_count['{category}'] の型が不正です")

        # last_*_posted の内容チェック
        for config in CATEGORY_CONFIG_PLURAL.values():
            category = config['singular']
            last_key = f"last_{category}_posted"
            if last_key in self.state and self.state[last_key] is not None:
                last_posted = self.state[last_key]
                if not isinstance(last_posted, dict):
                    issues.append(f"'{last_key}' の型が不正です")
                elif 'id' not in last_posted or 'timestamp' not in last_posted:
                    issues.append(f"'{last_key}' に 'id' または 'timestamp' が存在しません")

        passed = len(issues) == 0

        if verbose or not passed:
            print(f"{'✓' if passed else '✗'} データ構造: {'合格' if passed else '不合格'}")
            for issue in issues:
                print(f"  - {issue}")

        return {
            "passed": passed,
            "issues": issues
        }

    def validate_ids(
        self,
        categories: List[str],
        verbose: bool = False,
        fix: bool = False,
        save_state_func: Optional[callable] = None
    ) -> Dict:
        """
        posted_* 配列内のIDが実際のデータファイルに存在するか検証

        Args:
            categories: 検証するカテゴリのリスト
            verbose: 詳細情報を表示
            fix: 孤立IDを自動削除
            save_state_func: 状態を保存する関数（自動修正用）

        Returns:
            検証結果
        """
        issues = []
        fixed_count = 0

        print(f"{'✓' if True else '✗'} ID存在チェック:")

        for category in categories:
            # 古いstateではcreaturesフィールドがない可能性がある
            posted_key = f"posted_{category}"
            if posted_key not in self.state:
                if verbose:
                    print(f"  ⚠️  {category}: state に '{posted_key}' が存在しません（スキップ）")
                continue

            # データファイル読み込み
            data_file = PRODUCTION_DIR / GLOSSARY_SUBDIR / f'{category}.json'

            if not data_file.exists():
                issues.append(f"{category}: データファイルが見つかりません: {data_file}")
                print(f"  ✗ {category}: データファイルが見つかりません")
                continue

            with open(data_file, 'r', encoding='utf-8') as f:
                file_content = json.load(f)

            # ファイル構造の判定（配列 or metadata+data構造）
            if isinstance(file_content, list):
                data_items = file_content
            elif isinstance(file_content, dict) and 'data' in file_content:
                data_items = file_content['data']
            else:
                issues.append(f"{category}: データファイルの構造が不正です")
                print(f"  ✗ {category}: データファイルの構造が不正です")
                continue

            valid_ids = {item['id'] for item in data_items}
            posted_ids = set(self.state.get(posted_key, []))

            # 孤立ID（データファイルに存在しないID）を検出
            orphaned_ids = posted_ids - valid_ids

            if orphaned_ids:
                issues.append(f"{category}: 孤立ID {len(orphaned_ids)} 件検出")
                print(f"  ⚠️  {category}: 孤立ID {len(orphaned_ids)} 件検出")
                if verbose:
                    for orphaned_id in list(orphaned_ids)[:5]:
                        print(f"      - {orphaned_id}")
                    if len(orphaned_ids) > 5:
                        print(f"      ... (他 {len(orphaned_ids) - 5} 件)")

                # 自動修正
                if fix:
                    self.state[posted_key] = [pid for pid in self.state[posted_key] if pid not in orphaned_ids]
                    fixed_count += len(orphaned_ids)
                    print(f"      → {len(orphaned_ids)} 件の孤立IDを削除しました")
            else:
                print(f"  ✓ {category}: {len(posted_ids)}/{len(valid_ids)} (全て有効)")

        if fix and fixed_count > 0 and save_state_func:
            save_state_func()
            print(f"\n✓ {fixed_count} 件の孤立IDを削除し、状態を保存しました")

        passed = len(issues) == 0

        return {
            "passed": passed,
            "issues": issues,
            "fixed": fixed_count if fix else 0
        }

    def validate_cycle_counts(self, categories: List[str], verbose: bool = False) -> Dict:
        """
        サイクルカウントの妥当性を検証

        Args:
            categories: 検証するカテゴリのリスト
            verbose: 詳細情報を表示

        Returns:
            検証結果
        """
        issues = []

        print(f"\n{'✓' if True else '✗'} サイクルカウント:")

        for category in categories:
            cycle_count = self.state.get('cycle_count', {}).get(category)

            # 古いstateではcreaturesがない可能性がある
            if cycle_count is None:
                if verbose:
                    print(f"  ⚠️  {category}: cycle_count が存在しません（スキップ）")
                continue

            cycle_count = cycle_count or 0

            # 非負数チェック
            if cycle_count < 0:
                issues.append(f"{category}: サイクルカウントが負数です: {cycle_count}")
                print(f"  ✗ {category}: {cycle_count} (負数)")
                continue

            # 上限チェック
            if cycle_count > MAX_CYCLE_COUNT:
                issues.append(f"{category}: サイクルカウントが上限を超えています: {cycle_count} > {MAX_CYCLE_COUNT}")
                print(f"  ✗ {category}: {cycle_count} (上限超過)")
                continue

            print(f"  ✓ {category}: {cycle_count} (範囲内)")

        passed = len(issues) == 0

        return {
            "passed": passed,
            "issues": issues
        }

    def validate_timestamps(self, verbose: bool = False) -> Dict:
        """
        タイムスタンプの妥当性を検証

        Args:
            verbose: 詳細情報を表示

        Returns:
            検証結果
        """
        issues = []
        warnings = []

        print(f"\n{'✓' if True else '✗'} タイムスタンプ:")

        # 現在時刻
        now = datetime.now(timezone.utc)
        one_year_ago = now.replace(year=now.year - TIMESTAMP_PAST_TOLERANCE_YEARS)
        future_tolerance = now.replace(minute=now.minute + TIMESTAMP_FUTURE_TOLERANCE_MINUTES)

        # last_updated 検証
        last_updated_str = self.state.get('last_updated')
        if not last_updated_str:
            issues.append("last_updated が存在しません")
            print(f"  ✗ last_updated: 存在しません")
        else:
            try:
                last_updated = datetime.fromisoformat(last_updated_str.replace('Z', '+00:00'))

                # 未来日時チェック
                if last_updated > future_tolerance:
                    issues.append(f"last_updated が未来日時です: {last_updated_str}")
                    print(f"  ✗ last_updated: {last_updated_str} (未来日時)")
                # 極端に古いチェック
                elif last_updated < one_year_ago:
                    warnings.append(f"last_updated が1年以上前です: {last_updated_str}")
                    print(f"  ⚠️  last_updated: {last_updated_str} (1年以上前)")
                else:
                    print(f"  ✓ last_updated: {last_updated_str} (有効)")

            except (ValueError, AttributeError):
                issues.append(f"last_updated のフォーマットが不正です: {last_updated_str}")
                print(f"  ✗ last_updated: {last_updated_str} (フォーマット不正)")

        # last_*_posted 検証
        for config in CATEGORY_CONFIG.values():
            category = config['singular']
            last_key = f"last_{category}_posted"
            last_posted = self.state.get(last_key)

            if last_posted is None:
                continue

            timestamp_str = last_posted.get('timestamp')
            if not timestamp_str:
                issues.append(f"{last_key} に timestamp が存在しません")
                print(f"  ✗ {last_key}: timestamp が存在しません")
                continue

            try:
                timestamp = datetime.fromisoformat(timestamp_str.replace('Z', '+00:00'))

                # 未来日時チェック
                if timestamp > future_tolerance:
                    issues.append(f"{last_key}.timestamp が未来日時です: {timestamp_str}")
                    print(f"  ✗ {last_key}: {timestamp_str} (未来日時)")
                # last_updated との整合性チェック
                elif last_updated_str:
                    try:
                        last_updated = datetime.fromisoformat(last_updated_str.replace('Z', '+00:00'))
                        if timestamp > last_updated:
                            issues.append(f"{last_key}.timestamp が last_updated より新しいです")
                            print(f"  ✗ {last_key}: {timestamp_str} (last_updated より新しい)")
                        else:
                            if verbose:
                                print(f"  ✓ {last_key}: {timestamp_str} (有効)")
                    except:
                        pass
                else:
                    if verbose:
                        print(f"  ✓ {last_key}: {timestamp_str} (有効)")

            except (ValueError, AttributeError):
                issues.append(f"{last_key}.timestamp のフォーマットが不正です: {timestamp_str}")
                print(f"  ✗ {last_key}: {timestamp_str} (フォーマット不正)")

        passed = len(issues) == 0
        warning = len(warnings) > 0 and passed

        return {
            "passed": passed,
            "warning": warning,
            "issues": issues,
            "warnings": warnings
        }

    def validate_consistency(self, categories: List[str], verbose: bool = False) -> Dict:
        """
        論理的整合性を検証

        Args:
            categories: 検証するカテゴリのリスト
            verbose: 詳細情報を表示

        Returns:
            検証結果
        """
        issues = []

        print(f"\n{'✓' if True else '✗'} 論理的整合性:")

        for category in categories:
            # データファイル読み込み
            data_file = PRODUCTION_DIR / GLOSSARY_SUBDIR / f'{category}.json'

            if not data_file.exists():
                continue

            with open(data_file, 'r', encoding='utf-8') as f:
                file_content = json.load(f)

            # ファイル構造の判定（配列 or metadata+data構造）
            if isinstance(file_content, list):
                data_items = file_content
            elif isinstance(file_content, dict) and 'data' in file_content:
                data_items = file_content['data']
            else:
                continue

            total_count = len(data_items)
            posted_key = f"posted_{category}"
            posted_ids = set(self.state.get(posted_key, []))
            posted_count = len(posted_ids)

            # posted数が総数を超えていないかチェック
            if posted_count > total_count:
                issues.append(f"{category}: posted数({posted_count})が総数({total_count})を超えています")
                print(f"  ✗ {category}: posted数 {posted_count} > 総数 {total_count}")
                continue

            # last_*_posted.id が posted_* に含まれているかチェック
            last_key = f"last_{category[:-1]}_posted"  # 'spells' -> 'spell'
            last_posted = self.state.get(last_key)

            if last_posted and 'id' in last_posted:
                last_id = last_posted['id']
                if last_id not in posted_ids:
                    issues.append(f"{category}: last_posted.id が posted配列に含まれていません: {last_id}")
                    print(f"  ✗ {category}: last_posted.id が posted配列に含まれていません")
                    continue

            print(f"  ✓ {category}: 整合性OK (posted {posted_count}/{total_count})")

        passed = len(issues) == 0

        return {
            "passed": passed,
            "issues": issues
        }

    def validate_sync_status(
        self,
        verbose: bool = False,
        load_gist_state_func: Optional[callable] = None
    ) -> Dict:
        """
        Gist-ローカル同期状態を検証

        Args:
            verbose: 詳細情報を表示
            load_gist_state_func: Gist状態を読み込む関数

        Returns:
            検証結果
        """
        issues = []
        warnings = []

        print(f"\n{'✓' if True else '✗'} 同期状態:")

        # Gistから読み込み（関数が提供されている場合のみ）
        gist_state = None
        if load_gist_state_func:
            gist_state = load_gist_state_func()

        # ローカルから読み込み
        state_file = DATA_DIR / STATE_FILE_NAME
        local_state = None
        if state_file.exists():
            with open(state_file, 'r', encoding='utf-8') as f:
                local_state = json.load(f)

        # Gistが存在しない場合
        if not gist_state:
            warnings.append("Gistが存在しません")
            print(f"  ⚠️  Gistが存在しません")
            return {
                "passed": True,
                "warning": True,
                "issues": issues,
                "warnings": warnings
            }

        # ローカルが存在しない場合
        if not local_state:
            warnings.append("ローカルファイルが存在しません")
            print(f"  ⚠️  ローカルファイルが存在しません")
            return {
                "passed": True,
                "warning": True,
                "issues": issues,
                "warnings": warnings
            }

        # 状態比較用に一時的なStateManagerインスタンスを作成
        # （循環インポートを避けるため、実行時にインポート）
        temp_manager = StateManager.__new__(StateManager)
        comparison = temp_manager.compare_states(gist_state, local_state)

        if comparison["is_identical"]:
            print(f"  ✓ Gistとローカルは同期されています")
        else:
            warnings.append("Gistとローカルに差異があります")
            print(f"  ⚠️  Gistとローカルに差異があります")

            if verbose:
                # 差異の詳細表示
                if comparison["posted_diff"]:
                    for category, diff in comparison["posted_diff"].items():
                        gist_only = len(diff["only_in_1"])
                        local_only = len(diff["only_in_2"])
                        if gist_only or local_only:
                            print(f"      {category}: Gist専用 {gist_only} 件, ローカル専用 {local_only} 件")

            print(f"      推奨: python scripts/sync/state_manager.py sync --auto")

        passed = len(issues) == 0
        warning = len(warnings) > 0 and passed

        return {
            "passed": passed,
            "warning": warning,
            "issues": issues,
            "warnings": warnings
        }

    def _print_validation_result(self, result: Dict, verbose: bool = False):
        """
        検証結果を出力

        Args:
            result: 検証結果
            verbose: 詳細情報を表示
        """
        summary = result["summary"]

        print(f"\n{'='*40}")
        print(f"検証結果: {summary['passed']}/{summary['total_checks']} 合格", end="")

        if summary['failed'] > 0:
            print(f", {summary['failed']} エラー", end="")
        if summary['warnings'] > 0:
            print(f", {summary['warnings']} 警告", end="")

        print()

        if result["valid"]:
            print("✓ 状態は正常です")
        else:
            print("✗ 状態に問題があります")

        print(f"{'='*40}\n")

    def _generate_validation_report(self, result: Dict, report_file: str):
        """
        検証レポートをMarkdown形式で生成

        Args:
            result: 検証結果
            report_file: レポートファイルパス
        """
        lines = [
            "# 状態検証レポート",
            "",
            f"**検証日時:** {result['timestamp']}",
            "",
            "## 概要",
            "",
            f"- **総チェック数:** {result['summary']['total_checks']}",
            f"- **合格:** {result['summary']['passed']}",
            f"- **エラー:** {result['summary']['failed']}",
            f"- **警告:** {result['summary']['warnings']}",
            f"- **判定:** {'✓ 正常' if result['valid'] else '✗ 異常'}",
            "",
            "## 詳細",
            ""
        ]

        # 各チェックの詳細
        check_names = {
            "structure": "データ構造",
            "id_existence": "ID存在チェック",
            "cycle_counts": "サイクルカウント",
            "timestamps": "タイムスタンプ",
            "consistency": "論理的整合性",
            "sync_status": "同期状態"
        }

        for check_key, check_name in check_names.items():
            check_result = result["checks"].get(check_key, {})
            passed = check_result.get("passed", False)
            warning = check_result.get("warning", False)

            if passed and not warning:
                lines.append(f"### ✓ {check_name}: 合格")
            elif warning:
                lines.append(f"### ⚠️ {check_name}: 警告")
            else:
                lines.append(f"### ✗ {check_name}: 不合格")

            lines.append("")

            # Issues
            issues = check_result.get("issues", [])
            if issues:
                lines.append("**問題:**")
                lines.append("")
                for issue in issues:
                    lines.append(f"- {issue}")
                lines.append("")

            # Warnings
            warnings = check_result.get("warnings", [])
            if warnings:
                lines.append("**警告:**")
                lines.append("")
                for warning in warnings:
                    lines.append(f"- {warning}")
                lines.append("")

        # ファイルに書き込み
        report_path = Path(report_file)
        report_path.parent.mkdir(parents=True, exist_ok=True)

        with open(report_path, 'w', encoding='utf-8') as f:
            f.write('\n'.join(lines))

        print(f"✓ 検証レポートを生成しました: {report_file}")


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

    def _gist_api_call_with_retry(self, method: str, url: str, **kwargs) -> requests.Response:
        """
        リトライロジック付きGist API呼び出し

        Args:
            method: HTTPメソッド ('GET', 'PATCH', 'POST')
            url: API URL
            **kwargs: requests.request に渡す引数

        Returns:
            レスポンスオブジェクト

        Raises:
            GistAuthenticationError: 認証エラー
            GistNotFoundError: Gist が見つからない
            GistRateLimitError: レート制限エラー
            GistServerError: サーバーエラー
            GistNetworkError: ネットワークエラー
            GistTimeoutError: タイムアウトエラー
        """
        retry_delay = GIST_API_RETRY_DELAY

        for attempt in range(GIST_API_MAX_RETRIES):
            try:
                response = requests.request(method, url, **kwargs)

                # ステータスコードによる分岐
                if response.status_code in (200, 201):
                    return response
                elif response.status_code == 401:
                    raise GistAuthenticationError(f"認証エラー: トークンが無効です (ステータス: {response.status_code})")
                elif response.status_code == 403:
                    raise GistAuthenticationError(f"アクセス拒否: 権限が不足しています (ステータス: {response.status_code})")
                elif response.status_code == 404:
                    raise GistNotFoundError(f"Gist が見つかりません (ステータス: {response.status_code})")
                elif response.status_code == 429:
                    # レート制限エラー - Retry-After ヘッダーを確認
                    retry_after = response.headers.get('Retry-After')
                    retry_after_int = int(retry_after) if retry_after else retry_delay
                    if attempt < GIST_API_MAX_RETRIES - 1:
                        print(f"⚠️  レート制限に達しました。{retry_after_int}秒後にリトライします... (試行 {attempt + 1}/{GIST_API_MAX_RETRIES})")
                        time.sleep(retry_after_int)
                        continue
                    else:
                        raise GistRateLimitError(
                            f"レート制限エラー: 再試行回数の上限に達しました",
                            retry_after=retry_after_int
                        )
                elif response.status_code >= 500:
                    # サーバーエラー - リトライ可能
                    if attempt < GIST_API_MAX_RETRIES - 1:
                        print(f"⚠️  サーバーエラー (ステータス: {response.status_code})。{retry_delay}秒後にリトライします... (試行 {attempt + 1}/{GIST_API_MAX_RETRIES})")
                        time.sleep(retry_delay)
                        retry_delay *= GIST_API_RETRY_BACKOFF
                        continue
                    else:
                        raise GistServerError(f"サーバーエラー: リトライ回数の上限に達しました (ステータス: {response.status_code})")
                else:
                    # その他のエラー
                    raise GistAPIError(f"Gist API エラー (ステータス: {response.status_code}): {response.text}")

            except requests.exceptions.Timeout:
                if attempt < GIST_API_MAX_RETRIES - 1:
                    print(f"⚠️  タイムアウトしました。{retry_delay}秒後にリトライします... (試行 {attempt + 1}/{GIST_API_MAX_RETRIES})")
                    time.sleep(retry_delay)
                    retry_delay *= GIST_API_RETRY_BACKOFF
                    continue
                else:
                    raise GistTimeoutError(f"タイムアウト: リトライ回数の上限に達しました")

            except requests.exceptions.ConnectionError as e:
                if attempt < GIST_API_MAX_RETRIES - 1:
                    print(f"⚠️  ネットワークエラーが発生しました。{retry_delay}秒後にリトライします... (試行 {attempt + 1}/{GIST_API_MAX_RETRIES})")
                    time.sleep(retry_delay)
                    retry_delay *= GIST_API_RETRY_BACKOFF
                    continue
                else:
                    raise GistNetworkError(f"ネットワークエラー: リトライ回数の上限に達しました - {str(e)}")

            except requests.exceptions.RequestException as e:
                # その他の requests エラー
                raise GistNetworkError(f"リクエストエラー: {str(e)}")

        # 理論的にはここには到達しないが、念のため
        raise GistAPIError("予期しないエラー: リトライループを抜けました")

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

            response = self._gist_api_call_with_retry('GET', url, headers=headers, timeout=GIST_API_TIMEOUT)

            gist_data = response.json()
            state_content = gist_data['files'][GIST_FILE_NAME]['content']
            state = json.loads(state_content)
            # 古い状態データをマイグレーション
            return self._migrate_state(state)

        except GistNotFoundError:
            print("Gistが見つかりません。新しい状態を作成します。")
            return self._create_initial_state()

        except GistAuthenticationError as e:
            print(f"Warning: Gist認証エラー - {e}")
            print("  → ローカルファイルを使用します。トークンと権限を確認してください。")
            return self._load_local_state()

        except (GistTimeoutError, GistNetworkError) as e:
            print(f"Warning: Gist接続エラー - {e}")
            print("  → ローカルファイルを使用します。")
            return self._load_local_state()

        except GistRateLimitError as e:
            print(f"Warning: Gistレート制限エラー - {e}")
            if e.retry_after:
                print(f"  → {e.retry_after}秒後に再試行してください。")
            print("  → ローカルファイルを使用します。")
            return self._load_local_state()

        except GistServerError as e:
            print(f"Warning: Gistサーバーエラー - {e}")
            print("  → ローカルファイルを使用します。")
            return self._load_local_state()

        except GistAPIError as e:
            print(f"Warning: Gist読み込みエラー - {e}")
            print("  → ローカルファイルを使用します。")
            return self._load_local_state()

        except Exception as e:
            # 予期しないエラー（JSONパースエラーなど）
            print(f"Warning: Gist読み込み中に予期しないエラーが発生しました: {e}")
            print("  → ローカルファイルを使用します。")
            return self._load_local_state()

    def _load_local_state(self) -> Dict:
        """
        ローカルファイルから状態を読み込む（フォールバック）

        Returns:
            状態データ
        """
        state_file = DATA_DIR / STATE_FILE_NAME

        if state_file.exists():
            with open(state_file, 'r', encoding='utf-8') as f:
                state = json.load(f)
                # 古い状態データをマイグレーション
                return self._migrate_state(state)
        else:
            return self._create_initial_state()

    def _migrate_state(self, state: Dict) -> Dict:
        """
        古い状態データを新しい形式にマイグレーション

        Args:
            state: 既存の状態データ

        Returns:
            マイグレーション済み状態データ
        """
        # 新しいカテゴリを追加（存在しない場合のみ）
        for category in CATEGORY_CONFIG_PLURAL.keys():
            posted_key = f"posted_{category}"
            if posted_key not in state:
                state[posted_key] = []

            last_posted_key = f"last_{CATEGORY_CONFIG_PLURAL[category]['singular']}_posted"
            if last_posted_key not in state:
                state[last_posted_key] = None

        # cycle_countが存在しない場合は初期化
        if "cycle_count" not in state:
            state["cycle_count"] = {}

        # 新しいカテゴリのcycle_countを追加
        for category in CATEGORY_CONFIG_PLURAL.keys():
            if category not in state["cycle_count"]:
                state["cycle_count"][category] = 0

        return state

    def _create_initial_state(self) -> Dict:
        """
        初期状態を作成

        Returns:
            初期状態データ
        """
        state = {}

        # posted_* 配列の初期化
        for category in CATEGORY_CONFIG_PLURAL.keys():
            state[f"posted_{category}"] = []

        # last_*_posted の初期化
        for category, config in CATEGORY_CONFIG_PLURAL.items():
            state[f"last_{config['singular']}_posted"] = None

        # メタデータ
        state["last_updated"] = datetime.now(timezone.utc).isoformat().replace('+00:00', 'Z')

        # サイクルカウントの初期化
        state["cycle_count"] = {category: 0 for category in CATEGORY_CONFIG_PLURAL.keys()}

        return state

    def _save_state(self):
        """状態をGitHub Gistまたはローカルファイルに保存"""
        self.state['last_updated'] = datetime.now(timezone.utc).isoformat().replace('+00:00', 'Z')

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
                    GIST_FILE_NAME: {
                        "content": json.dumps(self.state, indent=2, ensure_ascii=False)
                    }
                }
            }

            self._gist_api_call_with_retry('PATCH', url, headers=headers, json=data, timeout=GIST_API_TIMEOUT)
            print("✓ 状態をGistに保存しました")

        except GistAuthenticationError as e:
            print(f"Warning: Gist認証エラー - {e}")
            print("  → ローカルファイルに保存します。トークンと権限を確認してください。")
            self._save_local_state()

        except (GistTimeoutError, GistNetworkError) as e:
            print(f"Warning: Gist接続エラー - {e}")
            print("  → ローカルファイルに保存します。")
            self._save_local_state()

        except GistRateLimitError as e:
            print(f"Warning: Gistレート制限エラー - {e}")
            if e.retry_after:
                print(f"  → {e.retry_after}秒後に再試行してください。")
            print("  → ローカルファイルに保存します。")
            self._save_local_state()

        except GistServerError as e:
            print(f"Warning: Gistサーバーエラー - {e}")
            print("  → ローカルファイルに保存します。")
            self._save_local_state()

        except GistAPIError as e:
            print(f"Warning: Gist保存エラー - {e}")
            print("  → ローカルファイルに保存します。")
            self._save_local_state()

        except Exception as e:
            # 予期しないエラー
            print(f"Warning: Gist保存中に予期しないエラーが発生しました: {e}")
            print("  → ローカルファイルに保存します。")
            self._save_local_state()

    def _save_local_state(self):
        """ローカルファイルに状態を保存（フォールバック）"""
        state_file = DATA_DIR / STATE_FILE_NAME

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

        # 古い状態データのために posted_key が存在しない場合は初期化
        if posted_key not in self.state:
            self.state[posted_key] = []

        if item_id not in self.state[posted_key]:
            self.state[posted_key].append(item_id)

        self.state[last_posted_key] = {
            "id": item_id,
            "timestamp": datetime.now(timezone.utc).isoformat().replace('+00:00', 'Z')
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
        stats = {}

        for category, config in CATEGORY_CONFIG_PLURAL.items():
            stats[category] = {
                "posted": len(self.state.get(f'posted_{category}', [])),
                "cycles": self.state.get('cycle_count', {}).get(category, 0),
                "last_posted": self.state.get(f'last_{config["singular"]}_posted')
            }

        stats["last_updated"] = self.state.get('last_updated')

        return stats

    def _load_gist_state(self) -> Optional[Dict]:
        """
        GitHub Gistから状態を直接読み込む（同期用）

        Returns:
            Gistから読み込んだ状態データ。失敗した場合はNone
        """
        if not self.gist_id or not self.github_token:
            return None

        try:
            url = f"https://api.github.com/gists/{self.gist_id}"
            headers = {
                "Authorization": f"token {self.github_token}",
                "Accept": "application/vnd.github.v3+json"
            }

            response = self._gist_api_call_with_retry('GET', url, headers=headers, timeout=GIST_API_TIMEOUT)

            gist_data = response.json()
            state_content = gist_data['files'][GIST_FILE_NAME]['content']
            return json.loads(state_content)

        except GistNotFoundError:
            print("Error: Gistが見つかりません")
            return None

        except GistAuthenticationError as e:
            print(f"Error: Gist認証エラー - {e}")
            return None

        except (GistTimeoutError, GistNetworkError) as e:
            print(f"Error: Gist接続エラー - {e}")
            return None

        except GistRateLimitError as e:
            print(f"Error: Gistレート制限エラー - {e}")
            if e.retry_after:
                print(f"  → {e.retry_after}秒後に再試行してください。")
            return None

        except GistServerError as e:
            print(f"Error: Gistサーバーエラー - {e}")
            return None

        except GistAPIError as e:
            print(f"Error: Gist読み込みエラー - {e}")
            return None

        except Exception as e:
            # 予期しないエラー（JSONパースエラーなど）
            print(f"Error: Gist読み込み中に予期しないエラーが発生しました: {e}")
            return None

    def _get_local_state_path(self) -> Path:
        """
        ローカル状態ファイルのパスを取得

        Returns:
            ローカル状態ファイルのPath
        """
        return DATA_DIR / STATE_FILE_NAME

    def _backup_local_state(self) -> bool:
        """
        ローカル状態ファイルをバックアップ

        Returns:
            バックアップが成功した場合はTrue
        """
        state_file = self._get_local_state_path()

        if not state_file.exists():
            return True  # ファイルが存在しない場合はバックアップ不要

        backup_file = state_file.parent / f'{STATE_FILE_NAME.replace(".json", ".backup.json")}'

        try:
            shutil.copy2(state_file, backup_file)
            print(f"✓ バックアップを作成しました: {backup_file}")
            return True
        except Exception as e:
            print(f"Warning: バックアップ作成に失敗しました: {e}")
            return False

    def compare_states(self, state1: Dict, state2: Dict) -> Dict:
        """
        2つの状態を比較して差異を検出

        Args:
            state1: 比較する状態1（例: Gist）
            state2: 比較する状態2（例: ローカル）

        Returns:
            比較結果を含む辞書:
            {
                "has_conflict": bool,
                "timestamp_diff": str,
                "posted_diff": {category: {"only_in_1": [...], "only_in_2": [...]}},
                "cycle_diff": {category: {"state1": int, "state2": int}},
                "is_identical": bool
            }
        """
        result = {
            "has_conflict": False,
            "timestamp_diff": None,
            "posted_diff": {},
            "cycle_diff": {},
            "is_identical": True
        }

        # タイムスタンプ比較
        ts1 = state1.get('last_updated')
        ts2 = state2.get('last_updated')

        if ts1 and ts2:
            if ts1 != ts2:
                result["timestamp_diff"] = f"State1: {ts1}, State2: {ts2}"
                result["is_identical"] = False

        # 各カテゴリーの投稿済みID比較
        for category in CATEGORY_CONFIG_PLURAL.keys():
            posted_key = f"posted_{category}"
            set1 = set(state1.get(posted_key, []))
            set2 = set(state2.get(posted_key, []))

            only_in_1 = list(set1 - set2)
            only_in_2 = list(set2 - set1)

            if only_in_1 or only_in_2:
                result["posted_diff"][category] = {
                    "only_in_1": only_in_1,
                    "only_in_2": only_in_2
                }
                result["is_identical"] = False

                # 両方に異なるIDがある場合は競合
                if only_in_1 and only_in_2:
                    result["has_conflict"] = True

        # サイクルカウント比較
        for category in CATEGORY_CONFIG_PLURAL.keys():
            count1 = state1.get('cycle_count', {}).get(category, 0)
            count2 = state2.get('cycle_count', {}).get(category, 0)

            if count1 != count2:
                result["cycle_diff"][category] = {
                    "state1": count1,
                    "state2": count2
                }
                result["is_identical"] = False

        return result

    def merge_states(self, state1: Dict, state2: Dict, prefer_newer: bool = True) -> Dict:
        """
        2つの状態をマージ

        Args:
            state1: マージする状態1
            state2: マージする状態2
            prefer_newer: Trueの場合、新しいタイムスタンプを優先

        Returns:
            マージされた状態
        """
        merged = self._create_initial_state()

        # タイムスタンプで新しい方を判定
        ts1 = state1.get('last_updated', '')
        ts2 = state2.get('last_updated', '')
        newer_state = state1 if ts1 >= ts2 else state2

        # posted_* 配列はunion（重複なし結合）
        for category in CATEGORY_CONFIG_PLURAL.keys():
            posted_key = f"posted_{category}"
            set1 = set(state1.get(posted_key, []))
            set2 = set(state2.get(posted_key, []))
            merged[posted_key] = list(set1 | set2)

        # last_*_posted は新しいタイムスタンプを優先
        for config in CATEGORY_CONFIG_PLURAL.values():
            category = config['singular']
            last_key = f"last_{category}_posted"
            last1 = state1.get(last_key)
            last2 = state2.get(last_key)

            if last1 and last2:
                ts1 = last1.get('timestamp', '')
                ts2 = last2.get('timestamp', '')
                merged[last_key] = last1 if ts1 >= ts2 else last2
            elif last1:
                merged[last_key] = last1
            elif last2:
                merged[last_key] = last2

        # cycle_count は大きい方を採用
        for category in CATEGORY_CONFIG_PLURAL.keys():
            count1 = state1.get('cycle_count', {}).get(category, 0)
            count2 = state2.get('cycle_count', {}).get(category, 0)
            merged['cycle_count'][category] = max(count1, count2)

        # last_updated は prefer_newer に応じて設定
        if prefer_newer:
            merged['last_updated'] = max(ts1, ts2) if (ts1 and ts2) else (ts1 or ts2)
        else:
            merged['last_updated'] = datetime.now(timezone.utc).isoformat().replace('+00:00', 'Z')

        return merged

    def sync_from_gist(self, force: bool = False, dry_run: bool = False) -> bool:
        """
        Gistからローカルに同期

        Args:
            force: Trueの場合、競合があっても強制的に上書き
            dry_run: Trueの場合、実際の変更は行わずシミュレートのみ

        Returns:
            同期が成功した場合はTrue
        """
        print("=== Gist → ローカル同期 ===\n")

        # Gistから読み込み
        gist_state = self._load_gist_state()
        if not gist_state:
            print("✗ Gistから状態を読み込めませんでした")
            return False

        # ローカルから読み込み
        state_file = self._get_local_state_path()
        if state_file.exists():
            with open(state_file, 'r', encoding='utf-8') as f:
                local_state = json.load(f)
        else:
            print("ℹ ローカルファイルが存在しません。Gistから新規作成します。")
            local_state = self._create_initial_state()

        # 状態比較
        comparison = self.compare_states(gist_state, local_state)

        if comparison["is_identical"]:
            print("✓ Gistとローカルはすでに同期されています")
            return True

        # タイムスタンプ比較
        gist_ts = gist_state.get('last_updated', '')
        local_ts = local_state.get('last_updated', '')

        print(f"Gist タイムスタンプ: {gist_ts}")
        print(f"ローカル タイムスタンプ: {local_ts}\n")

        # 競合チェック
        if comparison["has_conflict"] and not force:
            print("⚠️  競合が検出されました:")
            for category, diff in comparison["posted_diff"].items():
                if diff["only_in_1"] and diff["only_in_2"]:
                    print(f"  {category}: Gistのみ {len(diff['only_in_1'])} 件, ローカルのみ {len(diff['only_in_2'])} 件")
            print("\n--force オプションを使用して強制的に同期するか、")
            print("sync --auto でマージしてください")
            return False

        if gist_ts < local_ts and not force:
            print(f"⚠️  警告: Gistの状態がローカルより古いです")
            print(f"  Gist: {gist_ts}")
            print(f"  ローカル: {local_ts}")
            print("\n--force オプションを使用して強制的に上書きしてください")
            return False

        # Dry-runモード
        if dry_run:
            print("[DRY-RUN] 以下の変更が行われます:\n")
            print(f"  ローカルファイル: {state_file}")
            print(f"  Gistの状態で上書き")
            return True

        # バックアップ作成
        self._backup_local_state()

        # ローカルに保存
        state_file.parent.mkdir(parents=True, exist_ok=True)
        with open(state_file, 'w', encoding='utf-8') as f:
            json.dump(gist_state, f, indent=2, ensure_ascii=False)

        print(f"✓ Gistからローカルに同期しました: {state_file}")
        return True

    def sync_to_gist(self, force: bool = False, dry_run: bool = False) -> bool:
        """
        ローカルからGistに同期

        Args:
            force: Trueの場合、競合があっても強制的に上書き
            dry_run: Trueの場合、実際の変更は行わずシミュレートのみ

        Returns:
            同期が成功した場合はTrue
        """
        print("=== ローカル → Gist同期 ===\n")

        if not self.gist_id or not self.github_token:
            print("✗ Gist設定がありません")
            return False

        # ローカルから読み込み
        state_file = self._get_local_state_path()
        if not state_file.exists():
            print(f"✗ ローカルファイルが存在しません: {state_file}")
            return False

        with open(state_file, 'r', encoding='utf-8') as f:
            local_state = json.load(f)

        # Gistから読み込み
        gist_state = self._load_gist_state()
        if not gist_state:
            print("ℹ Gistが存在しません。ローカルから新規作成します。")
            gist_state = self._create_initial_state()

        # 状態比較
        comparison = self.compare_states(local_state, gist_state)

        if comparison["is_identical"]:
            print("✓ ローカルとGistはすでに同期されています")
            return True

        # タイムスタンプ比較
        local_ts = local_state.get('last_updated', '')
        gist_ts = gist_state.get('last_updated', '')

        print(f"ローカル タイムスタンプ: {local_ts}")
        print(f"Gist タイムスタンプ: {gist_ts}\n")

        # 競合チェック
        if comparison["has_conflict"] and not force:
            print("⚠️  競合が検出されました:")
            for category, diff in comparison["posted_diff"].items():
                if diff["only_in_1"] and diff["only_in_2"]:
                    print(f"  {category}: ローカルのみ {len(diff['only_in_1'])} 件, Gistのみ {len(diff['only_in_2'])} 件")
            print("\n--force オプションを使用して強制的に同期するか、")
            print("sync --auto でマージしてください")
            return False

        if local_ts < gist_ts and not force:
            print(f"⚠️  警告: ローカルの状態がGistより古いです")
            print(f"  ローカル: {local_ts}")
            print(f"  Gist: {gist_ts}")
            print("\n--force オプションを使用して強制的に上書きしてください")
            return False

        # Dry-runモード
        if dry_run:
            print("[DRY-RUN] 以下の変更が行われます:\n")
            print(f"  Gist ID: {self.gist_id}")
            print(f"  ローカルの状態で上書き")
            return True

        # Gistに保存
        try:
            url = f"https://api.github.com/gists/{self.gist_id}"
            headers = {
                "Authorization": f"token {self.github_token}",
                "Accept": "application/vnd.github.v3+json"
            }
            data = {
                "files": {
                    GIST_FILE_NAME: {
                        "content": json.dumps(local_state, indent=2, ensure_ascii=False)
                    }
                }
            }

            self._gist_api_call_with_retry('PATCH', url, headers=headers, json=data, timeout=GIST_API_TIMEOUT)
            print(f"✓ ローカルからGistに同期しました")
            return True

        except GistAuthenticationError as e:
            print(f"✗ Gist認証エラー: {e}")
            return False

        except (GistTimeoutError, GistNetworkError) as e:
            print(f"✗ Gist接続エラー: {e}")
            return False

        except GistRateLimitError as e:
            print(f"✗ Gistレート制限エラー: {e}")
            if e.retry_after:
                print(f"  → {e.retry_after}秒後に再試行してください。")
            return False

        except GistServerError as e:
            print(f"✗ Gistサーバーエラー: {e}")
            return False

        except GistAPIError as e:
            print(f"✗ Gist更新エラー: {e}")
            return False

        except Exception as e:
            # 予期しないエラー
            print(f"✗ Gist更新中に予期しないエラーが発生しました: {e}")
            return False

    def sync_auto(self, dry_run: bool = False) -> bool:
        """
        自動同期（タイムスタンプで最新を選択、または賢くマージ）

        Args:
            dry_run: Trueの場合、実際の変更は行わずシミュレートのみ

        Returns:
            同期が成功した場合はTrue
        """
        print("=== 自動同期（スマートマージ） ===\n")

        # Gistから読み込み
        gist_state = self._load_gist_state()

        # ローカルから読み込み
        state_file = self._get_local_state_path()
        local_state = None
        if state_file.exists():
            with open(state_file, 'r', encoding='utf-8') as f:
                local_state = json.load(f)

        # 片方のみ存在する場合
        if gist_state and not local_state:
            print("ℹ ローカルファイルが存在しません。Gistから同期します。")
            return self.sync_from_gist(dry_run=dry_run)

        if not gist_state and local_state:
            print("ℹ Gistが存在しません。ローカルから同期します。")
            return self.sync_to_gist(dry_run=dry_run)

        if not gist_state and not local_state:
            print("✗ Gistもローカルファイルも存在しません")
            return False

        # 状態比較
        comparison = self.compare_states(gist_state, local_state)

        if comparison["is_identical"]:
            print("✓ Gistとローカルはすでに同期されています")
            return True

        # タイムスタンプ表示
        gist_ts = gist_state.get('last_updated', '')
        local_ts = local_state.get('last_updated', '')

        print(f"Gist タイムスタンプ: {gist_ts}")
        print(f"ローカル タイムスタンプ: {local_ts}\n")

        # スマートマージ
        if comparison["has_conflict"]:
            print("ℹ 競合を検出しました。スマートマージを実行します...\n")

        merged_state = self.merge_states(gist_state, local_state, prefer_newer=True)

        # マージ結果の統計
        print("マージ結果:")
        for category in CATEGORY_CONFIG_PLURAL.keys():
            posted_key = f"posted_{category}"
            gist_count = len(gist_state.get(posted_key, []))
            local_count = len(local_state.get(posted_key, []))
            merged_count = len(merged_state.get(posted_key, []))
            print(f"  {category}: Gist {gist_count} 件 + ローカル {local_count} 件 → マージ {merged_count} 件")

        print(f"\nマージ後のタイムスタンプ: {merged_state.get('last_updated')}")

        # Dry-runモード
        if dry_run:
            print("\n[DRY-RUN] 以下の変更が行われます:")
            print(f"  ローカルファイル: マージ結果で更新")
            print(f"  Gist: マージ結果で更新")
            return True

        # バックアップ作成
        self._backup_local_state()

        # ローカルに保存
        state_file.parent.mkdir(parents=True, exist_ok=True)
        with open(state_file, 'w', encoding='utf-8') as f:
            json.dump(merged_state, f, indent=2, ensure_ascii=False)
        print(f"\n✓ ローカルファイルを更新しました: {state_file}")

        # Gistに保存
        try:
            url = f"https://api.github.com/gists/{self.gist_id}"
            headers = {
                "Authorization": f"token {self.github_token}",
                "Accept": "application/vnd.github.v3+json"
            }
            data = {
                "files": {
                    GIST_FILE_NAME: {
                        "content": json.dumps(merged_state, indent=2, ensure_ascii=False)
                    }
                }
            }

            self._gist_api_call_with_retry('PATCH', url, headers=headers, json=data, timeout=GIST_API_TIMEOUT)
            print(f"✓ Gistを更新しました")
            return True

        except GistAuthenticationError as e:
            print(f"Warning: Gist認証エラー - {e}")
            print(f"  ローカルファイルは更新されました")
            return False

        except (GistTimeoutError, GistNetworkError) as e:
            print(f"Warning: Gist接続エラー - {e}")
            print(f"  ローカルファイルは更新されました")
            return False

        except GistRateLimitError as e:
            print(f"Warning: Gistレート制限エラー - {e}")
            if e.retry_after:
                print(f"  → {e.retry_after}秒後に再試行してください。")
            print(f"  ローカルファイルは更新されました")
            return False

        except GistServerError as e:
            print(f"Warning: Gistサーバーエラー - {e}")
            print(f"  ローカルファイルは更新されました")
            return False

        except GistAPIError as e:
            print(f"Warning: Gist更新エラー - {e}")
            print(f"  ローカルファイルは更新されました")
            return False

        except Exception as e:
            # 予期しないエラー
            print(f"Warning: Gist更新中に予期しないエラーが発生しました: {e}")
            print(f"  ローカルファイルは更新されました")
            return False

    def sync_status(self, verbose: bool = False) -> Dict:
        """
        同期状態を確認

        Args:
            verbose: 詳細情報を表示

        Returns:
            状態比較結果
        """
        print("=== 同期状態確認 ===\n")

        # Gistから読み込み
        gist_state = self._load_gist_state()

        # ローカルから読み込み
        state_file = self._get_local_state_path()
        local_state = None
        if state_file.exists():
            with open(state_file, 'r', encoding='utf-8') as f:
                local_state = json.load(f)

        # 存在チェック
        print(f"Gist: {'✓ 存在' if gist_state else '✗ 存在しない'}")
        print(f"ローカル: {'✓ 存在' if local_state else '✗ 存在しない'}")

        if gist_state:
            print(f"  タイムスタンプ: {gist_state.get('last_updated')}")
        if local_state:
            print(f"  タイムスタンプ: {local_state.get('last_updated')}")

        if not gist_state or not local_state:
            print("\n同期が必要です")
            return {}

        # 状態比較
        comparison = self.compare_states(gist_state, local_state)

        print()
        if comparison["is_identical"]:
            print("✓ Gistとローカルは完全に同期されています")
        else:
            print("⚠️  Gistとローカルに差異があります\n")

            # 投稿済みIDの差異
            if comparison["posted_diff"]:
                print("投稿済みIDの差異:")
                for category, diff in comparison["posted_diff"].items():
                    gist_only = len(diff["only_in_1"])
                    local_only = len(diff["only_in_2"])
                    if gist_only or local_only:
                        print(f"  {category}: Gistのみ {gist_only} 件, ローカルのみ {local_only} 件")
                        if verbose and gist_only:
                            print(f"    Gistのみ: {diff['only_in_1'][:5]}{'...' if gist_only > 5 else ''}")
                        if verbose and local_only:
                            print(f"    ローカルのみ: {diff['only_in_2'][:5]}{'...' if local_only > 5 else ''}")

            # サイクルカウントの差異
            if comparison["cycle_diff"]:
                print("\nサイクルカウントの差異:")
                for category, diff in comparison["cycle_diff"].items():
                    print(f"  {category}: Gist {diff['state1']} 周, ローカル {diff['state2']} 周")

            # 競合の有無
            if comparison["has_conflict"]:
                print("\n⚠️  競合が存在します（両方に異なる変更）")
                print("  推奨: python scripts/sync/state_manager.py sync --auto")
            else:
                print("\n競合なし（マージ可能）")

        return comparison

    def validate(
        self,
        verbose: bool = False,
        fix: bool = False,
        category: Optional[str] = None,
        report_file: Optional[str] = None
    ) -> Dict:
        """
        状態データの整合性を検証

        Args:
            verbose: 詳細情報を表示
            fix: 軽微な問題を自動修正（例: 孤立IDの削除）
            category: 特定のカテゴリのみ検証（'spells', 'potions', 'creatures'）
            report_file: 検証レポートの出力先ファイルパス

        Returns:
            検証結果の辞書:
            {
                "valid": bool,
                "timestamp": str,
                "checks": {
                    "id_existence": {"passed": bool, "issues": [...]},
                    "cycle_counts": {"passed": bool, "issues": [...]},
                    "timestamps": {"passed": bool, "issues": [...]},
                    "structure": {"passed": bool, "issues": [...]},
                    "consistency": {"passed": bool, "issues": [...]},
                    "sync_status": {"passed": bool, "issues": [...]}
                },
                "summary": {
                    "total_checks": int,
                    "passed": int,
                    "failed": int,
                    "warnings": int
                }
            }
        """
        # StateValidatorを使用して検証を実行
        validator = StateValidator(self.state, self.gist_id, self.github_token)
        return validator.validate(
            verbose=verbose,
            fix=fix,
            category=category,
            report_file=report_file,
            load_gist_state_func=self._load_gist_state,
            save_state_func=self._save_state
        )


def create_gist(github_token: str, description: str = "Potterpedia Bot Glossary State") -> str:
    """
    新しいGistを作成（初回セットアップ用）

    Args:
        github_token: GitHub Personal Access Token
        description: Gistの説明

    Returns:
        作成されたGistのID

    Raises:
        GistAuthenticationError: 認証エラー
        GistRateLimitError: レート制限エラー
        GistServerError: サーバーエラー
        GistAPIError: その他のAPIエラー
    """
    url = "https://api.github.com/gists"
    headers = {
        "Authorization": f"token {github_token}",
        "Accept": "application/vnd.github.v3+json"
    }

    # StateManagerの_create_initial_stateを使用
    temp_manager = StateManager.__new__(StateManager)
    initial_state = temp_manager._create_initial_state()

    data = {
        "description": description,
        "public": False,  # プライベートGist
        "files": {
            GIST_FILE_NAME: {
                "content": json.dumps(initial_state, indent=2, ensure_ascii=False)
            }
        }
    }

    # リトライロジック付きAPI呼び出し
    retry_delay = GIST_API_RETRY_DELAY

    for attempt in range(GIST_API_MAX_RETRIES):
        try:
            response = requests.post(url, headers=headers, json=data, timeout=GIST_API_TIMEOUT)

            if response.status_code == 201:
                gist_data = response.json()
                gist_id = gist_data['id']
                print(f"✓ Gistを作成しました: {gist_id}")
                print(f"  URL: {gist_data['html_url']}")
                print(f"\n環境変数に以下を追加してください:")
                print(f"GLOSSARY_STATE_GIST_ID={gist_id}")
                return gist_id
            elif response.status_code == 401:
                raise GistAuthenticationError(f"認証エラー: トークンが無効です")
            elif response.status_code == 403:
                raise GistAuthenticationError(f"アクセス拒否: 権限が不足しています")
            elif response.status_code == 429:
                # レート制限エラー
                retry_after = response.headers.get('Retry-After')
                retry_after_int = int(retry_after) if retry_after else retry_delay
                if attempt < GIST_API_MAX_RETRIES - 1:
                    print(f"⚠️  レート制限に達しました。{retry_after_int}秒後にリトライします... (試行 {attempt + 1}/{GIST_API_MAX_RETRIES})")
                    time.sleep(retry_after_int)
                    continue
                else:
                    raise GistRateLimitError(
                        f"レート制限エラー: 再試行回数の上限に達しました",
                        retry_after=retry_after_int
                    )
            elif response.status_code >= 500:
                # サーバーエラー - リトライ可能
                if attempt < GIST_API_MAX_RETRIES - 1:
                    print(f"⚠️  サーバーエラー (ステータス: {response.status_code})。{retry_delay}秒後にリトライします... (試行 {attempt + 1}/{GIST_API_MAX_RETRIES})")
                    time.sleep(retry_delay)
                    retry_delay *= GIST_API_RETRY_BACKOFF
                    continue
                else:
                    raise GistServerError(f"サーバーエラー: リトライ回数の上限に達しました (ステータス: {response.status_code})")
            else:
                raise GistAPIError(f"Gist作成に失敗しました: {response.status_code} - {response.text}")

        except requests.exceptions.Timeout:
            if attempt < GIST_API_MAX_RETRIES - 1:
                print(f"⚠️  タイムアウトしました。{retry_delay}秒後にリトライします... (試行 {attempt + 1}/{GIST_API_MAX_RETRIES})")
                time.sleep(retry_delay)
                retry_delay *= GIST_API_RETRY_BACKOFF
                continue
            else:
                raise GistTimeoutError(f"タイムアウト: リトライ回数の上限に達しました")

        except requests.exceptions.ConnectionError as e:
            if attempt < GIST_API_MAX_RETRIES - 1:
                print(f"⚠️  ネットワークエラーが発生しました。{retry_delay}秒後にリトライします... (試行 {attempt + 1}/{GIST_API_MAX_RETRIES})")
                time.sleep(retry_delay)
                retry_delay *= GIST_API_RETRY_BACKOFF
                continue
            else:
                raise GistNetworkError(f"ネットワークエラー: リトライ回数の上限に達しました - {str(e)}")

        except requests.exceptions.RequestException as e:
            raise GistNetworkError(f"リクエストエラー: {str(e)}")

    # 理論的にはここには到達しないが、念のため
    raise GistAPIError("予期しないエラー: リトライループを抜けました")


if __name__ == '__main__':
    """
    スタンドアロン実行時の動作
    """
    import argparse
    import sys

    from dotenv import load_dotenv

    load_dotenv()

    parser = argparse.ArgumentParser(
        description='用語集投稿の状態管理',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
使用例:
  # 状態確認
  python scripts/sync/state_manager.py

  # Gist作成
  python scripts/sync/state_manager.py create-gist

  # Gistからローカルに同期
  python scripts/sync/state_manager.py sync --from-gist
  python scripts/sync/state_manager.py sync --from-gist --force

  # ローカルからGistに同期
  python scripts/sync/state_manager.py sync --to-gist
  python scripts/sync/state_manager.py sync --to-gist --force

  # 自動同期（スマートマージ）
  python scripts/sync/state_manager.py sync --auto

  # 同期状態確認
  python scripts/sync/state_manager.py sync --status
  python scripts/sync/state_manager.py sync --status --verbose

  # Dry-run（変更せずシミュレート）
  python scripts/sync/state_manager.py sync --from-gist --dry-run
  python scripts/sync/state_manager.py sync --auto --dry-run

  # 状態検証
  python scripts/sync/state_manager.py validate
  python scripts/sync/state_manager.py validate --verbose
  python scripts/sync/state_manager.py validate --report-file docs/validation_report.md
  python scripts/sync/state_manager.py validate --category spells
  python scripts/sync/state_manager.py validate --fix
        """
    )

    subparsers = parser.add_subparsers(dest='command', help='コマンド')

    # create-gist コマンド
    parser_create = subparsers.add_parser('create-gist', help='新しいGistを作成')

    # sync コマンド
    parser_sync = subparsers.add_parser('sync', help='Gistとローカルを同期')
    sync_group = parser_sync.add_mutually_exclusive_group(required=True)
    sync_group.add_argument('--from-gist', action='store_true', help='Gistからローカルに同期')
    sync_group.add_argument('--to-gist', action='store_true', help='ローカルからGistに同期')
    sync_group.add_argument('--auto', action='store_true', help='自動同期（スマートマージ）')
    sync_group.add_argument('--status', action='store_true', help='同期状態を確認')
    parser_sync.add_argument('--force', action='store_true', help='競合があっても強制的に同期')
    parser_sync.add_argument('--dry-run', action='store_true', help='変更せずシミュレートのみ')
    parser_sync.add_argument('--verbose', action='store_true', help='詳細情報を表示')

    # validate コマンド
    parser_validate = subparsers.add_parser('validate', help='状態データの整合性を検証')
    parser_validate.add_argument('--verbose', action='store_true', help='詳細情報を表示')
    parser_validate.add_argument('--fix', action='store_true', help='軽微な問題を自動修正（孤立IDの削除など）')
    parser_validate.add_argument('--report-file', type=str, help='検証レポートの出力先ファイルパス')
    parser_validate.add_argument('--category', choices=list(CATEGORY_CONFIG_PLURAL.keys()), help='特定のカテゴリのみ検証')

    args = parser.parse_args()

    if args.command == 'create-gist':
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

    elif args.command == 'sync':
        # 同期モード
        manager = StateManager()

        if args.from_gist:
            success = manager.sync_from_gist(force=args.force, dry_run=args.dry_run)
            sys.exit(0 if success else 1)

        elif args.to_gist:
            success = manager.sync_to_gist(force=args.force, dry_run=args.dry_run)
            sys.exit(0 if success else 1)

        elif args.auto:
            success = manager.sync_auto(dry_run=args.dry_run)
            sys.exit(0 if success else 1)

        elif args.status:
            manager.sync_status(verbose=args.verbose)
            sys.exit(0)

    elif args.command == 'validate':
        # 検証モード
        manager = StateManager()
        result = manager.validate(
            verbose=args.verbose,
            fix=args.fix,
            category=args.category,
            report_file=args.report_file
        )
        sys.exit(0 if result["valid"] else 1)

    else:
        # 状態確認モード（デフォルト）
        manager = StateManager()
        stats = manager.get_stats()

        print("=== 用語集投稿状態 ===\n")
        for category, config in CATEGORY_CONFIG_PLURAL.items():
            if category in stats:
                print(f"{config['display_name']}:")
                print(f"  投稿済み: {stats[category]['posted']} 個")
                print(f"  サイクル数: {stats[category]['cycles']} 周")
                if stats[category]['last_posted']:
                    print(f"  最終投稿: {stats[category]['last_posted']['timestamp']}")
                print()

        print(f"最終更新: {stats['last_updated']}")
