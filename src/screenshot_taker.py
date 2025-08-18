# src/screenshot_taker.py
"""
【最終版v5】価格.comのカテゴリページ内にある「上位製品をまとめて比較する」ボタンを
すべて探し出し、各比較ページのスクリーンショットをズームアウトして撮影するモジュール。
"""
import asyncio
from playwright.async_api import Browser
from playwright_stealth.stealth import Stealth
from typing import List

class ScreenshotTaker:
    def __init__(self, browser: Browser):
        self.browser = browser
        self.user_agent = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36"
        self.stealth = Stealth()

    async def take_all_comparison_screenshots(self, category_top_url: str, output_prefix: str = "comparison") -> List[str]:
        print(f"\n[1/2] 複数比較ページのスクリーンショット撮影を開始します...")
        screenshot_paths = []
        page = await self.browser.new_page(user_agent=self.user_agent)
        page.on("dialog", lambda dialog: dialog.accept())
        await self.stealth.apply_stealth_async(page)
        try:
            print(f"  -> カテゴリページにアクセス中: {category_top_url}")
            await page.goto(category_top_url, timeout=60000, wait_until="domcontentloaded")
            await page.wait_for_timeout(3000)

            print("  -> ページ全体をスクロールしてボタンを検出します...")
            await page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
            await asyncio.sleep(1)
            await page.evaluate("window.scrollTo(0, 0)")
            await asyncio.sleep(2)

            print("  -> 「上位製品をまとめて比較する」ボタンをテキストで検索中...")
            all_buttons = page.locator("text='上位製品をまとめて比較する'")
            button_count = await all_buttons.count()
            if button_count == 0:
                print("[NG] 比較ボタンが見つかりませんでした。")
                return []
            
            print(f"  -> {button_count}個の比較ボタンを発見しました。")

            for i in range(button_count):
                button = all_buttons.nth(i)
                await button.scroll_into_view_if_needed()
                
                try:
                    parent_text = await button.evaluate("(el) => el.closest('div, section')?.querySelector('h2, h3')?.textContent.trim() || 'group'")
                    safe_parent_text = "".join(c for c in (parent_text or f"group{i+1}") if c.isalnum()).rstrip() or f"group{i+1}"
                except Exception:
                    safe_parent_text = f"group{i+1}"

                print(f"\n  -> [{i+1}/{button_count}] '{safe_parent_text}' の比較表を処理中...")
                
                async with page.context.expect_page() as new_page_info:
                    await button.click()
                
                compare_page = await new_page_info.value
                
                # ★★★ 確実な待機処理 ★★★
                print("      -> 比較表の本体が表示されるのを待機します...")
                await compare_page.wait_for_selector("#compTbl", state="visible", timeout=30000)
                
                print("      -> ページを50%にズームアウトします...")
                await compare_page.evaluate("document.body.style.zoom = 0.5")
                await asyncio.sleep(2)

                output_path = f"{output_prefix}_{i+1}_{safe_parent_text}.png"
                await compare_page.screenshot(path=output_path, full_page=True)
                screenshot_paths.append(output_path)
                print(f"      [OK] スクリーンショットを '{output_path}' に保存しました。")
                
                await compare_page.close()
                await page.bring_to_front()

            print(f"\n[OK] 合計 {len(screenshot_paths)}枚のスクリーンショット撮影に成功しました。")
            
        except Exception as e:
            print(f"[NG] スクリーンショットの撮影中にエラーが発生しました: {e}")
        finally:
            await page.close()
            
        return screenshot_paths
