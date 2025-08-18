# run_screenshot_from_url.py
"""
【最終版】URL生成戦略を実行するスクリプト。
1. 比較ページのURLを生成する。
2. 生成したURLのスクリーンショットを撮影する。
3. AIで画像からスペック情報を抽出する。
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

    from kakaku_url_generator import KakakuUrlGenerator
    from spec_extractor import SpecExtractor
    from gemini_generator import GeminiGenerator

    # --- 実行パラメータ ---
    TARGET_CATEGORY_URL = "https://kakaku.com/kaden/fan/"
    TARGET_CATEGORY_NAME = "扇風機"
    SCREENSHOT_PATH = "final_comparison.png"
    # --------------------

    # 1. 比較ページのURLを生成
    generator = KakakuUrlGenerator(headless=True)
    comparison_url = await generator.generate_comparison_url(TARGET_CATEGORY_URL)

    if not comparison_url:
        print("\n[処理中断] 比較URLの生成に失敗したため、処理を中断します。")
        return

    # 2. 生成されたURLのスクリーンショットを撮影
    print(f"\n[2/3] 生成されたURLのスクリーンショットを撮影します...")
    print(f"  -> URL: {comparison_url}")
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)
        page = await browser.new_page(viewport={"width": 1920, "height": 1080})
        try:
            await page.goto(comparison_url, timeout=60000, wait_until="domcontentloaded")
            await page.wait_for_selector("#compTbl", state="visible", timeout=30000)
            await page.evaluate("document.body.style.zoom = 0.5")
            await asyncio.sleep(2)
            await page.screenshot(path=SCREENSHOT_PATH, full_page=True)
            print(f"[OK] スクリーンショットを '{SCREENSHOT_PATH}' に保存しました。")
        except Exception as e:
            print(f"[NG] スクリーンショット撮影中にエラー: {e}")
            return
        finally:
            await browser.close()

    # 3. AIで画像からスペック情報を抽出
    gemini = GeminiGenerator()
    extractor = SpecExtractor(gemini)
    final_json_string = extractor.extract_from_image(SCREENSHOT_PATH)

    # 4. 結果をファイルに保存
    print("\n[3/3] 抽出結果をファイルに保存します...")
    output_dir = Path("product_databases")
    output_dir.mkdir(exist_ok=True)
    timestamp = datetime.datetime.now().strftime("%Y-%m-%d_%H%M%S")
    safe_category_name = "".join(c for c in TARGET_CATEGORY_NAME if c.isalnum()).rstrip()
    output_filename = f"{timestamp}_{safe_category_name}_url_strategy_db.json"
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
