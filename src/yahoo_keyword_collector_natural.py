# src/yahoo_keyword_collector_natural.py
# Yahoo検索ベースのキーワード収集システム（自然サジェスト版・SERP API不要）

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

class YahooKeywordCollectorNatural:
    """Yahoo検索から自然なサジェストキーワードを収集するクラス"""
    
    def __init__(self, output_dir: str = "yahoo_keywords_natural", delay_range: tuple = (0.3, 0.8)):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(exist_ok=True)
        
        # 遅延設定（高速化）
        self.delay_range = delay_range
        
        # Yahoo検索のベースURL
        self.base_url = "https://search.yahoo.co.jp/search"
        
        # ユーザーエージェントのリスト（ローテーション用）
        self.user_agents = [
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0",
        ]
        
        print("[OK] YahooKeywordCollectorNaturalの初期化に成功しました。（自然サジェスト版）")
    
    async def collect_all_keywords(self, main_keyword: str) -> List[str]:
        """メインキーワードから自然なサジェストキーワードを収集"""
        start_time = time.time()
        print(f"\n=== 「{main_keyword}」の自然サジェストキーワード収集開始 ===")
        
        all_keywords: Set[str] = set()
        
        # 1. メインキーワードの基本検索から関連キーワードを収集
        print("\n[ステップ1/3] メインキーワードの基本検索から関連キーワードを収集中...")
        basic_keywords = await self._collect_basic_keywords(main_keyword)
        all_keywords.update(basic_keywords)
        print(f"  -> {len(basic_keywords)}個の基本キーワードを収集しました。")
        
        # 2. 自然サジェストキーワードの収集（戦略的拡張ワード不使用）
        print("\n[ステップ2/3] 自然サジェストキーワードを収集中...")
        natural_keywords = await self._collect_natural_suggestions(main_keyword)
        all_keywords.update(natural_keywords)
        print(f"  -> {len(natural_keywords)}個の自然サジェストキーワードを収集しました。")
        
        # 3. 関連検索の深掘り（並列実行で高速化）
        print("\n[ステップ3/3] 関連検索の深掘りを並列実行中...")
        deep_keywords = await self._collect_deep_keywords_parallel(main_keyword, list(all_keywords)[:8])
        all_keywords.update(deep_keywords)
        print(f"  -> {len(deep_keywords)}個の深掘りキーワードを収集しました。")
        
        # 結果を整理
        final_keywords = sorted(list(all_keywords))
        elapsed_time = time.time() - start_time
        
        print(f"\n✅ キーワード収集完了！ 合計 {len(final_keywords)}個のユニークキーワードを収集しました。")
        print(f"⏱️  処理時間: {elapsed_time:.1f}秒")
        
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
        
        return list(keywords)
    
    async def _collect_deep_keywords_parallel(self, main_keyword: str, seed_keywords: List[str]) -> List[str]:
        """収集されたキーワードから深掘り（並列実行で高速化）"""
        keywords = set()
        
        # 上位8個のキーワードから深掘り（並列実行）
        tasks = []
        for seed_keyword in seed_keywords[:8]:
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
async def test_natural_keyword_collector():
    """自然サジェスト版キーワード収集のテスト"""
    print("=== Yahoo検索ベースキーワード収集テスト（自然サジェスト版） ===")
    
    collector = YahooKeywordCollectorNatural()
    
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
        
        print(f"\n収集されたキーワード（上位15件）:")
        for i, kw in enumerate(collected_keywords[:15], 1):
            print(f"  {i:2d}. {kw}")
        
        if len(collected_keywords) > 15:
            print(f"  ... 他 {len(collected_keywords) - 15}件")
        
        print(f"\n合計: {len(collected_keywords)}件")
        print(f"処理時間: {elapsed_time:.1f}秒")
        
        # レート制限回避
        await asyncio.sleep(1)
    
    # キャッシュクリーンアップ
    collector.clear_cache()

if __name__ == "__main__":
    asyncio.run(test_natural_keyword_collector())
