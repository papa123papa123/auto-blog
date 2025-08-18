# src/flows/product_database_flow.py

import asyncio
import datetime
import json
import re
from pathlib import Path
from typing import Dict, List

from bs4 import BeautifulSoup
from playwright.async_api import Browser
from tqdm.asyncio import tqdm

from src.gemini_generator import GeminiGenerator
from src.kakaku_scraper import KakakuScraper
from src.serp_analyzer import SerpAnalyzer
from playwright_stealth.stealth import Stealth


class ProductDatabaseFlow:
    """
    【最終版】起動済みのBrowserインスタンスを共有し、責務を明確化したフロー。
    """
    def __init__(self, gemini_generator: GeminiGenerator, serp_analyzer: SerpAnalyzer):
        self.gemini_generator = gemini_generator
        self.serp_analyzer = serp_analyzer
        self.stealth = Stealth()

    async def _get_spec_html(self, browser: Browser, url: str) -> tuple[str, str]:
        page = None
        try:
            page = await browser.new_page(user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36")
            page.on("dialog", lambda dialog: dialog.accept())
            await self.stealth.apply_stealth_async(page)
            await page.goto(url, timeout=60000, wait_until="domcontentloaded")
            
            # AIコール#1: スペック部分のHTMLを抽出
            html_content = await page.content()
            prompt1 = f"""以下のHTMLソースコードの中から、製品のスペック（仕様）が記載されている部分のHTMLタグを抜き出してください。\n\n# HTML\n{html_content}\n\n# スペック部分のHTML"""
            spec_html = self.gemini_generator.generate(prompt1, timeout=120)
            
            return "OK", spec_html
        except Exception as e:
            return "エラー", f"Playwrightエラー: {e}"
        finally:
            if page: await page.close()

    async def build_database_from_category(self, browser: Browser, category_top_url: str, category_name: str, num_products: int):
        print(f"\n--- 製品データベース構築フロー開始 [{category_name}] ---")
        kakaku_scraper = KakakuScraper(browser)

        # STEP 1: 価格.comから製品情報と公式サイトURL候補を取得
        ranking_url = await kakaku_scraper.find_ranking_page_url(category_top_url)
        if not ranking_url: return None
        products = await kakaku_scraper.get_top_products(ranking_url, num_products=num_products)
        if not products: return None
        
        tasks = [kakaku_scraper.get_official_url(p["kakaku_detail_url"]) for p in products]
        results = await tqdm.gather(*tasks, desc="[1/3] 公式サイトURL取得", unit="件", ascii=True, ncols=80)
        for p, res in zip(products, results):
            p["official_url"] = res

        # STEP 2: AIによるスペック情報抽出
        final_database = []
        for product in tqdm(products, desc="[2/3] AIスペック抽出 ", unit="件", ascii=True, ncols=80):
            product_data = {
                "rank": product["rank"], "maker": product["maker"], "name": product["name"],
                "official_url": product["official_url"], "specs": None, "error": None
            }
            
            target_url = product["official_url"]
            if not target_url:
                product_data["error"] = "価格.comに公式サイトURLの記載なし"
                final_database.append(product_data)
                continue

            status, spec_html = await self._get_spec_html(browser, target_url)
            if status == "エラー":
                product_data["error"] = spec_html
                final_database.append(product_data)
                continue

            soup = BeautifulSoup(spec_html, 'html.parser')
            spec_text = soup.get_text(separator='\n', strip=True)
            if not spec_text:
                product_data["error"] = "スペックHTMLからテキスト抽出失敗"
                final_database.append(product_data)
                continue

            # AIコール#2: テキストをJSONへ整形
            prompt2 = f"""以下のスペック情報テキストを解析し、キー・バリュー形式のJSONオブジェクトとして出力してください。\n\n# テキスト\n{spec_text}\n\n# JSON"""
            response_text = self.gemini_generator.generate(prompt2, timeout=120)
            
            try:
                json_match = re.search(r'```json\s*(\{.*?\})\s*```', response_text, re.DOTALL)
                json_str = json_match.group(1) if json_match else response_text
                product_data["specs"] = json.loads(json_str)
            except json.JSONDecodeError:
                product_data["error"] = "AI応答のJSON解析失敗"
            final_database.append(product_data)

        # STEP 3: ファイル保存
        print("\n[3/3] データベースをファイルに保存中...")
        output_dir = Path("product_databases")
        output_dir.mkdir(exist_ok=True)
        timestamp = datetime.datetime.now().strftime("%Y-%m-%d_%H%M%S")
        safe_category_name = "".join(c for c in category_name if c.isalnum()).rstrip()
        output_filename = f"{timestamp}_{safe_category_name}_database.json"
        output_filepath = output_dir / output_filename
        with open(output_filepath, "w", encoding="utf-8") as f:
            json.dump(final_database, f, indent=2, ensure_ascii=False)
        print(f"\n[成功] データベース構築完了！ -> {output_filepath}")
        
        return str(output_filepath)
