# run_yahoo_competitor_analysis.py

import asyncio
import sys
from pathlib import Path
from src.yahoo_competitor_analyzer import YahooCompetitorAnalyzer
import pandas as pd

def load_keywords_from_csv(csv_path: str) -> list[str]:
    """CSVファイルからキーワードを読み込み"""
    try:
        df = pd.read_csv(csv_path, encoding='utf-8')
        if 'キーワード' in df.columns:
            keywords = df['キーワード'].dropna().astype(str).tolist()
        elif 'keyword' in df.columns:
            keywords = df['keyword'].dropna().astype(str).tolist()
        else:
            print("[ERROR] CSVファイルに'キーワード'または'keyword'列が見つかりません。")
            return []
        
        print(f"[OK] CSVから{len(keywords)}件のキーワードを読み込みました。")
        return keywords
        
    except Exception as e:
        print(f"[ERROR] CSVファイルの読み込みに失敗: {e}")
        return []

def load_keywords_from_input() -> list[str]:
    """ユーザー入力からキーワードを取得"""
    print("\n分析したいキーワードを1行に1つずつ入力してください。")
    print("入力を終えたら、何も入力せずにEnterキーを押してください。")
    
    keywords = []
    while True:
        keyword = input("> ").strip()
        if not keyword:
            break
        keywords.append(keyword)
    
    return keywords

def configure_cleanup_settings():
    """クリーンアップ設定をユーザーに確認"""
    print("\n=== HTMLファイルの自動クリーンアップ設定 ===")
    print("分析完了後にHTMLファイルを自動削除しますか？")
    print("（ディスク容量を節約し、プライバシーも保護されます）")
    
    auto_cleanup = input("自動クリーンアップを有効にしますか？ (y/n, デフォルト: y): ").strip().lower()
    if auto_cleanup == 'n':
        print("[INFO] 自動クリーンアップを無効にしました。HTMLファイルは手動で削除してください。")
        return False, 0
    
    print("[INFO] 自動クリーンアップが有効です。")
    
    # クリーンアップタイミングの設定
    print("\nクリーンアップのタイミングを選択してください:")
    print("1: 分析完了直後（推奨）")
    print("2: 分析完了後1時間")
    print("3: 分析完了後6時間")
    print("4: カスタム時間")
    
    choice = input("選択してください (1-4, デフォルト: 1): ").strip()
    
    if choice == "1" or choice == "":
        cleanup_hours = 0
        print("[INFO] 分析完了直後にクリーンアップを実行します。")
    elif choice == "2":
        cleanup_hours = 1
        print("[INFO] 分析完了後1時間でクリーンアップを実行します。")
    elif choice == "3":
        cleanup_hours = 6
        print("[INFO] 分析完了後6時間でクリーンアップを実行します。")
    elif choice == "4":
        try:
            cleanup_hours = int(input("時間数を入力してください（例: 2）: ").strip())
            print(f"[INFO] 分析完了後{cleanup_hours}時間でクリーンアップを実行します。")
        except ValueError:
            cleanup_hours = 0
            print("[WARN] 無効な入力です。分析完了直後にクリーンアップを実行します。")
    else:
        cleanup_hours = 0
        print("[INFO] 分析完了直後にクリーンアップを実行します。")
    
    return True, cleanup_hours

def main():
    print("=== Yahoo検索ベース競合分析システム ===")
    print("SERP APIを使わずにローカルでHTML収集・解析を行います。")
    
    # クリーンアップ設定
    auto_cleanup, cleanup_hours = configure_cleanup_settings()
    
    # キーワードの取得方法を選択
    print("\nキーワードの取得方法を選択してください:")
    print("1: CSVファイルから読み込み")
    print("2: 手動入力")
    print("3: テスト用キーワード（日傘 おすすめ, プログラミングスクール, ダイエット方法）")
    
    choice = input("選択してください (1-3): ").strip()
    
    keywords = []
    
    if choice == "1":
        csv_path = input("CSVファイルのパスを入力してください: ").strip()
        if not csv_path:
            print("[ERROR] パスが入力されませんでした。")
            return
        keywords = load_keywords_from_csv(csv_path)
        
    elif choice == "2":
        keywords = load_keywords_from_input()
        
    elif choice == "3":
        keywords = ["日傘 おすすめ", "プログラミングスクール", "ダイエット方法"]
        print(f"[INFO] テスト用キーワードを使用: {keywords}")
        
    else:
        print("[ERROR] 無効な選択です。")
        return
    
    if not keywords:
        print("[ERROR] キーワードが取得できませんでした。")
        return
    
    print(f"\n分析対象キーワード ({len(keywords)}件):")
    for i, keyword in enumerate(keywords, 1):
        print(f"  {i}. {keyword}")
    
    # 分析の実行確認
    confirm = input(f"\n{len(keywords)}件のキーワードで競合分析を開始しますか？ (y/n): ").strip().lower()
    if confirm != 'y':
        print("分析をキャンセルしました。")
        return
    
    # 非同期分析の実行
    async def run_analysis():
        try:
            # クリーンアップ設定でアナライザーを初期化
            if auto_cleanup:
                analyzer = YahooCompetitorAnalyzer(
                    auto_cleanup=True, 
                    cleanup_after_hours=cleanup_hours
                )
            else:
                analyzer = YahooCompetitorAnalyzer(auto_cleanup=False)
            
            print(f"\n--- 分析開始 ---")
            results_df = await analyzer.run_analysis(keywords)
            
            # 結果の表示
            print(f"\n=== 分析結果 ===")
            print(results_df.to_string(index=False))
            
            # サマリーの表示
            print(f"\n{analyzer.get_analysis_summary(results_df)}")
            
            # 結果を保存
            output_file = analyzer.save_results(results_df)
            if output_file:
                print(f"\n[SUCCESS] 分析完了！結果を保存しました: {output_file}")
            else:
                print(f"\n[WARNING] 分析は完了しましたが、結果の保存に失敗しました。")
            
            # 最終的なストレージ状況を表示
            final_storage_status = analyzer.get_storage_status()
            print(f"\n=== 最終ストレージ状況 ===")
            print(f"HTMLファイル数: {final_storage_status['file_count']}件")
            print(f"使用容量: {final_storage_status['total_size_mb']}MB")
            print(f"ディレクトリ: {final_storage_status['directory']}")
            
            if final_storage_status['file_count'] == 0:
                print("[OK] 全てのHTMLファイルが正常にクリーンアップされました。")
            else:
                print(f"[INFO] {final_storage_status['file_count']}件のHTMLファイルが残っています。")
                
                # 手動クリーンアップの提案
                if not auto_cleanup:
                    manual_cleanup = input("\n手動でHTMLファイルを削除しますか？ (y/n): ").strip().lower()
                    if manual_cleanup == 'y':
                        analyzer.manual_cleanup(keywords)
                        print("[OK] 手動クリーンアップが完了しました。")
                
        except Exception as e:
            print(f"[ERROR] 分析中にエラーが発生しました: {e}")
            import traceback
            traceback.print_exc()
    
    # 非同期処理の実行
    asyncio.run(run_analysis())

if __name__ == "__main__":
    main()
