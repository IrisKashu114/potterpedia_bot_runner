#!/usr/bin/env python3
"""
X (Twitter) APIクライアント

XPosterクラスを提供し、X (Twitter) への投稿を管理します。
"""

import os
import sys
from typing import Optional, Dict, Any

import tweepy
from dotenv import load_dotenv


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
