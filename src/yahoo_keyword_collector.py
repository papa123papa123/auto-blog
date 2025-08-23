# src/yahoo_keyword_collector.py
# Yahoo検索ベースのキーワード収集システム（SERP API不要）

import asyncio
import aiohttp
import re
from pathlib import Path
from typing import List, Set, Dict, Optional
from urllib.parse import quote, urlencode
import time
import random
import logging

# ロガーの設定
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

class YahooKeywordCollector:
    """Yahoo検索から関連キーワードを収集するクラス"""
    
    def __init__(self, output_dir: str = "yahoo_keywords", delay_range: tuple = (1, 3)):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(exist_ok=True)
        
        # 遅延設定（レート制限回避）
        self.delay_range = delay_range
        
        # Yahoo検索のベースURL
        self.base_url = "https://search.yahoo.co.jp/search"
        
        # 戦略的拡張ワード（既存のKeywordHunterと同じ）
        self.strategic_expansion_words = [
            "おすすめ", "比較", "ランキング", "選び方",  # 購入意図
            "やり方", "使い方",                          # 方法・実行意図
            "デメリット", "注意点", "口コミ",            # 懸念・比較検討意図
            "とは"                                     # 知識意図
        ]
        
        # ユーザーエージェントのリスト（ローテーション用）
        self.user_agents = [
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0",
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.1 Safari/605.1.15"
        ]
        
        print("[OK] YahooKeywordCollectorの初期化に成功しました。")
    
    async def collect_all_keywords(self, main_keyword: str) -> List[str]:
        """メインキーワードから関連キーワードを網羅的に収集"""
        print(f"\n=== 「{main_keyword}」の関連キーワード収集開始 ===")
        
        all_keywords: Set[str] = set()
        
        # 1. メインキーワードの基本検索から関連キーワードを収集
        print("\n[ステップ1/3] メインキーワードの基本検索から関連キーワードを収集中...")
        basic_keywords = await self._collect_basic_keywords(main_keyword)
        all_keywords.update(basic_keywords)
        print(f"  -> {len(basic_keywords)}個の基本キーワードを収集しました。")
        
        # 2. 戦略的キーワード拡張（並列実行）
        print("\n[ステップ2/3] 戦略的キーワード拡張を並列実行中...")
        strategic_keywords = await self._collect_strategic_keywords(main_keyword)
        all_keywords.update(strategic_keywords)
        print(f"  -> {len(strategic_keywords)}個の戦略的キーワードを収集しました。")
        
        # 3. 関連検索の深掘り
        print("\n[ステップ3/3] 関連検索の深掘りを実行中...")
        deep_keywords = await self._collect_deep_keywords(main_keyword, list(all_keywords)[:10])
        all_keywords.update(deep_keywords)
        print(f"  -> {len(deep_keywords)}個の深掘りキーワードを収集しました。")
        
        # 結果を整理
        final_keywords = sorted(list(all_keywords))
        print(f"\n✅ キーワード収集完了！ 合計 {len(final_keywords)}個のユニークキーワードを収集しました。")
        
        return final_keywords
    
    async def _collect_basic_keywords(self, main_keyword: str) -> List[str]:
        """メインキーワードの基本検索から関連キーワードを収集"""
        keywords = set()
        
        # 基本検索を実行
        html_content = await self._fetch_yahoo_search(main_keyword)
        if html_content:
            # 関連キーワードを抽出
            related_keywords = self._extract_related_keywords(html_content)
            keywords.update(related_keywords)
            
            # 検索結果のタイトルからもキーワードを抽出
            title_keywords = self._extract_title_keywords(html_content)
            keywords.update(title_keywords)
        
        return list(keywords)
    
    async def _collect_strategic_keywords(self, main_keyword: str) -> List[str]:
        """戦略的キーワード拡張を並列実行"""
        keywords = set()
        
        # 並列実行用のタスクリスト
        tasks = []
        for word in self.strategic_expansion_words:
            query = f"{main_keyword} {word}"
            task = self._fetch_and_extract_keywords(query)
            tasks.append(task)
        
        # 並列実行
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # 結果を統合
        for result in results:
            if isinstance(result, list):
                keywords.update(result)
            else:
                print(f"  -> [WARN] 戦略的拡張でエラーが発生: {result}")
        
        return list(keywords)
    
    async def _collect_deep_keywords(self, main_keyword: str, seed_keywords: List[str]) -> List[str]:
        """収集されたキーワードからさらに深掘り"""
        keywords = set()
        
        # 上位10個のキーワードから深掘り
        for seed_keyword in seed_keywords[:10]:
            html_content = await self._fetch_yahoo_search(seed_keyword)
            if html_content:
                related_keywords = self._extract_related_keywords(html_content)
                keywords.update(related_keywords)
            
            # レート制限回避
            await asyncio.sleep(random.uniform(*self.delay_range))
        
        return list(keywords)
    
    async def _fetch_and_extract_keywords(self, query: str) -> List[str]:
        """検索を実行してキーワードを抽出"""
        html_content = await self._fetch_yahoo_search(query)
        if html_content:
            return self._extract_related_keywords(html_content)
        return []
    
    async def _fetch_yahoo_search(self, query: str) -> Optional[str]:
        """Yahoo検索を実行してHTMLを取得"""
        try:
            # ランダムなユーザーエージェントを選択
            user_agent = random.choice(self.user_agents)
            
            # 検索パラメータ
            params = {
                'p': query,
                'ei': 'UTF-8',
                'fr': 'top_ga1_sa'
            }
            
            # ヘッダー
            headers = {
                'User-Agent': user_agent,
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
                'Accept-Language': 'ja,en-US;q=0.7,en;q=0.3',
                'Accept-Encoding': 'gzip, deflate',
                'DNT': '1',
                'Connection': 'keep-alive',
                'Upgrade-Insecure-Requests': '1',
            }
            
            # リクエスト実行
            async with aiohttp.ClientSession() as session:
                url = f"{self.base_url}?{urlencode(params)}"
                async with session.get(url, headers=headers) as response:
                    if response.status == 200:
                        content = await response.text()
                        
                        # HTMLを保存（デバッグ用）
                        safe_filename = self._make_safe_filename(query)
                        file_path = self.output_dir / f"{safe_filename}.html"
                        with open(file_path, 'w', encoding='utf-8') as f:
                            f.write(content)
                        
                        return content
                    else:
                        print(f"  -> [WARN] 検索クエリ「{query}」でHTTP {response.status}が返されました。")
                        return None
                        
        except Exception as e:
            print(f"  -> [ERROR] 検索クエリ「{query}」の実行中にエラーが発生: {e}")
            return None
    
    def _extract_related_keywords(self, html_content: str) -> List[str]:
        """HTMLから関連キーワードを抽出"""
        keywords = set()
        
        # パターン1: 「関連する検索」セクション
        related_patterns = [
            r'<a[^>]*class="[^"]*related[^"]*"[^>]*>([^<]+)</a>',
            r'<span[^>]*class="[^"]*related[^"]*"[^>]*>([^<]+)</span>',
            r'関連する検索[^>]*>([^<]+)</a>',
            r'関連検索[^>]*>([^<]+)</a>'
        ]
        
        for pattern in related_patterns:
            matches = re.findall(pattern, html_content, re.IGNORECASE)
            for match in matches:
                # HTMLタグを除去
                clean_text = re.sub(r'<[^>]+>', '', match).strip()
                if clean_text and len(clean_text) > 2:
                    keywords.add(clean_text)
        
        # パターン2: 検索結果の下部に表示される関連キーワード
        bottom_patterns = [
            r'<div[^>]*class="[^"]*bottom[^"]*"[^>]*>([^<]+)</div>',
            r'<ul[^>]*class="[^"]*related[^"]*"[^>]*>(.*?)</ul>',
            r'<li[^>]*class="[^"]*related[^"]*"[^>]*>([^<]+)</li>'
        ]
        
        for pattern in bottom_patterns:
            matches = re.findall(pattern, html_content, re.IGNORECASE | re.DOTALL)
            for match in matches:
                # HTMLタグを除去
                clean_text = re.sub(r'<[^>]+>', '', match).strip()
                if clean_text and len(clean_text) > 2:
                    keywords.add(clean_text)
        
        return list(keywords)
    
    def _extract_title_keywords(self, html_content: str) -> List[str]:
        """検索結果のタイトルからキーワードを抽出"""
        keywords = set()
        
        # 検索結果のタイトルを抽出
        title_pattern = r'<h3[^>]*>([^<]+)</h3>'
        titles = re.findall(title_pattern, html_content)
        
        for title in titles:
            # HTMLタグを除去
            clean_title = re.sub(r'<[^>]+>', '', title).strip()
            if clean_title:
                # タイトルから重要な単語を抽出
                words = re.findall(r'[\u3040-\u309F\u30A0-\u30FF\u4E00-\u9FAF]+', clean_title)
                for word in words:
                    if len(word) > 1:  # 1文字の単語は除外
                        keywords.add(word)
        
        return list(keywords)
    
    def _make_safe_filename(self, text: str) -> str:
        """テキストを安全なファイル名に変換"""
        # 危険な文字を除去・置換
        safe_text = re.sub(r'[<>:"/\\|?*]', '_', text)
        safe_text = re.sub(r'\s+', '_', safe_text)
        safe_text = safe_text[:100]  # 長すぎる場合は切り詰め
        return safe_text
    
    def clear_cache(self, older_than_hours: int = 24):
        """古いHTMLファイルを削除"""
        current_time = time.time()
        cutoff_time = current_time - (older_than_hours * 3600)
        
        deleted_count = 0
        for file_path in self.output_dir.glob("*.html"):
            if file_path.stat().st_mtime < cutoff_time:
                file_path.unlink()
                deleted_count += 1
        
        if deleted_count > 0:
            print(f"[INFO] {deleted_count}件の古いHTMLファイルを削除しました。")

# テスト用コード
async def test_keyword_collector():
    """キーワード収集のテスト"""
    print("=== Yahoo検索ベースキーワード収集テスト ===")
    
    collector = YahooKeywordCollector()
    
    # テスト用キーワード
    test_keywords = [
        "プログラミング学習",
        "料理 作り方",
        "健康管理"
    ]
    
    for keyword in test_keywords:
        print(f"\n{'='*50}")
        print(f"テストキーワード: {keyword}")
        print(f"{'='*50}")
        
        # キーワード収集を実行
        collected_keywords = await collector.collect_all_keywords(keyword)
        
        print(f"\n収集されたキーワード（上位20件）:")
        for i, kw in enumerate(collected_keywords[:20], 1):
            print(f"  {i:2d}. {kw}")
        
        if len(collected_keywords) > 20:
            print(f"  ... 他 {len(collected_keywords) - 20}件")
        
        print(f"\n合計: {len(collected_keywords)}件")
        
        # レート制限回避
        await asyncio.sleep(2)
    
    # キャッシュクリーンアップ
    collector.clear_cache()

if __name__ == "__main__":
    asyncio.run(test_keyword_collector())
