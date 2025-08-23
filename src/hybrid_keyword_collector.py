# src/hybrid_keyword_collector.py
# Yahoo + Googleのハイブリッド2段階深掘りキーワード収集システム

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

class HybridKeywordCollector:
    """Yahoo + Googleのハイブリッド2段階深掘りキーワード収集クラス"""
    
    def __init__(self, output_dir: str = "hybrid_keywords"):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(exist_ok=True)
        
        # レート制限回避のための遅延設定
        self.yahoo_delay = (3.0, 6.0)  # Yahoo用遅延
        self.google_delay = (3.0, 6.0)  # Google用遅延
        self.session_delay = (2.0, 5.0)  # セッション間遅延
        
        # Yahoo検索のベースURL
        self.yahoo_base_url = "https://search.yahoo.co.jp/search"
        
        # Google検索のベースURL
        self.google_base_url = "https://www.google.com/search"
        
        # ユーザーエージェントのリスト（ローテーション用）
        self.user_agents = [
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0",
        ]
        
        print("[OK] HybridKeywordCollectorの初期化に成功しました。（Yahoo + Google ハイブリッド版）")
    
    async def collect_all_keywords(self, main_keyword: str) -> List[str]:
        """メインキーワードからYahoo + Googleのハイブリッド収集"""
        start_time = time.time()
        print(f"\n=== 「{main_keyword}」のハイブリッド2段階深掘りキーワード収集開始 ===")
        
        all_keywords: Set[str] = set()
        
        # YahooとGoogleを並列実行
        print("\n[ステップ1/2] Yahoo + Googleの並列収集開始...")
        yahoo_task = asyncio.create_task(self._collect_yahoo_2stage(main_keyword))
        google_task = asyncio.create_task(self._collect_google_2stage(main_keyword))
        
        # 並列実行
        yahoo_result, google_result = await asyncio.gather(yahoo_task, google_task, return_exceptions=True)
        
        # 結果を統合
        if isinstance(yahoo_result, list):
            all_keywords.update(yahoo_result)
            print(f"  -> Yahoo: {len(yahoo_result)}個のキーワードを収集")
        else:
            print(f"  -> [ERROR] Yahoo収集でエラーが発生: {yahoo_result}")
        
        if isinstance(google_result, list):
            all_keywords.update(google_result)
            print(f"  -> Google: {len(google_result)}個のキーワードを収集")
        else:
            print(f"  -> [ERROR] Google収集でエラーが発生: {google_result}")
        
        # 結果を整理
        final_keywords = sorted(list(all_keywords))
        elapsed_time = time.time() - start_time
        
        print(f"\n✅ ハイブリッドキーワード収集完了！ 合計 {len(final_keywords)}個のユニークキーワードを収集しました。")
        print(f"⏱️  処理時間: {elapsed_time:.1f}秒")
        
        # 100個目標の達成状況
        if len(final_keywords) >= 100:
            print(f"🎯 目標達成！ 100個以上のキーワードを収集しました。")
        else:
            print(f"📊 目標まであと {100 - len(final_keywords)}個")
        
        return final_keywords
    
    async def _collect_yahoo_2stage(self, main_keyword: str) -> List[str]:
        """Yahoo検索の2段階深掘り"""
        keywords = set()
        
        # 1段階目: メインキーワードの関連検索ワード
        print("    [Yahoo] 1段階目: メインキーワードの関連検索ワードを収集中...")
        main_suggestions = await self._collect_yahoo_main_suggestions(main_keyword)
        keywords.update(main_suggestions)
        print(f"      -> {len(main_suggestions)}個のメインサジェストを収集")
        
        # レート制限回避のための待機
        await asyncio.sleep(random.uniform(*self.session_delay))
        
        # 2段階目: 1段階目のキーワードで深掘り
        print("    [Yahoo] 2段階目: 1段階目のキーワードで深掘り中...")
        deep_suggestions = await self._collect_yahoo_deep_suggestions(list(keywords)[:20])
        keywords.update(deep_suggestions)
        print(f"      -> {len(deep_suggestions)}個の深掘りサジェストを収集")
        
        return list(keywords)
    
    async def _collect_google_2stage(self, main_keyword: str) -> List[str]:
        """Google検索の2段階深掘り"""
        keywords = set()
        
        # 1段階目: メインキーワードの「他の人はこちらも検索」
        print("    [Google] 1段階目: メインキーワードの「他の人はこちらも検索」を収集中...")
        main_suggestions = await self._collect_google_main_suggestions(main_keyword)
        keywords.update(main_suggestions)
        print(f"      -> {len(main_suggestions)}個のメインサジェストを収集")
        
        # レート制限回避のための待機
        await asyncio.sleep(random.uniform(*self.session_delay))
        
        # 2段階目: 1段階目のキーワードで深掘り
        print("    [Google] 2段階目: 1段階目のキーワードで深掘り中...")
        deep_suggestions = await self._collect_google_deep_suggestions(list(keywords)[:20])
        keywords.update(deep_suggestions)
        print(f"      -> {len(deep_suggestions)}個の深掘りサジェストを収集")
        
        return list(keywords)
    
    async def _collect_yahoo_main_suggestions(self, main_keyword: str) -> List[str]:
        """Yahoo検索のメインサジェスト収集"""
        html_content = await self._fetch_yahoo_search(main_keyword)
        if html_content:
            return self._extract_yahoo_suggestions(html_content)
        return []
    
    async def _collect_yahoo_deep_suggestions(self, seed_keywords: List[str]) -> List[str]:
        """Yahoo検索の深掘りサジェスト収集"""
        keywords = set()
        
        # 上位20個のキーワードから深掘り
        for i, seed_keyword in enumerate(seed_keywords[:20]):
            print(f"      -> 深掘り {i+1}/20: {seed_keyword}")
            
            html_content = await self._fetch_yahoo_search(seed_keyword)
            if html_content:
                suggestions = self._extract_yahoo_suggestions(html_content)
                keywords.update(suggestions)
            
            # レート制限回避のための待機
            await asyncio.sleep(random.uniform(*self.yahoo_delay))
        
        return list(keywords)
    
    async def _collect_google_main_suggestions(self, main_keyword: str) -> List[str]:
        """Google検索のメインサジェスト収集"""
        html_content = await self._fetch_google_search(main_keyword)
        if html_content:
            return self._extract_google_suggestions(html_content)
        return []
    
    async def _collect_google_deep_suggestions(self, seed_keywords: List[str]) -> List[str]:
        """Google検索の深掘りサジェスト収集"""
        keywords = set()
        
        # 上位20個のキーワードから深掘り
        for i, seed_keyword in enumerate(seed_keywords[:20]):
            print(f"      -> 深掘り {i+1}/20: {seed_keyword}")
            
            html_content = await self._fetch_google_search(seed_keyword)
            if html_content:
                suggestions = self._extract_google_suggestions(html_content)
                keywords.update(suggestions)
            
            # レート制限回避のための待機
            await asyncio.sleep(random.uniform(*self.google_delay))
        
        return list(keywords)
    
    async def _fetch_yahoo_search(self, query: str) -> Optional[str]:
        """Yahoo検索を実行してHTMLを取得"""
        try:
            user_agent = random.choice(self.user_agents)
            
            params = {
                'p': query,
                'ei': 'UTF-8',
                'fr': 'top_ga1_sa'
            }
            
            headers = {
                'User-Agent': user_agent,
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
                'Accept-Language': 'ja,en-US;q=0.7,en;q=0.3',
                'Accept-Encoding': 'gzip, deflate',
                'DNT': '1',
                'Connection': 'keep-alive',
                'Upgrade-Insecure-Requests': '1',
            }
            
            async with aiohttp.ClientSession() as session:
                url = f"{self.yahoo_base_url}?{urlencode(params)}"
                async with session.get(url, headers=headers) as response:
                    if response.status == 200:
                        content = await response.text()
                        
                        # HTMLを保存（デバッグ用）
                        safe_filename = self._make_safe_filename(f"yahoo_{query}")
                        file_path = self.output_dir / f"{safe_filename}.html"
                        with open(file_path, 'w', encoding='utf-8') as f:
                            f.write(content)
                        
                        return content
                    else:
                        print(f"      -> [WARN] Yahoo検索「{query}」でHTTP {response.status}")
                        return None
                        
        except Exception as e:
            print(f"      -> [ERROR] Yahoo検索「{query}」でエラー: {e}")
            return None
    
    async def _fetch_google_search(self, query: str) -> Optional[str]:
        """Google検索を実行してHTMLを取得"""
        try:
            user_agent = random.choice(self.user_agents)
            
            params = {
                'q': query,
                'hl': 'ja',
                'gl': 'jp'
            }
            
            headers = {
                'User-Agent': user_agent,
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
                'Accept-Language': 'ja,en-US;q=0.7,en;q=0.3',
                'Accept-Encoding': 'gzip, deflate',
                'DNT': '1',
                'Connection': 'keep-alive',
                'Upgrade-Insecure-Requests': '1',
            }
            
            async with aiohttp.ClientSession() as session:
                url = f"{self.google_base_url}?{urlencode(params)}"
                async with session.get(url, headers=headers) as response:
                    if response.status == 200:
                        content = await response.text()
                        
                        # HTMLを保存（デバッグ用）
                        safe_filename = self._make_safe_filename(f"google_{query}")
                        file_path = self.output_dir / f"{safe_filename}.html"
                        with open(file_path, 'w', encoding='utf-8') as f:
                            f.write(content)
                        
                        return content
                    else:
                        print(f"      -> [WARN] Google検索「{query}」でHTTP {response.status}")
                        return None
                        
        except Exception as e:
            print(f"      -> [ERROR] Google検索「{query}」でエラー: {e}")
            return None
    
    def _extract_yahoo_suggestions(self, html_content: str) -> List[str]:
        """Yahoo検索結果からサジェストを抽出"""
        keywords = set()
        
        # Yahoo検索結果の最下部の関連検索ワード
        related_patterns = [
            r'<div[^>]*class="[^"]*related[^"]*"[^>]*>(.*?)</div>',
            r'<section[^>]*class="[^"]*related[^"]*"[^>]*>(.*?)</section>',
            r'<div[^>]*class="[^"]*suggestion[^"]*"[^>]*>(.*?)</div>',
            r'<ul[^>]*class="[^"]*related[^"]*"[^>]*>(.*?)</ul>',
            r'<li[^>]*class="[^"]*related[^"]*"[^>]*>([^<]+)</li>',
            r'<a[^>]*class="[^"]*related[^"]*"[^>]*>([^<]+)</a>',
            r'関連する検索[^>]*>([^<]+)</a>',
            r'関連検索[^>]*>([^<]+)</a>',
        ]
        
        for pattern in related_patterns:
            matches = re.findall(pattern, html_content, re.IGNORECASE | re.DOTALL)
            for match in matches:
                clean_text = re.sub(r'<[^>]+>', '', match).strip()
                if clean_text and len(clean_text) > 2:
                    lines = clean_text.split('\n')
                    for line in lines:
                        line = line.strip()
                        if line and len(line) > 2 and len(line) < 100:
                            keywords.add(line)
        
        return list(keywords)
    
    def _extract_google_suggestions(self, html_content: str) -> List[str]:
        """Google検索結果からサジェストを抽出"""
        keywords = set()
        
        # Google検索結果の最下部の「他の人はこちらも検索」
        related_patterns = [
            r'<div[^>]*class="[^"]*related[^"]*"[^>]*>(.*?)</div>',
            r'<div[^>]*class="[^"]*suggestion[^"]*"[^>]*>(.*?)</div>',
            r'<div[^>]*class="[^"]*bottom[^"]*"[^>]*>(.*?)</div>',
            r'<ul[^>]*class="[^"]*related[^"]*"[^>]*>(.*?)</ul>',
            r'<li[^>]*class="[^"]*related[^"]*"[^>]*>([^<]+)</li>',
            r'<a[^>]*class="[^"]*related[^"]*"[^>]*>([^<]+)</a>',
            r'他の人はこちらも検索[^>]*>([^<]+)</a>',
            r'関連検索[^>]*>([^<]+)</a>',
        ]
        
        for pattern in related_patterns:
            matches = re.findall(pattern, html_content, re.IGNORECASE | re.DOTALL)
            for match in matches:
                clean_text = re.sub(r'<[^>]+>', '', match).strip()
                if clean_text and len(clean_text) > 2:
                    lines = clean_text.split('\n')
                    for line in lines:
                        line = line.strip()
                        if line and len(line) > 2 and len(line) < 100:
                            keywords.add(line)
        
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
async def test_hybrid_collector():
    """ハイブリッドキーワード収集のテスト"""
    print("=== Yahoo + Google ハイブリッド2段階深掘りキーワード収集テスト ===")
    
    collector = HybridKeywordCollector()
    
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
        
        # レート制限回避のための待機
        await asyncio.sleep(5)
    
    # キャッシュクリーンアップ
    collector.clear_cache()

if __name__ == "__main__":
    asyncio.run(test_hybrid_collector())
