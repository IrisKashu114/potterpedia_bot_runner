"""
Configuration module for Potterpedia Bot

This module provides centralized configuration management for all scripts.
"""

from .settings import (
    # Paths
    PROJECT_ROOT,
    DATA_DIR,
    DRAFTS_DIR,
    PRODUCTION_DIR,
    CSV_DIR,
    STATE_DIR,
    BACKUP_DIR,
    WIKI_DIR,
    ARCHIVE_DIR,
    CALENDAR_SUBDIR,
    GLOSSARY_SUBDIR,
    CALENDAR_DIR,
    GLOSSARY_DIR,
    # Categories
    GLOSSARY_CATEGORIES,
    CALENDAR_CATEGORIES,
    ALL_CATEGORIES,
    CATEGORY_DISPLAY_NAMES,
    CATEGORY_CONFIG,
    # Fields
    EXCLUDE_FIELDS_VALIDATION,
    EXCLUDE_FIELDS_PRODUCTION,
    REQUIRED_FIELDS_SYNC,
    # API settings
    GIST_API_TIMEOUT,
    GIST_API_MAX_RETRIES,
    GIST_API_RETRY_DELAY,
    GIST_API_RETRY_BACKOFF,
    # Tweet settings
    TWEET_MAX_LENGTH,
    # Backup settings
    BACKUP_RETENTION_COUNT,
    # State settings
    STATE_FILE_NAME,
    GIST_FILE_NAME,
    MAX_CYCLE_COUNT,
    TIMESTAMP_PAST_TOLERANCE_YEARS,
    TIMESTAMP_FUTURE_TOLERANCE_MINUTES,
    # CSV settings
    CSV_EXCLUDE_FIELDS,
    CSV_KEY_FIELDS,
    CSV_LIST_FIELDS,
    # Helper functions
    get_category_file_path,
    get_category_display_name,
    get_required_fields,
)

__all__ = [
    # Paths
    "PROJECT_ROOT",
    "DATA_DIR",
    "DRAFTS_DIR",
    "PRODUCTION_DIR",
    "CSV_DIR",
    "STATE_DIR",
    "BACKUP_DIR",
    "WIKI_DIR",
    "ARCHIVE_DIR",
    "CALENDAR_SUBDIR",
    "GLOSSARY_SUBDIR",
    "CALENDAR_DIR",
    "GLOSSARY_DIR",
    # Categories
    "GLOSSARY_CATEGORIES",
    "CALENDAR_CATEGORIES",
    "ALL_CATEGORIES",
    "CATEGORY_DISPLAY_NAMES",
    "CATEGORY_CONFIG",
    # Fields
    "EXCLUDE_FIELDS_VALIDATION",
    "EXCLUDE_FIELDS_PRODUCTION",
    "REQUIRED_FIELDS_SYNC",
    # API settings
    "GIST_API_TIMEOUT",
    "GIST_API_MAX_RETRIES",
    "GIST_API_RETRY_DELAY",
    "GIST_API_RETRY_BACKOFF",
    # Tweet settings
    "TWEET_MAX_LENGTH",
    # Backup settings
    "BACKUP_RETENTION_COUNT",
    # State settings
    "STATE_FILE_NAME",
    "GIST_FILE_NAME",
    "MAX_CYCLE_COUNT",
    "TIMESTAMP_PAST_TOLERANCE_YEARS",
    "TIMESTAMP_FUTURE_TOLERANCE_MINUTES",
    # CSV settings
    "CSV_EXCLUDE_FIELDS",
    "CSV_KEY_FIELDS",
    "CSV_LIST_FIELDS",
    # Helper functions
    "get_category_file_path",
    "get_category_display_name",
    "get_required_fields",
]
