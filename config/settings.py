"""
Central configuration settings for Potterpedia Bot

This module provides centralized configuration management for all scripts,
eliminating hardcoded values and improving maintainability.
"""

from pathlib import Path

# ============================================================
# Project Structure
# ============================================================

PROJECT_ROOT = Path(__file__).parent.parent
DATA_DIR = PROJECT_ROOT / "data"

# Data subdirectories
DRAFTS_DIR = DATA_DIR / "drafts"
PRODUCTION_DIR = DATA_DIR / "production"
CSV_DIR = DATA_DIR / "csv"
STATE_DIR = DATA_DIR / "state"
BACKUP_DIR = DATA_DIR / "backups"
WIKI_DIR = DATA_DIR / "wiki"
ARCHIVE_DIR = DATA_DIR / "archive"

# Category subdirectories
CALENDAR_SUBDIR = "calendar"
GLOSSARY_SUBDIR = "glossary"

# Production data directories (for posting)
CALENDAR_DIR = PRODUCTION_DIR / CALENDAR_SUBDIR
GLOSSARY_DIR = PRODUCTION_DIR / GLOSSARY_SUBDIR

# Deprecated: POSTS_DIR - Use CALENDAR_DIR or GLOSSARY_DIR instead
# POSTS_DIR = DATA_DIR / "posts"  # This path no longer exists

# ============================================================
# Categories Configuration
# ============================================================

# Glossary categories (random glossary tweets)
GLOSSARY_CATEGORIES = [
    "spell",
    "potion",
    "creature",
    "object",
    "location",
    "organization",
    "concept",
    "character",
]

# Calendar categories (date-based tweets)
CALENDAR_CATEGORIES = [
    "birthday",
    "deathday",
    "event",
]

# All categories
ALL_CATEGORIES = GLOSSARY_CATEGORIES + CALENDAR_CATEGORIES

# Category display names (Japanese)
CATEGORY_DISPLAY_NAMES = {
    "spell": "呪文",
    "potion": "ポーション",
    "creature": "魔法生物",
    "object": "魔法道具",
    "location": "場所",
    "organization": "組織",
    "concept": "魔法概念",
    "character": "キャラクター",
    "birthday": "誕生日",
    "deathday": "命日",
    "event": "イベント",
}

# Category configuration for data processing
CATEGORY_CONFIG = {
    # Glossary categories
    "spell": {
        "file": "spells.json",
        "display_name": "呪文",
        "type": "glossary",
        "singular": "spell",
        "plural": "spells",
    },
    "potion": {
        "file": "potions.json",
        "display_name": "ポーション",
        "type": "glossary",
        "singular": "potion",
        "plural": "potions",
    },
    "creature": {
        "file": "creatures.json",
        "display_name": "魔法生物",
        "type": "glossary",
        "singular": "creature",
        "plural": "creatures",
    },
    "object": {
        "file": "objects.json",
        "display_name": "魔法道具",
        "type": "glossary",
        "singular": "object",
        "plural": "objects",
    },
    "location": {
        "file": "locations.json",
        "display_name": "場所",
        "type": "glossary",
        "singular": "location",
        "plural": "locations",
    },
    "organization": {
        "file": "organizations.json",
        "display_name": "組織",
        "type": "glossary",
        "singular": "organization",
        "plural": "organizations",
    },
    "concept": {
        "file": "concepts.json",
        "display_name": "魔法概念",
        "type": "glossary",
        "singular": "concept",
        "plural": "concepts",
    },
    "character": {
        "file": "characters.json",
        "display_name": "キャラクター",
        "type": "glossary",
        "singular": "character",
        "plural": "characters",
    },
    # Calendar categories
    "birthday": {
        "file": "birthdays.json",
        "display_name": "誕生日",
        "type": "calendar",
        "singular": "birthday",
        "plural": "birthdays",
    },
    "deathday": {
        "file": "deathdays.json",
        "display_name": "命日",
        "type": "calendar",
        "singular": "deathday",
        "plural": "deathdays",
    },
    "event": {
        "file": "events.json",
        "display_name": "イベント",
        "type": "calendar",
        "singular": "event",
        "plural": "events",
    },
}

# ============================================================
# Field Configuration
# ============================================================

# Fields to exclude during validation (internal validation fields)
EXCLUDE_FIELDS_VALIDATION = {
    "exclude_reasons",
    "is_valid",
}

# Fields to exclude when syncing to production
EXCLUDE_FIELDS_PRODUCTION = {
    "exclude_reasons",
    "is_valid",
    "ready_for_production",
}

# Required fields for sync validation (category-specific)
REQUIRED_FIELDS_SYNC = {
    "events": ["event_ja", "tweet_text_ja"],  # events use event_ja instead of name_ja
    "default": ["name_ja", "tweet_text_ja"],  # all other categories
}

# ============================================================
# API Configuration
# ============================================================

# Gist API settings
GIST_API_TIMEOUT = 10  # seconds
GIST_API_MAX_RETRIES = 3
GIST_API_RETRY_DELAY = 1  # seconds (initial delay)
GIST_API_RETRY_BACKOFF = 2  # backoff multiplier (exponential)

# ============================================================
# Tweet Configuration
# ============================================================

# Tweet length limit (X/Twitter enforces 280 chars, but we use 140 for our bot)
TWEET_MAX_LENGTH = 140

# ============================================================
# Backup Configuration
# ============================================================

# Number of backup files to retain per category
BACKUP_RETENTION_COUNT = 10

# ============================================================
# State Management Configuration
# ============================================================

# State file names
STATE_FILE_NAME = "glossary_state.json"
GIST_FILE_NAME = "glossary_state.json"

# State validation settings
MAX_CYCLE_COUNT = 1000  # Maximum reasonable cycle count
TIMESTAMP_PAST_TOLERANCE_YEARS = 1  # Allow timestamps up to 1 year ago
TIMESTAMP_FUTURE_TOLERANCE_MINUTES = 5  # Allow timestamps up to 5 minutes in future

# ============================================================
# CSV Export Configuration
# ============================================================

# Fields to exclude when exporting to CSV
CSV_EXCLUDE_FIELDS = EXCLUDE_FIELDS_VALIDATION

# Category-specific key fields for CSV export
CSV_KEY_FIELDS = {
    "spells": ["id", "name_en", "name_ja", "incantation", "incantation_ja", "tweet_text_ja"],
    "potions": ["id", "name_en", "name_ja", "effect_en", "effect_ja", "tweet_text_ja"],
    "creatures": ["id", "name_en", "name_ja", "description_ja", "tweet_text_ja"],
    "objects": ["id", "name_en", "name_ja", "description_ja", "tweet_text_ja"],
    "locations": ["id", "name_en", "name_ja", "description_ja", "tweet_text_ja"],
    "organizations": ["id", "name_en", "name_ja", "description_ja", "tweet_text_ja"],
    "concepts": ["id", "name_en", "name_ja", "description_ja", "tweet_text_ja"],
    "characters": ["id", "name_en", "name_ja", "description_en", "tweet_text_ja", "ready_for_production"],
    "birthdays": ["id", "name_en", "name_ja", "birthday", "tweet_text_ja"],
    "deathdays": ["id", "event_en", "event_ja", "deathday", "tweet_text_ja"],
    "events": ["id", "event_en", "event_ja", "event_date", "tweet_text_ja"],
}

# List fields that need special handling in CSV
CSV_LIST_FIELDS = {
    "spells": ["name_ja_alt", "sources"],
    "potions": ["name_ja_alt", "ingredients", "sources"],
    "creatures": ["name_ja_alt", "traits"],
    "objects": ["name_ja_alt", "powers"],
    "locations": ["name_ja_alt", "features"],
    "organizations": ["name_ja_alt", "members"],
    "concepts": ["name_ja_alt", "key_examples"],
    "characters": ["name_ja_alt"],
    "birthdays": ["name_ja_alt"],
    "deathdays": [],
    "events": [],
}

# ============================================================
# Helper Functions
# ============================================================


def get_category_file_path(category: str, data_type: str = "drafts") -> Path:
    """
    Get the file path for a category

    Args:
        category: Category name (singular form, e.g., 'spell', 'birthday')
        data_type: Type of data ('drafts', 'production', 'csv', 'posts')

    Returns:
        Path object pointing to the category file

    Raises:
        ValueError: If category or data_type is invalid
    """
    if category not in CATEGORY_CONFIG:
        raise ValueError(f"Unknown category: {category}")

    config = CATEGORY_CONFIG[category]
    filename = config["file"]
    category_type = config["type"]  # 'glossary' or 'calendar'

    if data_type == "drafts":
        return DRAFTS_DIR / category_type / filename
    elif data_type == "production":
        return PRODUCTION_DIR / category_type / filename
    elif data_type == "csv":
        return CSV_DIR / category_type / filename.replace(".json", ".csv")
    elif data_type == "posts":
        return POSTS_DIR / filename
    else:
        raise ValueError(f"Unknown data_type: {data_type}")


def get_category_display_name(category: str) -> str:
    """
    Get the display name (Japanese) for a category

    Args:
        category: Category name (singular form)

    Returns:
        Display name in Japanese

    Raises:
        ValueError: If category is invalid
    """
    if category not in CATEGORY_DISPLAY_NAMES:
        raise ValueError(f"Unknown category: {category}")
    return CATEGORY_DISPLAY_NAMES[category]


def get_required_fields(category: str) -> list:
    """
    Get required fields for a category during sync validation

    Args:
        category: Category name (plural form, e.g., 'spells', 'events')

    Returns:
        List of required field names
    """
    if category in REQUIRED_FIELDS_SYNC:
        return REQUIRED_FIELDS_SYNC[category]
    return REQUIRED_FIELDS_SYNC["default"]
