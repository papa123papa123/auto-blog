# run_human_operation.py
"""
【最終版v4】「人間と同じ操作」で、比較ページのスクリーンショットを撮影し、AIで解析するスクリプト。
Playwrightの機能で、ブラウザを確実に最大化する。
"""
import asyncio
import datetime
import json
import os
import sys
from pathlib import Path
import re
import pyautogui

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
    SCREENSHOT_PATH = "human_operation_screenshot.png"
    # --------------------

    print("\n--- 「人間と同じ操作」を開始します ---")

    async with async_playwright() as p:
        # ★★★ 確実な最大化 ★★★
        browser = await p.chromium.launch(
            headless=False,
            args=["--start-maximized"]
        )
        context = await browser.new_context(no_viewport=True)
        page = await context.new_page()
        # ★★★★★★★★★★★★★★★

        try:
            print(f"[INFO] カテゴリページにアクセスします: {TARGET_CATEGORY_URL}")
            await page.goto(TARGET_CATEGORY_URL, timeout=60000, wait_until="domcontentloaded")
            await asyncio.sleep(3)

            print("[INFO] ページをスクロールしてボタンを探します...")
            await page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
            await asyncio.sleep(1)
            
            print("[INFO] 「上位製品をまとめて比較する」ボタンをクリックします...")
            compare_button = page.locator("text='上位製品をまとめて比較する'").first
            
            # 比較ページが新しいタブで開くのを待つ
            async with context.expect_page() as new_page_info:
                await compare_button.click()
            
            compare_page = await new_page_info.value
            
            print("[INFO] 比較ページが表示されるのを待ちます...")
            await compare_page.wait_for_load_state("domcontentloaded", timeout=60000)
            await asyncio.sleep(5)

            print("[INFO] キーボード操作で3回ズームアウトします (Ctrl + -)...")
            for _ in range(3):
                pyautogui.hotkey('ctrl', '-')
                await asyncio.sleep(0.5)
            
            await asyncio.sleep(2)

            print(f"[INFO] スクリーンショットを撮影します: {SCREENSHOT_PATH}")
            await compare_page.screenshot(path=SCREENSHOT_PATH, full_page=True)
            
            print("[OK] 人間と同じ操作が完了しました。")

        except Exception as e:
            print(f"[NG] 操作中にエラーが発生しました: {e}")
            return
        finally:
            await browser.close()

    # AI処理とファイル保存 (変更なし)
    gemini = GeminiGenerator()
    extractor = SpecExtractor(gemini)
    final_json_string = extractor.extract_from_images([SCREENSHOT_PATH])

    print("\n--- 抽出結果をファイルに保存します ---")
    output_dir = Path("product_databases")
    output_dir.mkdir(exist_ok=True)
    timestamp = datetime.datetime.now().strftime("%Y-%m-%d_%H%M%S")
    safe_category_name = "".join(c for c in TARGET_CATEGORY_NAME if c.isalnum()).rstrip()
    output_filename = f"{timestamp}_{safe_category_name}_human_op_db.json"
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