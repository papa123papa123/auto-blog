# src/yahoo_keyword_collector_quality.py
# Yahoo検索ベースのキーワード収集システム（質重視版・実際のサジェストのみ）

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

class YahooKeywordCollectorQuality:
    """Yahoo検索から実際のサジェストキーワードのみを収集するクラス（質重視）"""
    
    def __init__(self, output_dir: str = "yahoo_keywords_quality", delay_range: tuple = (0.3, 0.8)):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(exist_ok=True)
        
        # 遅延設定
        self.delay_range = delay_range
        
        # Yahoo検索のベースURL
        self.base_url = "https://search.yahoo.co.jp/search"
        
        # ユーザーエージェントのリスト（ローテーション用）
        self.user_agents = [
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0",
        ]
        
        print("[OK] YahooKeywordCollectorQualityの初期化に成功しました。（質重視版・実際のサジェストのみ）")
    
    async def collect_all_keywords(self, main_keyword: str) -> List[str]:
        """メインキーワードから実際のサジェストキーワードのみを収集"""
        start_time = time.time()
        print(f"\n=== 「{main_keyword}」の質重視サジェストキーワード収集開始 ===")
        
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
        
        # 3. 関連検索の深掘り（並列実行）
        print("\n[ステップ3/3] 関連検索の深掘りを並列実行中...")
        deep_keywords = await self._collect_deep_keywords_parallel(main_keyword, list(all_keywords)[:10])
        all_keywords.update(deep_keywords)
        print(f"  -> {len(deep_keywords)}個の深掘りキーワードを収集しました。")
        
        # 結果を整理
        final_keywords = sorted(list(all_keywords))
        elapsed_time = time.time() - start_time
        
        print(f"\n✅ キーワード収集完了！ 合計 {len(final_keywords)}個のユニークキーワードを収集しました。")
        print(f"⏱️  処理時間: {elapsed_time:.1f}秒")
        
        # 質の確認
        print(f"\n📊 収集されたキーワードの質:")
        print(f"  - 実際のサジェスト: {len([kw for kw in final_keywords if self._is_quality_keyword(kw, main_keyword)])}個")
        print(f"  - 関連性の高いキーワード: {len([kw for kw in final_keywords if self._is_relevant_keyword(kw, main_keyword)])}個")
        
        return final_keywords
    
    async def _collect_basic_keywords(self, main_keyword: str) -> List[str]:
        """メインキーワードの基本検索から関連キーワードを収集（サジェストのみ）"""
        keywords = set()
        
        # 基本検索を実行
        html_content = await self._fetch_yahoo_search(main_keyword)
        if html_content:
            # 関連キーワードのみを抽出（サジェスト）
            related_keywords = self._extract_related_keywords(html_content)
            keywords.update(related_keywords)
        
        return list(keywords)
    
    async def _collect_natural_suggestions(self, main_keyword: str) -> List[str]:
        """自然なサジェストキーワードを収集（戦略的拡張ワード不使用）"""
        keywords = set()
        
        # メインキーワードの検索結果から自然に出てくる関連キーワードを抽出
        html_content = await self._fetch_yahoo_search(main_keyword)
        if html_content:
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
    
    async def _collect_deep_keywords_parallel(self, main_keyword: str, seed_keywords: List[str]) -> List[str]:
        """収集されたキーワードから深掘り（並列実行）"""
        keywords = set()
        
        # 上位10個のキーワードから深掘り
        tasks = []
        for seed_keyword in seed_keywords[:10]:
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
        """HTMLから関連キーワードを抽出（サジェストのみ）"""
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
    
    def _is_quality_keyword(self, keyword: str, main_keyword: str) -> bool:
        """キーワードの質を判定"""
        # 短すぎる、長すぎるキーワードを除外
        if len(keyword) < 3 or len(keyword) > 50:
            return False
        
        # 質問形式のキーワードを除外
        if keyword.endswith('？') or keyword.endswith('?'):
            return False
        
        # 設定や操作方法に関するキーワードを除外
        if any(word in keyword for word in ['設定', '方法', 'やり方', '使い方', 'オフ', 'オン']):
            return False
        
        return True
    
    def _is_relevant_keyword(self, keyword: str, main_keyword: str) -> bool:
        """キーワードの関連性を判定"""
        # メインキーワードとの関連性をチェック
        main_words = set(main_keyword.split())
        keyword_words = set(keyword.split())
        
        # 共通の単語があるかチェック
        common_words = main_words & keyword_words
        if common_words:
            return True
        
        # メインキーワードの一部が含まれているかチェック
        for word in main_words:
            if word in keyword:
                return True
        
        return False
    
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
async def test_quality_keyword_collector():
    """質重視版キーワード収集のテスト"""
    print("=== Yahoo検索ベースキーワード収集テスト（質重視版・実際のサジェストのみ） ===")
    
    collector = YahooKeywordCollectorQuality()
    
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
            quality_mark = "✅" if collector._is_quality_keyword(kw, keyword) else "❌"
            relevance_mark = "🔗" if collector._is_relevant_keyword(kw, keyword) else "🔴"
            print(f"  {i:2d}. {kw} {quality_mark}{relevance_mark}")
        
        if len(collected_keywords) > 20:
            print(f"  ... 他 {len(collected_keywords) - 20}件")
        
        print(f"\n合計: {len(collected_keywords)}件")
        print(f"処理時間: {elapsed_time:.1f}秒")
        
        # レート制限回避
        await asyncio.sleep(1)
    
    # キャッシュクリーンアップ
    collector.clear_cache()

if __name__ == "__main__":
    asyncio.run(test_quality_keyword_collector())
