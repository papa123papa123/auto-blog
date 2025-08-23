# src/yahoo_keyword_collector_simple.py
# Yahoo検索ベースのキーワード収集システム（シンプル版・実際のサジェストのみ）

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

class YahooKeywordCollectorSimple:
    """Yahoo検索から実際のサジェストキーワードのみを収集するクラス（シンプル版）"""
    
    def __init__(self, output_dir: str = "yahoo_keywords_simple", delay_range: tuple = (0.5, 1.0)):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(exist_ok=True)
        
        # 遅延設定（レート制限対策）
        self.delay_range = delay_range
        
        # Yahoo検索のベースURL
        self.base_url = "https://search.yahoo.co.jp/search"
        
        # ユーザーエージェントのリスト（ローテーション用）
        self.user_agents = [
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0",
        ]
        
        print("[OK] YahooKeywordCollectorSimpleの初期化に成功しました。（シンプル版・実際のサジェストのみ）")
    
    async def collect_all_keywords(self, main_keyword: str) -> List[str]:
        """メインキーワードから実際のサジェストキーワードのみを収集（2段階深掘り）"""
        start_time = time.time()
        print(f"\n=== 「{main_keyword}」のシンプルサジェストキーワード収集開始 ===")
        
        all_keywords: Set[str] = set()
        
        # 1. メインキーワードの関連検索ワードを収集
        print("\n[ステップ1/2] メインキーワードの関連検索ワードを収集中...")
        main_suggestions = await self._collect_main_suggestions(main_keyword)
        all_keywords.update(main_suggestions)
        print(f"  -> {len(main_suggestions)}個のメインサジェストを収集しました。")
        
        # 2. 1段階目のキーワードで深掘り（並列実行）
        print("\n[ステップ2/2] 1段階目のキーワードで深掘り中...")
        deep_suggestions = await self._collect_deep_suggestions(list(all_keywords)[:20])  # 上位20個で深掘り
        all_keywords.update(deep_suggestions)
        print(f"  -> {len(deep_suggestions)}個の深掘りサジェストを収集しました。")
        
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
    
    async def _collect_main_suggestions(self, main_keyword: str) -> List[str]:
        """メインキーワードの関連検索ワードを収集"""
        keywords = set()
        
        # 基本検索を実行
        html_content = await self._fetch_yahoo_search(main_keyword)
        if html_content:
            # ページ最下部の関連検索ワードのみを抽出
            related_keywords = self._extract_bottom_related_keywords(html_content)
            keywords.update(related_keywords)
        
        return list(keywords)
    
    async def _collect_deep_suggestions(self, seed_keywords: List[str]) -> List[str]:
        """1段階目のキーワードで深掘りして関連検索ワードを収集"""
        keywords = set()
        
        # 上位20個のキーワードから深掘り
        tasks = []
        for seed_keyword in seed_keywords[:20]:
            task = self._fetch_and_extract_deep_suggestions(seed_keyword)
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
    
    async def _fetch_and_extract_deep_suggestions(self, seed_keyword: str) -> List[str]:
        """シードキーワードから深掘りサジェストを取得"""
        html_content = await self._fetch_yahoo_search(seed_keyword)
        if html_content:
            return self._extract_bottom_related_keywords(html_content)
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
    
    def _extract_bottom_related_keywords(self, html_content: str) -> List[str]:
        """ページ最下部の関連検索ワードを抽出"""
        keywords = set()
        
        # ページ最下部の関連検索ワードのパターン
        # Yahoo検索結果の最下部に表示される「関連する検索」セクション
        related_patterns = [
            # パターン1: 関連する検索セクション
            r'<div[^>]*class="[^"]*related[^"]*"[^>]*>(.*?)</div>',
            r'<section[^>]*class="[^"]*related[^"]*"[^>]*>(.*?)</section>',
            r'<div[^>]*class="[^"]*suggestion[^"]*"[^>]*>(.*?)</div>',
            
            # パターン2: 関連検索のリスト
            r'<ul[^>]*class="[^"]*related[^"]*"[^>]*>(.*?)</ul>',
            r'<ol[^>]*class="[^"]*related[^"]*"[^>]*>(.*?)</ol>',
            
            # パターン3: 関連検索の個別アイテム
            r'<li[^>]*class="[^"]*related[^"]*"[^>]*>([^<]+)</li>',
            r'<a[^>]*class="[^"]*related[^"]*"[^>]*>([^<]+)</a>',
            
            # パターン4: 一般的な関連検索パターン
            r'関連する検索[^>]*>([^<]+)</a>',
            r'関連検索[^>]*>([^<]+)</a>',
            r'関連キーワード[^>]*>([^<]+)</a>',
        ]
        
        for pattern in related_patterns:
            matches = re.findall(pattern, html_content, re.IGNORECASE | re.DOTALL)
            for match in matches:
                # HTMLタグを除去してテキストのみを抽出
                clean_text = re.sub(r'<[^>]+>', '', match).strip()
                if clean_text and len(clean_text) > 2:
                    # 複数行の場合は分割
                    lines = clean_text.split('\n')
                    for line in lines:
                        line = line.strip()
                        if line and len(line) > 2 and len(line) < 100:  # 適切な長さのキーワードのみ
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
async def test_simple_keyword_collector():
    """シンプル版キーワード収集のテスト"""
    print("=== Yahoo検索ベースキーワード収集テスト（シンプル版・実際のサジェストのみ） ===")
    
    collector = YahooKeywordCollectorSimple()
    
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
        
        # レート制限回避
        await asyncio.sleep(2)
    
    # キャッシュクリーンアップ
    collector.clear_cache()

if __name__ == "__main__":
    asyncio.run(test_simple_keyword_collector())
