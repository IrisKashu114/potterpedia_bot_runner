#!/usr/bin/env python3
"""
データローダー

JSONデータファイルの読み込み機能を提供します。
"""

import json
from pathlib import Path
from typing import Dict, Any


def load_data_file(file_path: Path) -> Dict[str, Any]:
    """
    JSONデータファイルを読み込む

    Args:
        file_path: 読み込むJSONファイルのパス

    Returns:
        読み込んだJSONデータ（辞書形式）

    Raises:
        FileNotFoundError: ファイルが存在しない場合
        json.JSONDecodeError: JSON形式が不正な場合
    """
    if not file_path.exists():
        raise FileNotFoundError(f"データファイルが見つかりません: {file_path}")

    with open(file_path, 'r', encoding='utf-8') as f:
        return json.load(f)
