# run_product_database_build.py
"""
【最終版】製品データベース構築フローを実行する、安定化されたスクリプト。
"""

import asyncio
import json
import os
import sys
from pathlib import Path

from dotenv import load_dotenv
from playwright.async_api import async_playwright

# --- モジュール検索パスを追加 ---
sys.path.append(str(Path(__file__).resolve().parent / 'src'))
# --------------------------

# (evaluate_quality関数は変更なし)
def evaluate_quality(file_path: str):
    print("\n--- 品質の自動評価を開始 ---")
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        total_products = len(data)
        if total_products == 0:
            print("[評価NG] 製品情報が1件もありません。")
            return
        success_count = sum(1 for p in data if not p.get('error'))
        well_defined_count = sum(1 for p in data if p.get('specs') and isinstance(p['specs'], dict) and len(p['specs']) >= 5)
        success_rate = (success_count / total_products) * 100
        quality_rate = (well_defined_count / total_products) * 100
        print(f"\n[評価サマリー]")
        print(f"- 対象製品数: {total_products} 件")
        print(f"- 処理成功率: {success_rate:.1f}% ({success_count}/{total_products})")
        print(f"- 高品質データ率（スペック5項目以上）: {quality_rate:.1f}% ({well_defined_count}/{total_products})")
        errors = [f"  - Rank {p['rank']} ({p['name']}): {p['error']}" for p in data if p.get('error')]
        if errors:
            print("\n[エラー詳細]")
            print("\n".join(errors))
        print("\n--- 品質の自動評価を完了 ---")
    except Exception as e:
        print(f"[評価エラー] {e}")

async def main():
    """メインの実行関数"""
    load_dotenv()
    if not (os.getenv("GEMINI_API_KEY") and os.getenv("SERP_API_KEY")):
        print("[エラー] .envファイルにAPIキーが設定されていません。")
        return

    from flows.product_database_flow import ProductDatabaseFlow
    from gemini_generator import GeminiGenerator
    from serp_analyzer import SerpAnalyzer

    # --- 実行パラメータ ---
    TARGET_CATEGORY_URL = "https://kakaku.com/kaden/fan/"
    TARGET_CATEGORY_NAME = "扇風機"
    NUMBER_OF_PRODUCTS = 10
    HEADLESS_MODE = False
    # --------------------

    print("--- モジュールの初期化を開始 ---")
    gemini_generator = GeminiGenerator()
    serp_analyzer = SerpAnalyzer(api_key=os.getenv("SERP_API_KEY"))
    flow = ProductDatabaseFlow(gemini_generator, serp_analyzer)
    print("--- モジュールの初期化が完了 ---")

    # --- ブラウザを一度だけ起動し、フローに渡す ---
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=HEADLESS_MODE)
        result_file_path = await flow.build_database_from_category(
            browser=browser,
            category_top_url=TARGET_CATEGORY_URL,
            category_name=TARGET_CATEGORY_NAME,
            num_products=NUMBER_OF_PRODUCTS
        )
        await browser.close()

    if result_file_path:
        evaluate_quality(result_file_path)

if __name__ == "__main__":
    sys.stdout.reconfigure(encoding='utf-8')
    sys.stderr.reconfigure(encoding='utf-8')
    asyncio.run(main())
