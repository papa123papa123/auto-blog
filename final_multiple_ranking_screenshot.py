# final_multiple_ranking_screenshot.py
"""
【最終版v2】「複数の人気売れ筋ランキング」を、それぞれ「スクロール前」「スクロール後」の2枚ずつ撮影する、最後のスクリプト。
"""
import asyncio
import os
import sys
from pathlib import Path
from playwright.async_api import async_playwright

# --- モジュール検索パスを追加 ---
sys.path.append(str(Path(__file__).resolve().parent.parent))
# --------------------------

async def take_ranking_screenshots(category_url: str, category_name: str):
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
            
            # ★★★ 先に、すべてのボタンのURLと名前を取得する ★★★
            all_buttons_info = await page.evaluate("""
                () => {
                    const info = [];
                    const elements = document.querySelectorAll("a:has-text('人気売れ筋ランキングをもっと見る')");
                    for (const el of elements) {
                        const groupName = el.closest('div, section')?.querySelector('h2, h3')?.textContent.trim() || '';
                        info.push({ href: el.href, name: groupName });
                    }
                    return info;
                }
            """)

            if not all_buttons_info:
                print("[NG] 「人気売れ筋ランキングをもっと見る」ボタンが見つかりませんでした。")
                return

            print(f"[INFO] {len(all_buttons_info)}個のランキングを発見しました。")
            await page.close()

            for i, button_info in enumerate(all_buttons_info):
                safe_group_name = "".join(c for c in button_info['name'] if c.isalnum()).rstrip() or f"group{i+1}"
                print(f"\n--- [{i+1}/{len(all_buttons_info)}] '{safe_group_name}' のランキングを処理します ---")
                
                ranking_page = await context.new_page()
                try:
                    # ★★★ URLに直接アクセス ★★★
                    await ranking_page.goto(button_info['href'], timeout=60000, wait_until="domcontentloaded")
                    await ranking_page.bring_to_front()
                    await ranking_page.wait_for_timeout(3000) # 描画安定化
                    
                    # 撮影#1 (上部)
                    filename_top = f"{category_name}_{safe_group_name}_1_top.png"
                    path_top = output_dir / filename_top
                    await ranking_page.screenshot(path=path_top)
                    print(f"  [OK] {path_top} を撮影しました。")

                    # 撮影#2 (下部)
                    await ranking_page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
                    await asyncio.sleep(1)
                    filename_bottom = f"{category_name}_{safe_group_name}_2_bottom.png"
                    path_bottom = output_dir / filename_bottom
                    await ranking_page.screenshot(path=path_bottom)
                    print(f"  [OK] {path_bottom} を撮影しました。")

                finally:
                    await ranking_page.close()

            print("\n[成功] すべてのスクリーンショット撮影が完了しました。")

        except Exception as e:
            print(f"[NG] 操作中にエラーが発生しました: {e}")
        finally:
            await browser.close()

if __name__ == "__main__":
    if sys.platform == "win32":
        sys.stdout.reconfigure(encoding='utf-8')
        sys.stderr.reconfigure(encoding='utf-8')
    
    asyncio.run(take_ranking_screenshots("https://kakaku.com/kaden/fan/", "扇風機"))