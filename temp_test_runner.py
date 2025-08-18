
import asyncio
import os
from dotenv import load_dotenv
from src.serp_analyzer import SerpAnalyzer

# .envファイルから環境変数を読み込む
load_dotenv()

async def main():
    """
    Playwrightを使った新しいメソッドをテストする。
    """
    # 環境変数からAPIキーを取得
    api_key = os.getenv("SERP_API_KEY")
    if not api_key:
        print("[エラー] 環境変数 SERP_API_KEY が設定されていません。")
        return

    analyzer = SerpAnalyzer(api_key=api_key)
    
    # 扇風機カテゴリのURL
    test_url = "https://kakaku.com/kaden/fan/"
    
    print(f"--- テスト開始: {test_url} ---")
    
    # 新しいメソッドを呼び出す
    ranking_url = await analyzer.find_kakaku_ranking_url(test_url)
    
    if ranking_url:
        print(f"\n--- テスト成功 ---")
        print(f"取得したランキングURL: {ranking_url}")
    else:
        print(f"\n--- テスト失敗 ---")
        print("ランキングURLを取得できませんでした。")

if __name__ == "__main__":
    asyncio.run(main())
