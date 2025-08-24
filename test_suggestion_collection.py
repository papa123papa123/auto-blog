# test_suggestion_collection.py

import asyncio
import sys
from playwright.async_api import async_playwright

async def test_suggestion_collection():
    """サジェスト収集機能のテスト"""
    print("=== サジェスト収集機能テスト ===")
    
    try:
        from src.advanced_suggestion_collector import AdvancedSuggestionCollector
        
        async with async_playwright() as p:
            # ブラウザを起動（テスト用にヘッドレスモード）
            browser = await p.chromium.launch(
                headless=True,
                args=[
                    "--no-sandbox",
                    "--disable-dev-shm-usage",
                    "--disable-gpu"
                ]
            )
            
            print("✅ ブラウザの起動に成功")
            
            # AdvancedSuggestionCollectorの初期化
            collector = AdvancedSuggestionCollector(browser)
            print("✅ AdvancedSuggestionCollectorの初期化に成功")
            
            # テスト用のメインキーワード
            test_keyword = "ワークマン"
            print(f"\nテストキーワード: 「{test_keyword}」")
            
            # 第1段階のテスト（メインキーワードからサジェスト収集）
            print("\n--- 第1段階テスト開始 ---")
            primary_suggestions = await collector.collect_main_keyword_suggestions(test_keyword)
            
            if primary_suggestions:
                print(f"✅ 第1段階成功: {len(primary_suggestions)}個のサジェストを収集")
                print("最初の5個のサジェスト:")
                for i, suggestion in enumerate(primary_suggestions[:5], 1):
                    print(f"  {i}. {suggestion}")
                
                # 第2段階のテスト（深掘り収集）
                print(f"\n--- 第2段階テスト開始（目標: 100個以上） ---")
                
                # テスト用に短縮版を実行（最初の3個のサジェストのみ）
                test_suggestions = primary_suggestions[:3]
                print(f"テスト用に{len(test_suggestions)}個のサジェストで深掘りテストを実行")
                
                # 深掘り収集のテスト（短縮版）
                for i, suggestion in enumerate(test_suggestions):
                    print(f"\n[{i+1}/{len(test_suggestions)}] 「{suggestion}」から深掘り中...")
                    
                    page = await collector._get_stealth_page()
                    try:
                        # Googleから収集
                        google_suggestions = await collector._collect_suggestions_with_retry(
                            suggestion, "google", page
                        )
                        print(f"  -> Google: {len(google_suggestions)}個")
                        
                        # Yahooから収集
                        yahoo_suggestions = await collector._collect_suggestions_with_retry(
                            suggestion, "yahoo", page
                        )
                        print(f"  -> Yahoo: {len(yahoo_suggestions)}個")
                        
                        # 新しいサジェストを追加
                        all_new = google_suggestions + yahoo_suggestions
                        new_suggestions = [s for s in all_new if s not in collector.collected_suggestions]
                        collector.collected_suggestions.update(new_suggestions)
                        
                        print(f"  -> 新しいサジェスト: {len(new_suggestions)}個（累計: {len(collector.collected_suggestions)}個）")
                        
                        # レート制限回避のための待機
                        await collector._random_delay()
                        
                    finally:
                        await page.close()
                
                # 最終結果の表示
                final_suggestions = list(collector.collected_suggestions)
                print(f"\n=== テスト結果 ===")
                print(f"メインキーワード: {test_keyword}")
                print(f"総サジェスト数: {len(final_suggestions)}個")
                print(f"第1段階: {len(primary_suggestions)}個")
                print(f"第2段階: {len(final_suggestions) - len(primary_suggestions)}個")
                
                # 品質フィルタリングのテスト
                filtered_suggestions = collector.get_suggestions_for_sub_keyword_creation()
                print(f"フィルタリング済み: {len(filtered_suggestions)}個")
                
                if len(filtered_suggestions) > 0:
                    print("\nフィルタリング済みサジェスト（最初の10個）:")
                    for i, suggestion in enumerate(filtered_suggestions[:10], 1):
                        print(f"  {i:2d}. {suggestion}")
                
                print("\n🎉 サジェスト収集テストが完了しました！")
                
            else:
                print("❌ 第1段階でサジェストが取得できませんでした")
                return False
            
            await browser.close()
            return True
            
    except ImportError as e:
        print(f"❌ インポートエラー: {e}")
        return False
    except Exception as e:
        print(f"❌ エラーが発生: {e}")
        import traceback
        traceback.print_exc()
        return False

async def main():
    """メインのテスト関数"""
    print("AdvancedSuggestionCollector サジェスト収集機能のテストを開始します...\n")
    
    # サジェスト収集テスト
    result = await test_suggestion_collection()
    
    if result:
        print("\n✅ テストが成功しました！")
        print("システムは正常に動作しており、サジェスト収集が可能です。")
    else:
        print("\n❌ テストが失敗しました。")
        print("問題を確認して修正してください。")
    
    return result

if __name__ == "__main__":
    # Windows環境での文字エンコーディング設定
    if sys.platform == "win32":
        import sys
        sys.stdout.reconfigure(encoding='utf-8')
    
    # 非同期メイン関数の実行
    result = asyncio.run(main())
    sys.exit(0 if result else 1)
