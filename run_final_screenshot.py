# run_final_screenshot.py
"""
【最終版v16】「URLを先に全部集める」戦略 + 「2枚セット撮影」戦略で、
最もシンプルかつ確実に実行するスクリプト。
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
    SCREENSHOT_DIR = Path("screenshots")
    SCREENSHOT_DIR.mkdir(exist_ok=True)
    # --------------------

    print("\n--- シンプルなスクリーンショット撮影を開始します ---")
    screenshot_paths = []
    comparison_links = []

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False, args=["--start-maximized"])
        context = await browser.new_context(no_viewport=True)
        page = await context.new_page()

        try:
            # 1. カテゴリページにアクセスし、比較ページのURLとグループ名をすべて取得
            print(f"[INFO] カテゴリページにアクセスし、全比較情報を抽出します: {TARGET_CATEGORY_URL}")
            await page.goto(TARGET_CATEGORY_URL, timeout=60000, wait_until="domcontentloaded")
            await page.wait_for_timeout(5000)
            
            all_links_info = await page.evaluate("""
                () => {
                    const info = [];
                    const elements = document.querySelectorAll("a");
                    for (const el of elements) {
                        if (el.textContent.includes('人気売れ筋ランキングをもっと見る')) {
                            const groupName = el.closest('div, section')?.querySelector('h2, h3')?.textContent.trim() || '';
                            info.push({ href: el.href, name: groupName });
                        }
                    }
                    return info;
                }
            """)
            if not all_links_info:
                print("[NG] 「人気売れ筋ランキングをもっと見る」リンクが見つかりませんでした。")
                return
            
            comparison_links = all_links_info
            print(f"[OK] {len(comparison_links)}個の比較情報の抽出が完了しました。")
            await page.close()

            # 2. 抽出した情報を元に、2枚セットでスクリーンショットを撮影
            for i, link_info in enumerate(comparison_links):
                group_name = "".join(c for c in link_info['name'] if c.isalnum()).rstrip() or f"group{i+1}"
                print(f"\n--- [{i+1}/{len(comparison_links)}] '{group_name}' の比較表を撮影します ---")
                
                compare_page = await context.new_page()
                try:
                    print(f"[INFO] ページにアクセス: {link_info['href']}")
                    await compare_page.goto(link_info['href'], timeout=60000, wait_until="networkidle")
                    await asyncio.sleep(3)
                    
                    path_top = SCREENSHOT_DIR / f"{TARGET_CATEGORY_NAME}_{group_name}_1_top.png"
                    await compare_page.screenshot(path=path_top)
                    print(f"  [OK] {path_top} を撮影しました。")

                    await compare_page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
                    await asyncio.sleep(2)
                    path_bottom = SCREENSHOT_DIR / f"{TARGET_CATEGORY_NAME}_{group_name}_2_bottom.png"
                    await compare_page.screenshot(path=path_bottom)
                    print(f"  [OK] {path_bottom} を撮影しました。")
                    
                    screenshot_paths.append([str(path_top), str(path_bottom)])

                finally:
                    await compare_page.close()

            print("\n[OK] すべてのスクリーンショット撮影が完了しました。")

        except Exception as e:
            print(f"[NG] 操作中にエラーが発生しました: {e}")
            return
        finally:
            await browser.close()

    # 3. AI処理
    if not screenshot_paths:
        return
        
    gemini = GeminiGenerator()
    extractor = SpecExtractor(gemini)
    all_extracted_texts = []

    print("\n--- AIによるテキスト抽出を開始します ---")
    for i, image_pair in enumerate(screenshot_paths):
        group_name = Path(image_pair[0]).stem.replace("_1_top", "")
        print(f"\n--- [{i+1}/{len(screenshot_paths)}] '{group_name}' の画像を処理します ---")
        extracted_text = extractor.extract_from_images(image_pair)
        all_extracted_texts.append(f"--- {group_name} ---\n\n{extracted_text}\n\n")

    # 4. 最終統合
    print("\n--- すべての抽出結果を単一ファイルに統合します ---")
    output_dir = Path("product_texts_final")
    output_dir.mkdir(exist_ok=True)
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    output_filename = f"【最終統合版】{TARGET_CATEGORY_NAME}_ランキング_{timestamp}.txt"
    output_filepath = output_dir / output_filename
    with open(output_filepath, "w", encoding="utf-8") as f:
        f.write("\n".join(all_extracted_texts))

    print(f"\n[★★★★★ 完 成 ★★★★★]")
    print(f"すべての処理が完了しました！ 最終成果物はこちらです！")
    print(f"-> {output_filepath}")


if __name__ == "__main__":
    if sys.platform == "win32":
        sys.stdout.reconfigure(encoding='utf-8')
        sys.stderr.reconfigure(encoding='utf-8')
    
    asyncio.run(main())