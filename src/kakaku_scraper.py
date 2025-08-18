# src/kakaku_scraper.py

import asyncio
from playwright.async_api import Browser
from playwright_stealth.stealth import Stealth
from typing import List, Dict, Optional

class KakakuScraper:
    """
    【最終版】起動済みのBrowserインスタンスを共有し、各タスクはページ（タブ）単位で完結する。
    """
    def __init__(self, browser: Browser):
        self.browser = browser
        self.user_agent = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36"
        self.stealth = Stealth()

    async def _get_new_stealth_page(self):
        page = await self.browser.new_page(user_agent=self.user_agent)
        page.on("dialog", lambda dialog: dialog.accept())
        await self.stealth.apply_stealth_async(page)
        return page

    async def find_ranking_page_url(self, category_top_url: str) -> Optional[str]:
        page = await self._get_new_stealth_page()
        try:
            await page.goto(category_top_url, timeout=60000, wait_until="domcontentloaded")
            link_locator = page.get_by_role("link", name="人気売れ筋ランキングをもっと見る")
            await link_locator.wait_for(state="visible", timeout=15000)
            href = await link_locator.get_attribute("href")
            return href if href.startswith('http') else f"https://kakaku.com{href}"
        finally:
            await page.close()

    async def get_top_products(self, ranking_page_url: str, num_products: int = 20) -> List[Dict[str, str]]:
        products = []
        page = await self._get_new_stealth_page()
        try:
            await page.goto(ranking_page_url, timeout=60000, wait_until="domcontentloaded")
            await page.locator(".rkgContents").wait_for(state="visible", timeout=15000)
            product_blocks = page.locator("div.rkgBox")
            count = await product_blocks.count()
            for i in range(min(num_products, count)):
                row = product_blocks.nth(i)
                maker = await row.locator("span.rkgBoxNameMaker").inner_text()
                product_name = await row.locator("span.rkgBoxNameItem").inner_text()
                detail_page_url = await row.locator("a.rkgBoxLink").get_attribute("href")
                if detail_page_url:
                    products.append({
                        "rank": i + 1, "maker": maker.strip(), "name": product_name.strip(),
                        "kakaku_detail_url": detail_page_url
                    })
            return products
        finally:
            await page.close()

    async def get_official_url(self, kakaku_detail_url: str) -> Optional[str]:
        page = await self._get_new_stealth_page()
        try:
            await page.goto(kakaku_detail_url, timeout=60000, wait_until="domcontentloaded")
            link_locator = page.get_by_role("link", name="メーカー製品情報ページ")
            await link_locator.wait_for(state="visible", timeout=10000)
            return await link_locator.get_attribute("href")
        except Exception:
            return None
        finally:
            await page.close()
