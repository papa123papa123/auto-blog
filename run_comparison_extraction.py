# run_comparison_extraction.py
"""
【最終版v4】スクリーンショット戦略を実行するスクリプト。
pygetwindowでブラウザを確実に最大化し、安定性を確保する。
"""
import asyncio
import datetime
import json
import os
import sys
from pathlib import Path
import re
import time
import pygetwindow as gw

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

    from screenshot_taker import ScreenshotTaker
    from spec_extractor import SpecExtractor
    from gemini_generator import GeminiGenerator

    # --- 実行パラメータ ---
    TARGET_CATEGORY_URL = "https://kakaku.com/kaden/fan/"
    TARGET_CATEGORY_NAME = "扇風機"
    SCREENSHOT_PREFIX = "comparison"
    # --------------------

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)
        
        # ★★★ pygetwindowによる確実な最大化 ★★★
        try:
            # ブラウザウィンドウが表示されるのを少し待つ
            await asyncio.sleep(2)
            # ウィンドウタイトルに "Chromium" が含まれるウィンドウを探す
            window = gw.getWindowsWithTitle('Chromium')[0]
            if window:
                window.maximize()
                print("[INFO] ブラウザウィンドウを最大化しました。")
            else:
                print("[WARN] ブラウザウィンドウが見つかりませんでした。")
        except Exception as e:
            print(f"[WARN] ウィンドウの最大化に失敗しました: {e}")

        try:
            taker = ScreenshotTaker(browser)
            screenshot_paths = await taker.take_all_comparison_screenshots(
                category_top_url=TARGET_CATEGORY_URL,
                output_prefix=SCREENSHOT_PREFIX
            )

            if not screenshot_paths:
                print("\n[処理中断] スクリーンショットが1枚も撮影できなかったため、処理を中断します。")
                return

            gemini = GeminiGenerator()
            extractor = SpecExtractor(gemini)
            final_json_string = extractor.extract_from_images(screenshot_paths)

            print("\n[3/3] 統合された抽出結果をファイルに保存します...")
            output_dir = Path("product_databases")
            output_dir.mkdir(exist_ok=True)
            timestamp = datetime.datetime.now().strftime("%Y-%m-%d_%H%M%S")
            safe_category_name = "".join(c for c in TARGET_CATEGORY_NAME if c.isalnum()).rstrip()
            output_filename = f"{timestamp}_{safe_category_name}_screenshot_db.json"
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

        finally:
            await browser.close()


if __name__ == "__main__":
    if sys.platform == "win32":
        sys.stdout.reconfigure(encoding='utf-8')
        sys.stderr.reconfigure(encoding='utf-8')
    
    asyncio.run(main())