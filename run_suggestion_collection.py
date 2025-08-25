#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Google SERP API サジェスト収集システムの実行用スクリプト
1. collect_google_suggestions.py を実行してサジェストを収集
2. extract_seo_content.py を実行してSEO用コンテンツを抽出
"""

import asyncio
import subprocess
import sys
import os
from pathlib import Path

def run_python_script(script_name: str, description: str) -> bool:
    """Pythonスクリプトを実行"""
    print(f"\n{'='*60}")
    print(f"🚀 {description}")
    print(f"{'='*60}")
    
    try:
        # スクリプトが存在するかチェック
        if not os.path.exists(script_name):
            print(f"❌ スクリプトが見つかりません: {script_name}")
            return False
        
        # スクリプトを実行
        result = subprocess.run([sys.executable, script_name], 
                              capture_output=True, 
                              text=True, 
                              encoding='utf-8')
        
        # 標準出力を表示
        if result.stdout:
            print(result.stdout)
        
        # エラー出力があれば表示
        if result.stderr:
            print(f"⚠️  警告・エラー:")
            print(result.stderr)
        
        # 終了コードをチェック
        if result.returncode == 0:
            print(f"✅ {description}が正常に完了しました")
            return True
        else:
            print(f"❌ {description}が失敗しました（終了コード: {result.returncode}）")
            return False
            
    except Exception as e:
        print(f"❌ スクリプト実行中にエラーが発生しました: {e}")
        return False

async def main():
    """メイン実行関数"""
    print("🎯 Google SERP API サジェスト収集システム")
    print("=" * 60)
    print("このスクリプトは以下の処理を順次実行します:")
    print("1. サジェスト収集（collect_google_suggestions_保護済み_絶対変更禁止.py）")
    print("2. SEO用コンテンツ抽出（extract_seo_content.py）")
    print("=" * 60)
    
    # 必要なファイルの存在確認
    required_files = [
        "collect_google_suggestions_保護済み_絶対変更禁止.py",
        "extract_seo_content.py"
    ]
    
    missing_files = []
    for file in required_files:
        if not os.path.exists(file):
            missing_files.append(file)
    
    if missing_files:
        print("❌ 必要なファイルが見つかりません:")
        for file in missing_files:
            print(f"   - {file}")
        print("\nスクリプトファイルが正しいディレクトリに配置されているか確認してください。")
        return
    
    print("✅ 必要なファイルの確認が完了しました")
    
    # 環境変数の確認
    if not os.getenv('SERPAPI_API_KEY'):
        print("❌ SERPAPI_API_KEYが設定されていません")
        print(".envファイルにSERPAPI_API_KEYを設定してください")
        return
    
    print("✅ 環境変数の確認が完了しました")
    
    # ステップ1: サジェスト収集
    print("\n" + "="*60)
    print("📊 ステップ1: Google SERP API サジェスト収集")
    print("="*60)
    
    success = run_python_script(
        "collect_google_suggestions_保護済み_絶対変更禁止.py",
        "Google SERP API サジェスト収集"
    )
    
    if not success:
        print("❌ サジェスト収集が失敗したため、処理を中断します")
        return
    
    # 生成されたJSONファイルを確認
    json_files = []
    for file in os.listdir('.'):
        if file.startswith('serp_collected_') and file.endswith('.json'):
            json_files.append(file)
    
    if not json_files:
        print("❌ サジェスト収集の結果ファイルが見つかりません")
        return
    
    # 最新のファイルを表示
    json_files.sort(reverse=True)
    latest_file = json_files[0]
    print(f"\n📁 生成されたファイル: {latest_file}")
    
    # ステップ2: SEO用コンテンツ抽出
    print("\n" + "="*60)
    print("🔍 ステップ2: SEO用コンテンツ抽出")
    print("="*60)
    
    success = run_python_script(
        "extract_seo_content.py",
        "SEO用コンテンツ抽出"
    )
    
    if not success:
        print("❌ SEO用コンテンツ抽出が失敗しました")
        return
    
    # 生成されたテキストファイルを確認
    txt_files = []
    for file in os.listdir('.'):
        if file.startswith('seo_content_') and file.endswith('.txt'):
            txt_files.append(file)
    
    if txt_files:
        txt_files.sort(reverse=True)
        latest_txt = txt_files[0]
        print(f"\n📁 生成されたテキストファイル: {latest_txt}")
    
    # 完了メッセージ
    print("\n" + "="*60)
    print("🎉 全処理が完了しました！")
    print("="*60)
    print("生成されたファイル:")
    
    for file in json_files:
        print(f"  📊 {file}")
    
    for file in txt_files:
        print(f"  📝 {file}")
    
    print(f"\n次のステップ:")
    print("1. 生成されたテキストファイルを確認")
    print("2. SEO用のH2・H3タグ生成に活用")
    print("3. 必要に応じてキーワードを調整して再実行")

if __name__ == "__main__":
    asyncio.run(main())
