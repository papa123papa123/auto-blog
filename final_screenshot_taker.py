# final_screenshot_taker.py
"""
【最終版v2】「スクロールして4枚撮る」戦略で、比較表のスクリーンショットを撮影するスクリプト。
"""
import asyncio
import os
import sys
from pathlib import Path
from playwright.async_api import async_playwright

# --- モジュール検索パスを追加 ---
sys.path.append(str(Path(__file__).resolve().parent.parent))
# --------------------------

async def take_screenshots(category_url: str, category_name: str):
    """メインの実行関数"""
    print("\n--- スクリーンショット撮影を開始します ---")
    
    output_dir = Path(f"screenshots_{category_name}")
    output_dir.mkdir(exist_ok=True)
    print(f"[INFO] スクリーンショットは '{output_dir}' フォルダに保存されます。")

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False, args=["--start-maximized"])
        context = await browser.new_context(no_viewport=True)
        page = await context.new_page()

        try:
            await page.goto(category_url, timeout=60000, wait_until="domcontentloaded")
            await page.wait_for_timeout(3000)
            
            all_links = await page.evaluate("() => Array.from(document.querySelectorAll('a')).filter(a => a.textContent.includes('上位製品をまとめて比較する')).map(a => ({href: a.href, text: a.closest('div, section')?.querySelector('h2, h3')?.textContent.trim() || ''}))")
            await page.close()

            if not all_links:
                print("[NG] 「上位製品をまとめて比較する」リンクが見つかりませんでした。")
                return

            print(f"[INFO] {len(all_links)}個の比較表を発見しました。")

            for i, link_info in enumerate(all_links):
                group_name = "".join(c for c in link_info['text'] if c.isalnum()).rstrip() or f"group{i+1}"
                print(f"\n--- [{i+1}/{len(all_links)}] '{group_name}' の比較表を処理します ---")
                
                compare_page = await context.new_page()
                try:
                    await compare_page.goto(link_info['href'], timeout=60000, wait_until="networkidle")
                    
                    # ★★★ 新しいタブを、確実にアクティブにする ★★★
                    await compare_page.bring_to_front()
                    
                    # 撮影シーケンス
                    for j, (action, scroll_x, scroll_y) in enumerate([
                        ("右上", 0, 0), 
                        ("右下", 0, 9999), 
                        ("左下", -9999, 9999),
                        ("左上", -9999, 0)
                    ]):
                        await compare_page.mouse.wheel(scroll_x, scroll_y)
                        await asyncio.sleep(1)
                        filename = f"{category_name}_{group_name}_{j+1}_{action}.png"
                        path = output_dir / filename
                        await compare_page.screenshot(path=path)
                        print(f"  [OK] {path} を撮影しました。")
                finally:
                    await compare_page.close()
            
            print("\n[成功] すべてのスクリーンショット撮影が完了しました。")

        except Exception as e:
            print(f"[NG] 操作中にエラーが発生しました: {e}")
        finally:
            await browser.close()

if __name__ == "__main__":
    if sys.platform == "win32":
        sys.stdout.reconfigure(encoding='utf-8')
        sys.stderr.reconfigure(encoding='utf-8')
    
    asyncio.run(take_screenshots("https://kakaku.com/kaden/fan/", "扇風機"))