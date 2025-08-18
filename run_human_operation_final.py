# run_human_operation_final.py
"""
【最終版v8】お客様の最終設計に基づき、「人間と同じ操作」を正確に実行するスクリプト。
普段使いのGoogle Chromeを直接操作し、安定性を最大化する。
"""
import asyncio
import datetime
import json
import os
import sys
from pathlib import Path
import re
import pyautogui
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

    from spec_extractor import SpecExtractor
    from gemini_generator import GeminiGenerator

    # --- 実行パラメータ ---
    TARGET_CATEGORY_URL = "https://kakaku.com/kaden/fan/"
    TARGET_CATEGORY_NAME = "扇風機"
    SCREENSHOT_PREFIX = "comparison_final"
    # --------------------

    print("\n--- 「人間と同じ操作」を開始します ---")
    screenshot_paths = []

    async with async_playwright() as p:
        # ★★★ 普段使いのGoogle Chromeを、非シークレットモードで起動 ★★★
        browser = await p.chromium.launch(
            channel="chrome", # chrome, msedge, etc.
            headless=False
        )
        context = await browser.new_context(no_viewport=True)
        page = await context.new_page()
        # ★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★

        try:
            print("[INFO] ブラウザを最大化します...")
            await asyncio.sleep(2)
            # ★★★ ウィンドウタイトルを 'Google Chrome' に変更 ★★★
            window = gw.getWindowsWithTitle('Google Chrome')[0]
            if window:
                window.maximize()
            await asyncio.sleep(1)

            print(f"[INFO] カテゴリページにアクセスします: {TARGET_CATEGORY_URL}")
            await page.goto(TARGET_CATEGORY_URL, timeout=60000, wait_until="domcontentloaded")
            await page.wait_for_timeout(3000)
            
            print("[INFO] ページをスクロールして、すべてのボタンを探します...")
            await page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
            await asyncio.sleep(1)

            compare_buttons = page.locator("text='上位製品をまとめて比較する'")
            button_count = await compare_buttons.count()
            if button_count == 0:
                print("[NG] 「上位製品をまとめて比較する」ボタンが見つかりませんでした。")
                return
            print(f"[INFO] {button_count}個の「上位製品をまとめて比較する」ボタンを発見しました。")

            for i in range(button_count):
                print(f"\n--- [{i+1}/{button_count}] 個目の比較表を処理します ---")
                button = compare_buttons.nth(i)
                await button.scroll_into_view_if_needed()
                
                async with context.expect_page() as new_page_info:
                    await button.click()
                
                compare_page = await new_page_info.value
                print("[INFO] 新しいタブで比較ページを開きました。")
                
                print("[INFO] 比較表の本体が表示されるのを待機します...")
                await compare_page.wait_for_selector("#compTbl", state="visible", timeout=30000)
                await asyncio.sleep(2)
                
                print("[INFO] ブラウザウィンドウをアクティブにします...")
                window = gw.getWindowsWithTitle('Google Chrome')[0]
                if window:
                    window.activate()
                await asyncio.sleep(1)

                print("[INFO] キーボード操作で3回ズームアウトします (Ctrl + -)...")
                for _ in range(3):
                    pyautogui.hotkey('ctrl', '-')
                    await asyncio.sleep(0.5)
                await asyncio.sleep(2)

                output_path = f"{SCREENSHOT_PREFIX}_{i+1}.png"
                pyautogui.screenshot(output_path)
                screenshot_paths.append(output_path)
                print(f"[INFO] スクリーンショットを撮影しました: {output_path}")

                print("[INFO] タブを閉じて、元のページに戻ります。")
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

    # 8. 結果をファイルに保存
    print("\n--- 抽出結果をファイルに保存します ---")
    output_dir = Path("product_databases")
    output_dir.mkdir(exist_ok=True)
    timestamp = datetime.datetime.now().strftime("%Y-%m-%d_%H%M%S")
    safe_category_name = "".join(c for c in TARGET_CATEGORY_NAME if c.isalnum()).rstrip()
    output_filename = f"{timestamp}_{safe_category_name}_final_db.json"
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