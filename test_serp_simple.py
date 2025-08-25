#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
SERP APIの動作テスト - シンプル版
"""

import os
from dotenv import load_dotenv
from pathlib import Path

# 環境変数の読み込み
load_dotenv(dotenv_path=Path(__file__).parent / ".env")

def test_env_loading():
    """環境変数の読み込みテスト"""
    print("🔍 環境変数読み込みテスト開始")
    
    serp_api_key = os.getenv('SERPAPI_API_KEY')
    print(f"SERPAPI_API_KEY: {'設定済み' if serp_api_key else '未設定'}")
    
    if not serp_api_key:
        print("❌ SERPAPI_API_KEYが設定されていません")
        print("📝 .envファイルにSERPAPI_API_KEYを追加してください")
        return False
    
    print("✅ 環境変数読み込み完了")
    return True

def test_user_input():
    """ユーザー入力テスト"""
    print("\n📝 ユーザー入力テスト開始")
    
    try:
        user_input = input("テスト用キーワードを入力してください: ").strip()
        print(f"✅ 入力完了: '{user_input}'")
        return True
    except Exception as e:
        print(f"❌ 入力エラー: {e}")
        return False

if __name__ == "__main__":
    print("🚀 SERP API動作テスト開始")
    print("=" * 40)
    
    # 環境変数テスト
    if not test_env_loading():
        exit(1)
    
    # ユーザー入力テスト
    if not test_user_input():
        exit(1)
    
    print("\n✅ すべてのテストが完了しました")
