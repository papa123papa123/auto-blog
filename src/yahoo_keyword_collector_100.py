# src/yahoo_keyword_collector_100.py
# Yahoo検索ベースのキーワード収集システム（高速100個版・SERP API不要）

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

class YahooKeywordCollector100:
    """Yahoo検索から高速で100個のキーワードを収集するクラス"""
    
    def __init__(self, output_dir: str = "yahoo_keywords_100", delay_range: tuple = (0.2, 0.5)):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(exist_ok=True)
        
        # 遅延設定（超高速化）
        self.delay_range = delay_range
        
        # Yahoo検索のベースURL
        self.base_url = "https://search.yahoo.co.jp/search"
        
        # ユーザーエージェントのリスト（ローテーション用）
        self.user_agents = [
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0",
        ]
        
        print("[OK] YahooKeywordCollector100の初期化に成功しました。（高速100個版）")
    
    async def collect_all_keywords(self, main_keyword: str) -> List[str]:
        """メインキーワードから高速で100個のキーワードを収集"""
        start_time = time.time()
        print(f"\n=== 「{main_keyword}」の高速100個キーワード収集開始 ===")
        
        all_keywords: Set[str] = set()
        
        # 1. メインキーワードの基本検索から関連キーワードを収集
        print("\n[ステップ1/4] メインキーワードの基本検索から関連キーワードを収集中...")
        basic_keywords = await self._collect_basic_keywords(main_keyword)
        all_keywords.update(basic_keywords)
        print(f"  -> {len(basic_keywords)}個の基本キーワードを収集しました。")
        
        # 2. 自然サジェストキーワードの収集（戦略的拡張ワード不使用）
        print("\n[ステップ2/4] 自然サジェストキーワードを収集中...")
        natural_keywords = await self._collect_natural_suggestions(main_keyword)
        all_keywords.update(natural_keywords)
        print(f"  -> {len(natural_keywords)}個の自然サジェストキーワードを収集しました。")
        
        # 3. 複数ページの検索結果を並列解析
        print("\n[ステップ3/4] 複数ページの検索結果を並列解析中...")
        multi_page_keywords = await self._collect_multi_page_keywords(main_keyword)
        all_keywords.update(multi_page_keywords)
        print(f"  -> {len(multi_page_keywords)}個の複数ページキーワードを収集しました。")
        
        # 4. 関連検索の深掘り（大幅拡張・並列実行）
        print("\n[ステップ4/4] 関連検索の深掘りを大幅拡張・並列実行中...")
        deep_keywords = await self._collect_deep_keywords_extended(main_keyword, list(all_keywords)[:15])
        all_keywords.update(deep_keywords)
        print(f"  -> {len(deep_keywords)}個の深掘りキーワードを収集しました。")
        
        # 結果を整理
        final_keywords = sorted(list(all_keywords))
        elapsed_time = time.time() - start_time
        
        print(f"\n✅ キーワード収集完了！ 合計 {len(final_keywords)}個のユニークキーワードを収集しました。")
        print(f"⏱️  処理時間: {elapsed_time:.1f}秒")
        
        # 100個目標の達成状況
        if len(final_keywords) >= 100:
            print(f"🎯 目標達成！ 100個以上のキーワードを収集しました。")
        else:
            print(f"📊 目標まであと {100 - len(final_keywords)}個")
        
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
            
            # 検索結果の説明文からもキーワードを抽出
            description_keywords = self._extract_description_keywords(html_content)
            keywords.update(description_keywords)
            
            # 検索結果のURLからもキーワードを抽出
            url_keywords = self._extract_url_keywords(html_content)
            keywords.update(url_keywords)
        
        return list(keywords)
    
    async def _collect_natural_suggestions(self, main_keyword: str) -> List[str]:
        """自然なサジェストキーワードを収集（戦略的拡張ワード不使用）"""
        keywords = set()
        
        # メインキーワードの検索結果から自然に出てくる関連キーワードを抽出
        html_content = await self._fetch_yahoo_search(main_keyword)
        if html_content:
            # より詳細なキーワード抽出
            natural_keywords = self._extract_natural_suggestions(html_content)
            keywords.update(natural_keywords)
            
            # 検索結果の下部に表示される「関連する検索」セクション
            bottom_suggestions = self._extract_bottom_suggestions(html_content)
            keywords.update(bottom_suggestions)
            
            # 検索結果の右側に表示される関連キーワード
            right_suggestions = self._extract_right_suggestions(html_content)
            keywords.update(right_suggestions)
            
            # 検索結果の上部に表示される関連キーワード
            top_suggestions = self._extract_top_suggestions(html_content)
            keywords.update(top_suggestions)
        
        return list(keywords)
    
    async def _collect_multi_page_keywords(self, main_keyword: str) -> List[str]:
        """複数ページの検索結果を並列解析してキーワードを収集"""
        keywords = set()
        
        # 1-3ページ目を並列実行
        tasks = []
        for page in range(1, 4):
            task = self._fetch_and_extract_page_keywords(main_keyword, page)
            tasks.append(task)
        
        # 並列実行
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # 結果を統合
        for result in results:
            if isinstance(result, list):
                keywords.update(result)
            else:
                print(f"  -> [WARN] 複数ページ解析でエラーが発生: {result}")
        
        return list(keywords)
    
    async def _fetch_and_extract_page_keywords(self, main_keyword: str, page: int) -> List[str]:
        """指定ページの検索結果からキーワードを抽出"""
        keywords = set()
        
        # ページ指定の検索を実行
        html_content = await self._fetch_yahoo_search_page(main_keyword, page)
        if html_content:
            # タイトルからキーワードを抽出
            title_keywords = self._extract_title_keywords(html_content)
            keywords.update(title_keywords)
            
            # 説明文からキーワードを抽出
            description_keywords = self._extract_description_keywords(html_content)
            keywords.update(description_keywords)
            
            # URLからキーワードを抽出
            url_keywords = self._extract_url_keywords(html_content)
            keywords.update(url_keywords)
        
        return list(keywords)
    
    async def _collect_deep_keywords_extended(self, main_keyword: str, seed_keywords: List[str]) -> List[str]:
        """収集されたキーワードから深掘り（大幅拡張・並列実行）"""
        keywords = set()
        
        # 上位15個のキーワードから深掘り（8個から拡張）
        tasks = []
        for seed_keyword in seed_keywords[:15]:
            task = self._fetch_and_extract_deep_keywords(seed_keyword)
            tasks.append(task)
        
        # 並列実行
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # 結果を統合
        for result in results:
            if isinstance(result, list):
                keywords.update(result)
            else:
                print(f"  -> [WARN] 深掘りでエラーが発生: {result}")
        
        return list(keywords)
    
    async def _fetch_and_extract_deep_keywords(self, seed_keyword: str) -> List[str]:
        """シードキーワードから深掘りキーワードを取得"""
        html_content = await self._fetch_yahoo_search(seed_keyword)
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
    
    async def _fetch_yahoo_search_page(self, query: str, page: int) -> Optional[str]:
        """指定ページのYahoo検索を実行してHTMLを取得"""
        try:
            # ランダムなユーザーエージェントを選択
            user_agent = random.choice(self.user_agents)
            
            # 検索パラメータ（ページ指定）
            params = {
                'p': query,
                'ei': 'UTF-8',
                'fr': 'top_ga1_sa',
                'b': (page - 1) * 10 + 1  # ページ番号を計算
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
                        safe_filename = self._make_safe_filename(f"{query}_page{page}")
                        file_path = self.output_dir / f"{safe_filename}.html"
                        with open(file_path, 'w', encoding='utf-8') as f:
                            f.write(content)
                        
                        return content
                    else:
                        print(f"  -> [WARN] ページ{page}の検索クエリ「{query}」でHTTP {response.status}が返されました。")
                        return None
                        
        except Exception as e:
            print(f"  -> [ERROR] ページ{page}の検索クエリ「{query}」の実行中にエラーが発生: {e}")
            return None
    
    def _extract_related_keywords(self, html_content: str) -> List[str]:
        """HTMLから関連キーワードを抽出（基本版）"""
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
                clean_text = re.sub(r'<[^>]+>', '', match).strip()
                if clean_text and len(clean_text) > 2:
                    keywords.add(clean_text)
        
        return list(keywords)
    
    def _extract_natural_suggestions(self, html_content: str) -> List[str]:
        """自然なサジェストキーワードを抽出"""
        keywords = set()
        
        # 検索結果の説明文からキーワードを抽出
        description_patterns = [
            r'<p[^>]*class="[^"]*description[^"]*"[^>]*>([^<]+)</p>',
            r'<div[^>]*class="[^"]*description[^"]*"[^>]*>([^<]+)</div>',
            r'<span[^>]*class="[^"]*description[^"]*"[^>]*>([^<]+)</span>'
        ]
        
        for pattern in description_patterns:
            matches = re.findall(pattern, html_content, re.IGNORECASE)
            for match in matches:
                clean_text = re.sub(r'<[^>]+>', '', match).strip()
                if clean_text:
                    # 説明文から重要な単語を抽出
                    words = re.findall(r'[\u3040-\u309F\u30A0-\u30FF\u4E00-\u9FAF]+', clean_text)
                    for word in words:
                        if len(word) > 1 and len(word) < 15:  # 適切な長さの単語のみ
                            keywords.add(word)
        
        return list(keywords)
    
    def _extract_bottom_suggestions(self, html_content: str) -> List[str]:
        """検索結果の下部に表示される関連キーワードを抽出"""
        keywords = set()
        
        # 検索結果の下部に表示される関連キーワード
        bottom_patterns = [
            r'<div[^>]*class="[^"]*bottom[^"]*"[^>]*>([^<]+)</div>',
            r'<ul[^>]*class="[^"]*related[^"]*"[^>]*>(.*?)</ul>',
            r'<li[^>]*class="[^"]*related[^"]*"[^>]*>([^<]+)</li>',
            r'<div[^>]*class="[^"]*suggestion[^"]*"[^>]*>([^<]+)</div>'
        ]
        
        for pattern in bottom_patterns:
            matches = re.findall(pattern, html_content, re.IGNORECASE | re.DOTALL)
            for match in matches:
                clean_text = re.sub(r'<[^>]+>', '', match).strip()
                if clean_text and len(clean_text) > 2:
                    keywords.add(clean_text)
        
        return list(keywords)
    
    def _extract_right_suggestions(self, html_content: str) -> List[str]:
        """検索結果の右側に表示される関連キーワードを抽出"""
        keywords = set()
        
        # 右側のサイドバーに表示される関連キーワード
        right_patterns = [
            r'<div[^>]*class="[^"]*sidebar[^"]*"[^>]*>(.*?)</div>',
            r'<div[^>]*class="[^"]*right[^"]*"[^>]*>(.*?)</div>',
            r'<aside[^>]*>(.*?)</aside>'
        ]
        
        for pattern in right_patterns:
            matches = re.findall(pattern, html_content, re.IGNORECASE | re.DOTALL)
            for match in matches:
                # リンクテキストを抽出
                link_matches = re.findall(r'<a[^>]*>([^<]+)</a>', match)
                for link_text in link_matches:
                    clean_text = re.sub(r'<[^>]+>', '', link_text).strip()
                    if clean_text and len(clean_text) > 2:
                        keywords.add(clean_text)
        
        return list(keywords)
    
    def _extract_top_suggestions(self, html_content: str) -> List[str]:
        """検索結果の上部に表示される関連キーワードを抽出"""
        keywords = set()
        
        # 検索結果の上部に表示される関連キーワード
        top_patterns = [
            r'<div[^>]*class="[^"]*top[^"]*"[^>]*>([^<]+)</div>',
            r'<div[^>]*class="[^"]*header[^"]*"[^>]*>([^<]+)</div>',
            r'<div[^>]*class="[^"]*nav[^"]*"[^>]*>([^<]+)</div>'
        ]
        
        for pattern in top_patterns:
            matches = re.findall(pattern, html_content, re.IGNORECASE | re.DOTALL)
            for match in matches:
                # リンクテキストを抽出
                link_matches = re.findall(r'<a[^>]*>([^<]+)</a>', match)
                for link_text in link_matches:
                    clean_text = re.sub(r'<[^>]+>', '', link_text).strip()
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
            clean_title = re.sub(r'<[^>]+>', '', title).strip()
            if clean_title:
                # タイトルから重要な単語を抽出
                words = re.findall(r'[\u3040-\u309F\u30A0-\u30FF\u4E00-\u9FAF]+', clean_title)
                for word in words:
                    if len(word) > 1:
                        keywords.add(word)
        
        return list(keywords)
    
    def _extract_description_keywords(self, html_content: str) -> List[str]:
        """検索結果の説明文からキーワードを抽出"""
        keywords = set()
        
        # 検索結果の説明文を抽出
        desc_patterns = [
            r'<p[^>]*class="[^"]*description[^"]*"[^>]*>([^<]+)</p>',
            r'<div[^>]*class="[^"]*description[^"]*"[^>]*>([^<]+)</div>',
            r'<span[^>]*class="[^"]*description[^"]*"[^>]*>([^<]+)</span>'
        ]
        
        for pattern in desc_patterns:
            matches = re.findall(pattern, html_content, re.IGNORECASE)
            for match in matches:
                clean_text = re.sub(r'<[^>]+>', '', match).strip()
                if clean_text:
                    # 説明文から重要な単語を抽出
                    words = re.findall(r'[\u3040-\u309F\u30A0-\u30FF\u4E00-\u9FAF]+', clean_text)
                    for word in words:
                        if len(word) > 1 and len(word) < 15:
                            keywords.add(word)
        
        return list(keywords)
    
    def _extract_url_keywords(self, html_content: str) -> List[str]:
        """検索結果のURLからキーワードを抽出"""
        keywords = set()
        
        # 検索結果のURLを抽出
        url_pattern = r'<a[^>]*href="([^"]*)"[^>]*>([^<]+)</a>'
        url_matches = re.findall(url_pattern, html_content)
        
        for url, link_text in url_matches:
            # URLからドメイン名を抽出
            if 'yahoo.co.jp' not in url and 'google.com' not in url:
                # 外部サイトのURLからキーワードを抽出
                domain_match = re.search(r'https?://(?:www\.)?([^/]+)', url)
                if domain_match:
                    domain = domain_match.group(1)
                    # ドメイン名からキーワードを抽出
                    domain_words = re.findall(r'[\u3040-\u309F\u30A0-\u30FF\u4E00-\u9FAF]+', domain)
                    for word in domain_words:
                        if len(word) > 1:
                            keywords.add(word)
            
            # リンクテキストからもキーワードを抽出
            clean_text = re.sub(r'<[^>]+>', '', link_text).strip()
            if clean_text:
                words = re.findall(r'[\u3040-\u309F\u30A0-\u30FF\u4E00-\u9FAF]+', clean_text)
                for word in words:
                    if len(word) > 1:
                        keywords.add(word)
        
        return list(keywords)
    
    def _make_safe_filename(self, text: str) -> str:
        """テキストを安全なファイル名に変換"""
        safe_text = re.sub(r'[<>:"/\\|?*]', '_', text)
        safe_text = re.sub(r'\s+', '_', safe_text)
        safe_text = safe_text[:100]
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
async def test_100_keyword_collector():
    """高速100個版キーワード収集のテスト"""
    print("=== Yahoo検索ベースキーワード収集テスト（高速100個版） ===")
    
    collector = YahooKeywordCollector100()
    
    # テスト用キーワード
    test_keywords = [
        "プログラミング学習",
        "料理 作り方"
    ]
    
    for keyword in test_keywords:
        print(f"\n{'='*50}")
        print(f"テストキーワード: {keyword}")
        print(f"{'='*50}")
        
        # キーワード収集を実行
        start_time = time.time()
        collected_keywords = await collector.collect_all_keywords(keyword)
        elapsed_time = time.time() - start_time
        
        print(f"\n収集されたキーワード（上位20件）:")
        for i, kw in enumerate(collected_keywords[:20], 1):
            print(f"  {i:2d}. {kw}")
        
        if len(collected_keywords) > 20:
            print(f"  ... 他 {len(collected_keywords) - 20}件")
        
        print(f"\n合計: {len(collected_keywords)}件")
        print(f"処理時間: {elapsed_time:.1f}秒")
        
        # 100個目標の達成状況
        if len(collected_keywords) >= 100:
            print(f"🎯 目標達成！ 100個以上のキーワードを収集しました。")
        else:
            print(f"📊 目標まであと {100 - len(collected_keywords)}個")
        
        # レート制限回避
        await asyncio.sleep(1)
    
    # キャッシュクリーンアップ
    collector.clear_cache()

if __name__ == "__main__":
    asyncio.run(test_100_keyword_collector())
