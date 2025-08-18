# config/settings.py
"""
Phase 2: ハル式月産10,000記事システム - 設定ファイル
"""

import os
from pathlib import Path

# プロジェクトのルートディレクトリ
BASE_DIR = Path(__file__).parent.parent

# WordPress設定
WORDPRESS_CONFIG = {
    'url': 'https://your-site.com',
    'username': 'auto_poster2',
    'password': '',
}

# ハル式SEO設定
HARU_SEO_CONFIG = {
    'h2_count': 2,           # H2見出し数（ハル式固定）
    'h3_count': 12,          # H3見出し数（ハル式固定）
    'target_word_count': 3000,
}

print("✅ ハル式設定ファイル読み込み完了")
