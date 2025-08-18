# src/kakaku_url_generator.py
"""
【最終版】価格.comのカテゴリページから製品IDを抽出し、
比較ページのURLを生成する、最もシンプルで確実なモジュール。
"""
import asyncio
import re
from playwright.async_api import async_playwright
from typing import List, Optional

class KakakuUrlGenerator:
    def __init__(self, headless: bool = True):
        self.headless = headless

    async def generate_comparison_url(self, category_top_url: str) -> Optional[str]:
        """
        カテゴリページから製品IDを抽出し、比較URLを生成する。
        """
        print(f"\n[1/2] 製品IDを抽出し、比較URLを生成します...")
        print(f"  -> カテゴリページにアクセス中: {category_top_url}")

        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=self.headless)
            page = await browser.new_page()
            try:
                await page.goto(category_top_url, timeout=60000, wait_until="domcontentloaded")
                html_content = await page.content()

                # HTMLからすべての製品ID (Kで始まり数字が続く) を正規表現で抽出
                product_ids = re.findall(r'K\d{11}', html_content)
                
                if not product_ids:
                    print("[NG] 製品IDが見つかりませんでした。")
                    return None

                # 重複を除外し、最大20件に絞る
                unique_ids = sorted(list(set(product_ids)), key=product_ids.index)
                target_ids = unique_ids[:20]
                
                print(f"  -> {len(target_ids)}件のユニークな製品IDを抽出しました。")

                # カテゴリIDをURLから抽出 (例: .../fan/ -> fan)
                category_match = re.search(r'/kaden/([^/]+)/', category_top_url)
                if not category_match:
                    print("[NG] URLからカテゴリIDを特定できませんでした。")
                    return None
                
                # 比較URLを組み立てる
                base_url = "https://kakaku.com/prdcompare/prdcompare.aspx"
                id_string = "_".join(target_ids)
                
                # カテゴリIDはHTML内から探す方が確実
                # <input type="hidden" name="CategoryCD" value="2152"> のような形式
                cat_id_match = re.search(r'name="CategoryCD" value="(\d+)"', html_content)
                if not cat_id_match:
                    print("[NG] HTML内からカテゴリIDが見つかりませんでした。")
                    return None
                
                category_id = cat_id_match.group(1)
                
                comparison_url = f"{base_url}?pd_cmpkey={id_string}&pd_ctg={category_id}"
                
                print(f"[OK] 比較ページのURLを生成しました。")
                return comparison_url

            except Exception as e:
                print(f"[NG] URL生成中にエラーが発生しました: {e}")
                return None
            finally:
                await browser.close()

if __name__ == '__main__':
    async def main_test():
        generator = KakakuUrlGenerator(headless=False)
        url = await generator.generate_comparison_url("https://kakaku.com/kaden/fan/")
        if url:
            print(f"\n生成されたURL: {url}")
        else:
            print("\nURLの生成に失敗しました。")
    
    asyncio.run(main_test())
