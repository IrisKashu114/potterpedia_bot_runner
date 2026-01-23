# Potterpedia Bot Runner

⚠️ **このリポジトリは非公開リポジトリから自動的に同期されています。**

**このリポジトリで直接変更を行わないでください** - 次回の同期で上書きされます。

## 概要

このリポジトリは、Potterpedia Twitter Botの公開実行環境です。ボットは以下の内容を投稿します：

- ハリー・ポッターシリーズのキャラクターの誕生日
- キャラクターの命日（追悼）
- 原作の重要なイベント
- 用語集の投稿（呪文、ポーション、魔法生物、魔法道具、場所、組織、魔法概念、キャラクタープロフィール）

## 内容

このリポジトリには、ボットの実行に必要なファイルのみが含まれています：

### スクリプト

- [scripts/post_tweet.py](scripts/post_tweet.py) - メインのツイート投稿スクリプト
- [scripts/twitter_client.py](scripts/twitter_client.py) - X (Twitter) API クライアント
- [scripts/data_loader.py](scripts/data_loader.py) - データファイル読み込み機能
- [scripts/state_manager.py](scripts/state_manager.py) - 投稿状態管理（重複防止）

### データファイル

- `data/posts/birthdays.json` - キャラクター誕生日データ
- `data/posts/deathdays.json` - キャラクター命日データ
- `data/posts/events.json` - ハリー・ポッターのイベントデータ
- `data/posts/spells.json` - 呪文用語集データ
- `data/posts/potions.json` - ポーション用語集データ
- `data/posts/creatures.json` - 魔法生物用語集データ
- `data/posts/objects.json` - 魔法道具用語集データ
- `data/posts/locations.json` - 場所用語集データ
- `data/posts/organizations.json` - 組織用語集データ
- `data/posts/concepts.json` - 魔法概念用語集データ
- `data/posts/characters.json` - キャラクタープロフィールデータ

### その他

- [requirements.txt](requirements.txt) - Python依存関係

## 動作の仕組み

### 自動投稿スケジュール

ボットはGitHub Actionsを通じて自動的に実行されます：

- **0:00 JST (15:00 UTC)**: その日の誕生日・命日ツイートを投稿
- **12:00 JST (3:00 UTC)**: その日のイベントツイートを投稿
- **21:00 JST (12:00 UTC)**: ランダムな用語集エントリ（呪文、ポーション、魔法生物、魔法道具、場所、組織、魔法概念、キャラクター）を投稿

### データ同期

ファイルは、非公開の開発リポジトリから変更がプッシュされると自動的に同期されます。すべてのデータファイルには、投稿用の日本語訳が含まれています。

## 手動実行（テスト用）

ローカルでボットをテスト実行したい場合：

### 前提条件

- Python 3.11以上
- X (Twitter) API認証情報

### セットアップ

1. **このリポジトリをクローン:**
   ```bash
   git clone https://github.com/IrisKashu114/potterpedia_bot_runner.git
   cd potterpedia_bot_runner
   ```

2. **仮想環境を作成:**
   ```bash
   python -m venv venv
   source venv/bin/activate  # Windowsの場合: venv\Scripts\activate
   ```

3. **依存関係をインストール:**
   ```bash
   pip install -r requirements.txt
   ```

4. **X API認証情報を含む`.env`ファイルを作成:**
   ```bash
   X_API_KEY=your_api_key_here
   X_API_KEY_SECRET=your_api_key_secret_here
   X_ACCESS_TOKEN=your_access_token_here
   X_ACCESS_TOKEN_SECRET=your_access_token_secret_here
   ```

### 実行コマンド

```bash
# 今日のすべてのツイート（誕生日、命日、イベント）を投稿
python scripts/post_tweet.py today

# 特定の日付の誕生日ツイートを投稿
python scripts/post_tweet.py birthday 1980-07-31

# 特定の日付の命日ツイートを投稿
python scripts/post_tweet.py deathday 1998-05-02

# 特定の日付のイベントツイートを投稿
python scripts/post_tweet.py event 1991-09-01

# ランダムな用語集エントリを投稿（すべてのカテゴリから）
python scripts/post_tweet.py glossary

# 呪文をランダムに投稿
python scripts/post_tweet.py spell

# ポーションをランダムに投稿
python scripts/post_tweet.py potion

# 魔法生物をランダムに投稿
python scripts/post_tweet.py creature

# 魔法道具をランダムに投稿
python scripts/post_tweet.py object

# 場所をランダムに投稿
python scripts/post_tweet.py location

# 組織をランダムに投稿
python scripts/post_tweet.py organization

# 魔法概念をランダムに投稿
python scripts/post_tweet.py concept

# キャラクタープロフィールをランダムに投稿
python scripts/post_tweet.py character

# 特定のIDで呪文を投稿
python scripts/post_tweet.py spell --id SPELL_ID

# ドライラン（実際には投稿せずにテスト）
python scripts/post_tweet.py --dry-run today
```

## データ構造

すべてのデータファイルはJSON形式で、日本語訳が含まれています：

### 誕生日 (`data/posts/birthdays.json`)

```json
{
  "id": "uuid",
  "name_en": "Harry Potter",
  "name_ja": "ハリー・ポッター",
  "birthday": "1980-07-31",
  "tweet_text_ja": "今日7月31日は、ハリー・ポッターの誕生日です！..."
}
```

### 命日 (`data/posts/deathdays.json`)

同じ日に亡くなったキャラクターの個別エントリとグループエントリの両方が含まれます。

### イベント (`data/posts/events.json`)

```json
{
  "id": "uuid",
  "event_date": "1991-09-01",
  "event_en": "Harry's first day at Hogwarts",
  "event_ja": "ハリーのホグワーツ初登校",
  "tweet_text_ja": "今日9月1日は..."
}
```

### 用語集 (`spells.json`, `potions.json`, `creatures.json`, など)

ハリー・ポッターシリーズの呪文、ポーション、魔法生物、魔法道具、場所、組織、魔法概念、キャラクターに関する詳細情報（日本語名と効果を含む）が含まれています。

## X API レート制限

- **無料プラン**: 月500投稿、24時間あたり17投稿
- **現在の使用量**: 月あたり約60-90投稿（制限内に余裕あり）
  - 日付ベースの投稿: 月あたり0-30投稿（カレンダーに依存）
  - 用語集投稿: 月あたり30投稿（21:00 JSTに1日1回）

## ライセンス

データはJ.K.ローリング著のハリー・ポッターシリーズから取得されています。このボットはファンプロジェクトであり、J.K.ローリングやワーナーブラザーズとは関係がなく、承認も受けていません。

## お問い合わせ

このボットに関する問題や質問がある場合は、このリポジトリでissueを開いてください。

---

**最終同期**: GitHub Actionsによって自動更新
**ソースリポジトリ**: 非公開（開発およびデータ管理用）
