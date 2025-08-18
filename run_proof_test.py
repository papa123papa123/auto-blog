# run_proof_test.py
"""
【最終証拠撮影】Bot対策により、意図的に違うページが表示されていないかを確認するためのスクリプト。
1. 最初にカテゴリページ自体のスクリーンショットを撮影する。
2. ズーム率を70%に変更して、比較表のスクリーンショットを撮影する。
"""
import asyncio
import datetime
import json
import os
import sys
from pathlib import Path
import re

from dotenv import load_dotenv
from playwright.async_api import async_playwright

# --- モジュール検索パスを追加 ---
sys.path.append(str(Path(__file__).resolve().parent / 'src'))
# --------------------------

async def main():
    """メインの実行関数"""
    load_dotenv()
    if not os.getenv("GEMINI_API_KEY"):
        print("[エラー] .envファイルに GEMINI_API_KEY が設定されていません。")
        return

    from spec_extractor import SpecExtractor
    from gemini_generator import GeminiGenerator

    # --- 実行パラメータ ---
    TARGET_CATEGORY_URL = "https://kakaku.com/kaden/fan/"
    TARGET_CATEGORY_NAME = "扇風機"
    SCREENSHOT_PREFIX = "proof_comparison"
    # --------------------

    print("\n--- 最終証拠撮影を開始します ---")
    screenshot_paths = []
    comparison_urls = []

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False, args=["--start-maximized"])
        context = await browser.new_context(no_viewport=True)
        page = await context.new_page()

        try:
            # 1. カテゴリページにアクセス
            print(f"[INFO] カテゴリページにアクセスします: {TARGET_CATEGORY_URL}")
            await page.goto(TARGET_CATEGORY_URL, timeout=60000, wait_until="domcontentloaded")
            await page.wait_for_timeout(3000)
            
            # ★★★ 証拠撮影 #1: カテゴリページのスクリーンショット ★★★
            print("[INFO] 証拠として、カテゴリページ全体のスクリーンショットを撮影します...")
            await page.screenshot(path="proof_category_page.png", full_page=True)
            print("[OK] 証拠写真 'proof_category_page.png' を保存しました。")

            # 2. 比較ページのURLをすべて取得
            print("\n[INFO] JavaScriptを実行して、全比較URLを一括抽出します。")
            all_links = await page.evaluate("() => Array.from(document.querySelectorAll('a')).filter(a => a.textContent.includes('上位製品をまとめて比較する')).map(a => a.href)")
            if not all_links:
                print("[NG] 「上位製品をまとめて比較する」リンクが見つかりませんでした。")
                return
            
            comparison_urls = all_links
            print(f"[OK] {len(comparison_urls)}個の比較URLの抽出が完了しました。")
            await page.close()

            # 3. 抽出したURLを順番に処理してスクリーンショットを撮影
            for i, url in enumerate(comparison_urls):
                print(f"\n--- [{i+1}/{len(comparison_urls)}] 個目の比較表を処理します ---")
                compare_page = await context.new_page()
                try:
                    print(f"[INFO] 比較ページにアクセスします: {url}")
                    await compare_page.goto(url, timeout=60000, wait_until="networkidle")
                    
                    # ★★★ ズーム率を70%に変更 ★★★
                    print("[INFO] ページを70%にズームアウトします...")
                    await compare_page.evaluate("document.body.style.zoom = 0.7")
                    await asyncio.sleep(2)

                    output_path = f"{SCREENSHOT_PREFIX}_{i+1}.png"
                    await compare_page.screenshot(path=output_path, full_page=True, animations="disabled", timeout=30000)
                    screenshot_paths.append(output_path)
                    print(f"[INFO] スクリーンショットを撮影しました: {output_path}")

                finally:
                    await compare_page.close()

            print("\n[OK] すべての比較表のスクリーンショット撮影が完了しました。")

        except Exception as e:
            print(f"[NG] 操作中にエラーが発生しました: {e}")
            return
        finally:
            await browser.close()

    # 4. AIに画像を渡す
    if not screenshot_paths:
        print("\n[処理中断] 撮影されたスクリーンショットがないため、処理を終了します。")
        return
        
    gemini = GeminiGenerator()
    extractor = SpecExtractor(gemini)
    final_json_string = extractor.extract_from_images(screenshot_paths)

    # 5. 結果をファイルに保存
    print("\n--- 抽出結果をファイルに保存します ---")
    output_dir = Path("product_databases")
    output_dir.mkdir(exist_ok=True)
    timestamp = datetime.datetime.now().strftime("%Y-%m-%d_%H%M%S")
    safe_category_name = "".join(c for c in TARGET_CATEGORY_NAME if c.isalnum()).rstrip()
    output_filename = f"{timestamp}_{safe_category_name}_proof_db.json"
    output_filepath = output_dir / output_filename

    try:
        json_match = re.search(r'```json\s*(\[.*\])\s*```', final_json_string, re.DOTALL)
        if json_match:
            json_str = json_match.group(1)
            parsed_json = json.loads(json_str)
            with open(output_filepath, "w", encoding="utf-8") as f:
                json.dump(parsed_json, f, indent=2, ensure_ascii=False)
        else:
            output_filepath = output_filepath.with_suffix('.txt')
            with open(output_filepath, "w", encoding="utf-8") as f:
                f.write(final_json_string)
    except (json.JSONDecodeError, AttributeError):
        output_filepath = output_filepath.with_suffix('.txt')
        with open(output_filepath, "w", encoding="utf-8") as f:
            f.write(final_json_string)

    print(f"[成功] 処理が完了しました！ 結果ファイル: {output_filepath}")


if __name__ == "__main__":
    if sys.platform == "win32":
        sys.stdout.reconfigure(encoding='utf-8')
        sys.stderr.reconfigure(encoding='utf-8')
    
    asyncio.run(main())
