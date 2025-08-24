# test_advanced_suggestion_collector.py

import asyncio
import sys
from playwright.async_api import async_playwright

# テスト用の簡単なバージョン
async def test_basic_functionality():
    """基本的な機能をテスト"""
    print("=== AdvancedSuggestionCollector 基本テスト ===")
    
    try:
        async with async_playwright() as p:
            # ブラウザを起動
            browser = await p.chromium.launch(
                headless=True,
                args=[
                    "--no-sandbox",
                    "--disable-dev-shm-usage"
                ]
            )
            
            print("✅ ブラウザの起動に成功")
            
            # ページを作成
            page = await browser.new_page()
            print("✅ ページの作成に成功")
            
            # 簡単なテスト：Googleにアクセス
            await page.goto("https://www.google.com", timeout=30000)
            print("✅ Googleへのアクセスに成功")
            
            # タイトルを取得
            title = await page.title()
            print(f"✅ ページタイトル: {title}")
            
            await page.close()
            await browser.close()
            print("✅ ブラウザの終了に成功")
            
    except Exception as e:
        print(f"❌ エラーが発生: {e}")
        return False
    
    return True

async def test_suggestion_collector():
    """AdvancedSuggestionCollectorのテスト"""
    print("\n=== AdvancedSuggestionCollector クラステスト ===")
    
    try:
        from src.advanced_suggestion_collector import AdvancedSuggestionCollector
        
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            
            # クラスの初期化テスト
            collector = AdvancedSuggestionCollector(browser)
            print("✅ AdvancedSuggestionCollectorの初期化に成功")
            
            # ステルスページの作成テスト
            page = await collector._get_stealth_page()
            print("✅ ステルスページの作成に成功")
            
            await page.close()
            await browser.close()
            
    except ImportError as e:
        print(f"❌ インポートエラー: {e}")
        return False
    except Exception as e:
        print(f"❌ エラーが発生: {e}")
        return False
    
    return True

async def main():
    """メインのテスト関数"""
    print("AdvancedSuggestionCollectorシステムのテストを開始します...\n")
    
    # 基本機能テスト
    basic_test_result = await test_basic_functionality()
    
    # クラステスト
    class_test_result = await test_suggestion_collector()
    
    # 結果の表示
    print("\n=== テスト結果 ===")
    print(f"基本機能テスト: {'✅ 成功' if basic_test_result else '❌ 失敗'}")
    print(f"クラステスト: {'✅ 成功' if class_test_result else '❌ 失敗'}")
    
    if basic_test_result and class_test_result:
        print("\n🎉 全てのテストが成功しました！")
        print("システムは正常に動作しています。")
        return True
    else:
        print("\n⚠️  一部のテストが失敗しました。")
        print("問題を確認して修正してください。")
        return False

if __name__ == "__main__":
    # Windows環境での文字エンコーディング設定
    if sys.platform == "win32":
        import sys
        sys.stdout.reconfigure(encoding='utf-8')
    
    # 非同期メイン関数の実行
    result = asyncio.run(main())
    sys.exit(0 if result else 1)
