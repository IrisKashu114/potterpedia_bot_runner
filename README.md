# Potterpedia Bot Runner

⚠️ **This repository is automatically synchronized from a private repository.**

**DO NOT make changes directly in this repository** - they will be overwritten by the next sync.

## About

This is the public execution environment for the Potterpedia Twitter Bot. The bot posts:
- Character birthdays from the Harry Potter series
- Character deathdays (commemorations)
- Important events from the books
- Glossary posts (spells and potions)

## Contents

This repository contains only the files needed to run the bot:

- [scripts/post_tweet.py](scripts/post_tweet.py) - Main tweet posting script
- `data/posts/birthdays.json` - Character birthday data (14 characters)
- `data/posts/deathdays.json` - Character deathday data (9 grouped posts)
- `data/posts/events.json` - Harry Potter event data (13 major events)
- `data/posts/spells.json` - Spell glossary data (29 spells)
- `data/posts/potions.json` - Potion glossary data (12 potions)
- [requirements.txt](requirements.txt) - Python dependencies

## How It Works

### Automated Posting Schedule

The bot runs automatically via GitHub Actions:
- **0:00 JST (15:00 UTC)**: Posts birthday/deathday/event tweets for the current date
- **21:00 JST (12:00 UTC)**: Posts a random glossary entry (spell or potion)

### Data Sync

Files are automatically synced from the private development repository when changes are pushed. All data files contain Japanese translations ready for posting.

## Manual Execution (For Testing)

If you want to run the bot locally for testing:

### Prerequisites
- Python 3.11+
- X (Twitter) API credentials

### Setup

1. **Clone this repository:**
   ```bash
   git clone https://github.com/YOUR_USERNAME/potterpedia_bot_runner.git
   cd potterpedia_bot_runner
   ```

2. **Create virtual environment:**
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

4. **Create `.env` file with your X API credentials:**
   ```bash
   X_API_KEY=your_api_key_here
   X_API_KEY_SECRET=your_api_key_secret_here
   X_ACCESS_TOKEN=your_access_token_here
   X_ACCESS_TOKEN_SECRET=your_access_token_secret_here
   ```

### Run Commands

```bash
# Post all tweets for today (birthdays, deathdays, events)
python scripts/post_tweet.py today

# Post birthday tweets for a specific date
python scripts/post_tweet.py birthday 1980-07-31

# Post deathday tweets for a specific date
python scripts/post_tweet.py deathday 1998-05-02

# Post event tweets for a specific date
python scripts/post_tweet.py event 1991-09-01

# Post random glossary entry (spell or potion)
python scripts/post_tweet.py glossary

# Post specific spell by ID
python scripts/post_tweet.py spell SPELL_ID

# Post specific potion by ID
python scripts/post_tweet.py potion POTION_ID

# Dry run (test without actually posting)
python scripts/post_tweet.py --dry-run today
```

## Data Structure

All data files are in JSON format with Japanese translations:

### Birthdays (`data/posts/birthdays.json`)
```json
{
  "id": "uuid",
  "name_en": "Harry Potter",
  "name_ja": "ハリー・ポッター",
  "birthday": "1980-07-31",
  "tweet_text_ja": "今日7月31日は、ハリー・ポッターの誕生日です！..."
}
```

### Deathdays (`data/posts/deathdays.json`)
Includes both individual and grouped entries for characters who died on the same date.

### Events (`data/posts/events.json`)
```json
{
  "id": "uuid",
  "event_date": "1991-09-01",
  "event_en": "Harry's first day at Hogwarts",
  "event_ja": "ハリーのホグワーツ初登校",
  "tweet_text_ja": "今日9月1日は..."
}
```

### Glossary (`spells.json`, `potions.json`)
Contains detailed information about spells and potions from the Harry Potter series, including Japanese names and effects.

## X API Rate Limits

- **Free Tier**: 500 posts/month, 17 posts/24 hours
- **Current Usage**: ~30-60 posts/month (well within limits)
  - Date-based posts: 0-30/month (depending on calendar)
  - Glossary posts: 30/month (1 per day at 21:00 JST)

## License

Data is sourced from the Harry Potter series by J.K. Rowling. This bot is a fan project and not affiliated with or endorsed by J.K. Rowling or Warner Bros.

## Contact

For issues or questions about this bot, please open an issue in this repository.

---

**Last Sync**: Automatically updated by GitHub Actions
**Source Repository**: Private (development and data management)
