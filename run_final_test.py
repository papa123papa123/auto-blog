# run_final_test.py
"""
【最終版】「人間と同じ操作」と「究極のシンプルプロンプト」で、
比較ページのスペック情報を、確実かつ高品質に抽出する最終スクリプト。
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
    # ★★★ スクリーンショットを専用フォルダに保存 ★★★
    SCREENSHOT_DIR = Path("screenshots")
    SCREENSHOT_DIR.mkdir(exist_ok=True)
    # ★★★★★★★★★★★★★★★★★★★★★★★★★★★★★
    
    print("\n--- 最終テストを開始します ---")
    screenshot_paths = []
    comparison_urls = []

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False, args=["--start-maximized"])
        context = await browser.new_context(no_viewport=True)
        page = await context.new_page()

        try:
            print(f"[INFO] カテゴリページにアクセスし、全比較URLを抽出します: {TARGET_CATEGORY_URL}")
            await page.goto(TARGET_CATEGORY_URL, timeout=60000, wait_until="domcontentloaded")
            await page.wait_for_timeout(3000)
            
            all_links = await page.evaluate("() => Array.from(document.querySelectorAll('a')).filter(a => a.textContent.includes('上位製品をまとめて比較する')).map(a => a.href)")
            if not all_links:
                print("[NG] 「上位製品をまとめて比較する」リンクが見つかりませんでした。")
                return
            
            comparison_urls = all_links
            print(f"[OK] {len(comparison_urls)}個の比較URLの抽出が完了しました。")
            await page.close()

            for i, url in enumerate(comparison_urls):
                print(f"\n--- [{i+1}/{len(comparison_urls)}] 個目の比較表を処理します ---")
                compare_page = await context.new_page()
                try:
                    await compare_page.goto(url, timeout=60000, wait_until="networkidle")
                    
                    print("[INFO] ページを70%にズームアウトします...")
                    await compare_page.evaluate("document.body.style.zoom = 0.7")
                    await asyncio.sleep(2)

                    output_path = SCREENSHOT_DIR / f"comparison_{i+1}.png"
                    await compare_page.screenshot(path=output_path, full_page=True, animations="disabled")
                    screenshot_paths.append(str(output_path))
                    print(f"[INFO] スクリーンショットを撮影しました: {output_path}")

                finally:
                    await compare_page.close()

            print("\n[OK] すべての比較表のスクリーンショット撮影が完了しました。")

        except Exception as e:
            print(f"[NG] 操作中にエラーが発生しました: {e}")
            return
        finally:
            await browser.close()

    if not screenshot_paths:
        print("\n[処理中断] 撮影されたスクリーンショットがないため、処理を終了します。")
        return
        
    gemini = GeminiGenerator()
    extractor = SpecExtractor(gemini)
    final_json_string = extractor.extract_from_images(screenshot_paths)

    print("\n--- 抽出結果をファイルに保存します ---")
    output_dir = Path("product_databases")
    output_dir.mkdir(exist_ok=True)
    timestamp = datetime.datetime.now().strftime("%Y-%m-%d_%H%M%S")
    safe_category_name = "".join(c for c in TARGET_CATEGORY_NAME if c.isalnum()).rstrip()
    output_filename = f"{timestamp}_{safe_category_name}_final_db.json"
    output_filepath = output_dir / output_filename

    try:
        parsed_json = json.loads(final_json_string)
        with open(output_filepath, "w", encoding="utf-8") as f:
            json.dump(parsed_json, f, indent=2, ensure_ascii=False)
    except json.JSONDecodeError:
        output_filepath = output_filepath.with_suffix('.txt')
        with open(output_filepath, "w", encoding="utf-8") as f:
            f.write(final_json_string)

    print(f"[成功] 処理が完了しました！ 結果ファイル: {output_filepath}")


if __name__ == "__main__":
    if sys.platform == "win32":
        sys.stdout.reconfigure(encoding='utf-8')
        sys.stderr.reconfigure(encoding='utf-8')
    
    asyncio.run(main())
