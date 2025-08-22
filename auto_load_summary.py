#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
会話要約の自動読み込みスクリプト
次回作業開始時に実行して、前回の作業内容を確認できます
"""

import os
from datetime import datetime

def load_conversation_summary():
    """会話要約ファイルを読み込んで表示"""
    
    summary_file = "conversation_summary.md"
    
    if not os.path.exists(summary_file):
        print("❌ 会話要約ファイルが見つかりません")
        print(f"ファイル: {summary_file}")
        return False
    
    try:
        with open(summary_file, 'r', encoding='utf-8') as f:
            content = f.read()
        
        print("=" * 80)
        print("📚 前回の作業内容 - 会話要約")
        print("=" * 80)
        print(f"📅 読み込み日時: {datetime.now().strftime('%Y年%m月%d日 %H:%M:%S')}")
        print("=" * 80)
        print()
        print(content)
        print("=" * 80)
        print("✅ 会話要約の読み込みが完了しました")
        print("🚀 作業を継続できます")
        print("=" * 80)
        
        return True
        
    except Exception as e:
        print(f"❌ ファイル読み込みエラー: {e}")
        return False

def show_quick_start_guide():
    """クイックスタートガイドを表示"""
    
    print("\n" + "=" * 80)
    print("🚀 クイックスタートガイド")
    print("=" * 80)
    
    print("""
1. 仮想環境の有効化:
   .\\venv\\Scripts\\Activate.ps1

2. 環境変数の設定 (.envファイル):
   DATAFORSEO_LOGIN=your_login
   DATAFORSEO_PASSWORD=your_password
   SERPAPI_API_KEY=your_key

3. 最適化版の実行:
   python run_dataforseo_competitor_research.py
   または
   python run_serpapi_optimized_competitor_research.py

4. 厳密基準をクリアするキーワードの特定

5. 記事作成への移行
""")
    
    print("=" * 80)

def main():
    """メイン処理"""
    
    print("🔄 会話要約の自動読み込みを開始します...")
    print()
    
    # 会話要約を読み込み
    if load_conversation_summary():
        # クイックスタートガイドを表示
        show_quick_start_guide()
        
        print("\n🎯 次のステップ:")
        print("1. 環境変数を設定")
        print("2. 最適化版をテスト実行")
        print("3. 厳密基準クリアキーワードを特定")
        print("4. 記事作成に進む")
        
    else:
        print("\n⚠️ 会話要約の読み込みに失敗しました")
        print("手動で conversation_summary.md を確認してください")

if __name__ == "__main__":
    main()
