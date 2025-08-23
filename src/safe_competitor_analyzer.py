# src/safe_competitor_analyzer.py
# レート制限回避型競合分析システム

import asyncio
import aiohttp
import pandas as pd
import re
import time
import random
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime
import json
import logging

# ロガーの設定
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

class SafeCompetitorAnalyzer:
    """レート制限回避型競合分析システム"""
    
    def __init__(self, output_dir: str = "safe_competitor_analysis"):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(exist_ok=True)
        
        # レート制限回避のための設定
        self.base_delay = (5.0, 10.0)  # 基本遅延時間（秒）
        self.search_delay = (8.0, 15.0)  # 検索間遅延時間（秒）
        self.session_delay = (3.0, 8.0)  # セッション間遅延時間（秒）
        self.max_retries = 3  # 最大リトライ回数
        self.exponential_backoff = True  # 指数バックオフ有効
        
        # Yahoo検索のベースURL
        self.yahoo_base_url = "https://search.yahoo.co.jp/search"
        
        # ユーザーエージェントのリスト
        self.user_agents = [
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0",
            "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        ]
        
        # 弱い競合サイトの定義
        self.weak_competitors = {
            "個人ブログ": ["ameblo.jp", "fc2.com", "seesaa.net", "livedoor.jp", "blog.jp"],
            "SNS": ["twitter.com", "facebook.com", "instagram.com", "tiktok.com"],
            "Q&Aサイト": ["yahoo.co.jp", "okwave.jp", "chiebukuro.yahoo.co.jp"],
            "まとめサイト": ["matome.naver.jp", "togetter.com", "naver.jp"],
            "個人サイト": ["wixsite.com", "squarespace.com", "wordpress.com"]
        }
        
        # 統計情報
        self.stats = {
            "total_searches": 0,
            "successful_searches": 0,
            "rate_limited": 0,
            "errors": 0,
            "start_time": None,
            "end_time": None
        }
        
        print("[OK] SafeCompetitorAnalyzerの初期化に成功しました。（レート制限回避型）")
    
    async def analyze_keywords_safely(self, keywords: List[str], 
                                    batch_size: int = 5, 
                                    max_concurrent: int = 2) -> pd.DataFrame:
        """キーワードを安全に分析（レート制限回避）"""
        
        self.stats["start_time"] = time.time()
        print(f"\n=== 安全な競合分析開始 ===")
        print(f"対象キーワード数: {len(keywords)}件")
        print(f"バッチサイズ: {batch_size}件")
        print(f"最大同時実行数: {max_concurrent}件")
        print(f"予想処理時間: {self._estimate_processing_time(len(keywords), batch_size, max_concurrent)}")
        
        results = []
        
        # キーワードをバッチに分割
        batches = [keywords[i:i + batch_size] for i in range(0, len(keywords), batch_size)]
        print(f"バッチ数: {len(batches)}")
        
        # セマフォで同時実行数を制限
        semaphore = asyncio.Semaphore(max_concurrent)
        
        for batch_num, batch in enumerate(batches, 1):
            print(f"\n--- バッチ {batch_num}/{len(batches)} 処理中 ---")
            print(f"キーワード: {batch}")
            
            # バッチ内のキーワードを並列処理
            batch_tasks = []
            for keyword in batch:
                task = asyncio.create_task(self._analyze_single_keyword_safely(keyword, semaphore))
                batch_tasks.append(task)
            
            # バッチ完了を待機
            batch_results = await asyncio.gather(*batch_tasks, return_exceptions=True)
            
            # 結果を統合
            for result in batch_results:
                if isinstance(result, dict):
                    results.append(result)
                else:
                    print(f"[ERROR] キーワード分析でエラー: {result}")
                    self.stats["errors"] += 1
            
            # バッチ間の待機（レート制限回避）
            if batch_num < len(batches):
                wait_time = random.uniform(*self.session_delay)
                print(f"バッチ間待機: {wait_time:.1f}秒")
                await asyncio.sleep(wait_time)
        
        self.stats["end_time"] = time.time()
        self.stats["total_searches"] = len(keywords) * 3  # allintitle, intitle, 通常検索
        
        # 結果をDataFrameに変換
        results_df = pd.DataFrame(results)
        return results_df
    
    async def _analyze_single_keyword_safely(self, keyword: str, semaphore: asyncio.Semaphore) -> Dict[str, Any]:
        """単一キーワードを安全に分析"""
        
        async with semaphore:
            print(f"  -> 分析開始: {keyword}")
            
            result = {
                "キーワード": keyword,
                "allintitle_count": "Error",
                "intitle_count": "Error",
                "weak_competitors_in_top10": [],
                "weak_competitors_count": 0,
                "analysis_time": datetime.now().isoformat(),
                "status": "pending"
            }
            
            try:
                # 1. All Intitle検索
                print(f"    -> All Intitle検索: {keyword}")
                allintitle_count = await self._search_allintitle_safely(keyword)
                result["allintitle_count"] = allintitle_count
                
                # 検索間待機
                await asyncio.sleep(random.uniform(*self.search_delay))
                
                # 2. Intitle検索
                print(f"    -> Intitle検索: {keyword}")
                intitle_count = await self._search_intitle_safely(keyword)
                result["intitle_count"] = intitle_count
                
                # 検索間待機
                await asyncio.sleep(random.uniform(*self.search_delay))
                
                # 3. 通常検索（競合サイト分析）
                print(f"    -> 通常検索（競合分析）: {keyword}")
                competitors = await self._search_competitors_safely(keyword)
                result["weak_competitors_in_top10"] = competitors
                result["weak_competitors_count"] = len(competitors)
                
                result["status"] = "completed"
                self.stats["successful_searches"] += 1
                
                print(f"    -> 完了: {keyword} (allintitle: {allintitle_count}, intitle: {intitle_count}, 競合: {len(competitors)}件)")
                
            except Exception as e:
                print(f"    -> エラー: {keyword} - {e}")
                result["status"] = "error"
                result["error_message"] = str(e)
                self.stats["errors"] += 1
            
            return result
    
    async def _search_allintitle_safely(self, keyword: str) -> int:
        """All Intitle検索を安全に実行"""
        query = f'allintitle:"{keyword}"'
        return await self._execute_search_safely(query, "allintitle")
    
    async def _search_intitle_safely(self, keyword: str) -> int:
        """Intitle検索を安全に実行"""
        query = f'intitle:"{keyword}"'
        return await self._execute_search_safely(query, "intitle")
    
    async def _search_competitors_safely(self, keyword: str) -> List[Dict[str, Any]]:
        """競合サイト検索を安全に実行"""
        query = keyword
        html_content = await self._fetch_html_safely(query)
        
        if not html_content:
            return []
        
        return self._extract_competitors_from_html(html_content)
    
    async def _execute_search_safely(self, query: str, search_type: str) -> int:
        """検索を安全に実行（レート制限回避）"""
        
        for attempt in range(self.max_retries):
            try:
                html_content = await self._fetch_html_safely(query)
                
                if html_content:
                    if search_type == "allintitle":
                        return self._extract_allintitle_count(html_content)
                    elif search_type == "intitle":
                        return self._extract_intitle_count(html_content)
                
                return 0
                
            except Exception as e:
                if "429" in str(e) or "Too Many Requests" in str(e):
                    self.stats["rate_limited"] += 1
                    wait_time = self._calculate_backoff_wait(attempt)
                    print(f"      -> レート制限検知。{wait_time:.1f}秒待機してリトライ...")
                    await asyncio.sleep(wait_time)
                else:
                    print(f"      -> 検索エラー: {e}")
                    if attempt < self.max_retries - 1:
                        wait_time = random.uniform(*self.base_delay)
                        await asyncio.sleep(wait_time)
                    else:
                        raise e
        
        return 0
    
    async def _fetch_html_safely(self, query: str) -> Optional[str]:
        """HTMLを安全に取得（レート制限回避）"""
        
        # 基本待機時間
        await asyncio.sleep(random.uniform(*self.base_delay))
        
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
                url = f"{self.yahoo_base_url}?{self._build_query_string(params)}"
                async with session.get(url, headers=headers) as response:
                    
                    if response.status == 200:
                        content = await response.text()
                        
                        # HTMLを保存（デバッグ用）
                        safe_filename = self._make_safe_filename(f"search_{query}")
                        file_path = self.output_dir / f"{safe_filename}.html"
                        with open(file_path, 'w', encoding='utf-8') as f:
                            f.write(content)
                        
                        return content
                        
                    elif response.status == 429:
                        raise Exception(f"HTTP 429: Too Many Requests for query: {query}")
                    else:
                        print(f"      -> HTTP {response.status} for query: {query}")
                        return None
                        
        except Exception as e:
            print(f"      -> 検索エラー: {e}")
            raise e
    
    def _extract_allintitle_count(self, html_content: str) -> int:
        """HTMLからAll Intitle件数を抽出"""
        # Yahoo検索結果の件数表示を抽出
        patterns = [
            r'約\s*([0-9,]+)\s*件',
            r'([0-9,]+)\s*件の検索結果',
            r'検索結果\s*([0-9,]+)\s*件'
        ]
        
        for pattern in patterns:
            match = re.search(pattern, html_content)
            if match:
                count_str = match.group(1).replace(',', '')
                try:
                    return int(count_str)
                except ValueError:
                    continue
        
        return 0
    
    def _extract_intitle_count(self, html_content: str) -> int:
        """HTMLからIntitle件数を抽出"""
        # All Intitleと同様の処理
        return self._extract_allintitle_count(html_content)
    
    def _extract_competitors_from_html(self, html_content: str) -> List[Dict[str, Any]]:
        """HTMLから競合サイトを抽出"""
        competitors = []
        
        # 検索結果のリンクを抽出
        link_patterns = [
            r'<a[^>]*href="([^"]*)"[^>]*>([^<]+)</a>',
            r'<a[^>]*>([^<]+)</a>[^>]*href="([^"]*)"'
        ]
        
        for pattern in link_patterns:
            matches = re.findall(pattern, html_content)
            for match in matches:
                if len(match) == 2:
                    url, text = match
                    if url.startswith('http'):
                        domain = self._extract_domain(url)
                        category = self._categorize_domain(domain)
                        
                        if category:
                            competitors.append({
                                'domain': domain,
                                'category': category,
                                'url': url,
                                'title': text.strip()
                            })
        
        # 上位10件に制限
        return competitors[:10]
    
    def _extract_domain(self, url: str) -> str:
        """URLからドメインを抽出"""
        import urllib.parse
        try:
            parsed = urllib.parse.urlparse(url)
            return parsed.netloc.lower()
        except:
            return url.lower()
    
    def _categorize_domain(self, domain: str) -> Optional[str]:
        """ドメインをカテゴリに分類"""
        for category, domains in self.weak_competitors.items():
            if any(weak_domain in domain for weak_domain in domains):
                return category
        return None
    
    def _calculate_backoff_wait(self, attempt: int) -> float:
        """指数バックオフの待機時間を計算"""
        if self.exponential_backoff:
            base_wait = 10.0
            max_wait = 300.0  # 最大5分
            wait_time = min(base_wait * (2 ** attempt), max_wait)
            return wait_time + random.uniform(0, 10)  # ランダム要素追加
        else:
            return random.uniform(15, 30)
    
    def _build_query_string(self, params: Dict[str, str]) -> str:
        """クエリパラメータを文字列に変換"""
        import urllib.parse
        return urllib.parse.urlencode(params)
    
    def _make_safe_filename(self, text: str) -> str:
        """テキストを安全なファイル名に変換"""
        safe_text = re.sub(r'[<>:"/\\|?*]', '_', text)
        safe_text = re.sub(r'\s+', '_', safe_text)
        safe_text = safe_text[:100]
        return safe_text
    
    def _estimate_processing_time(self, keyword_count: int, batch_size: int, max_concurrent: int) -> str:
        """処理時間を推定"""
        # 1キーワードあたりの処理時間（秒）
        base_time_per_keyword = 30  # 基本待機時間 + 検索時間
        
        # バッチ数
        batch_count = (keyword_count + batch_size - 1) // batch_size
        
        # 並列処理による効率化
        effective_batch_count = batch_count / max_concurrent
        
        # 総処理時間（分）
        total_minutes = (effective_batch_count * base_time_per_keyword) / 60
        
        if total_minutes < 60:
            return f"{total_minutes:.1f}分"
        else:
            hours = total_minutes / 60
            return f"{hours:.1f}時間"
    
    def save_results(self, results_df: pd.DataFrame) -> str:
        """結果をCSVファイルに保存"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"safe_competitor_analysis_{timestamp}.csv"
        file_path = self.output_dir / filename
        
        # 結果を整形
        formatted_df = self._format_results_for_csv(results_df)
        
        # CSV保存
        formatted_df.to_csv(file_path, index=False, encoding='utf-8-sig')
        
        return str(file_path)
    
    def _format_results_for_csv(self, results_df: pd.DataFrame) -> pd.DataFrame:
        """CSV出力用に結果を整形"""
        if results_df.empty:
            return results_df
        
        # 競合サイトの詳細を文字列に変換
        formatted_df = results_df.copy()
        
        if 'weak_competitors_in_top10' in formatted_df.columns:
            formatted_df['競合サイト詳細'] = formatted_df['weak_competitors_in_top10'].apply(
                lambda x: '; '.join([f"{c.get('domain', '')}({c.get('category', '')})" for c in x]) if isinstance(x, list) else ''
            )
        
        # 列名を日本語化
        column_mapping = {
            'キーワード': 'キーワード',
            'allintitle_count': 'All Intitle件数',
            'intitle_count': 'Intitle件数',
            'weak_competitors_count': '弱い競合件数',
            'analysis_time': '分析時刻',
            'status': 'ステータス'
        }
        
        formatted_df = formatted_df.rename(columns=column_mapping)
        
        return formatted_df
    
    def get_analysis_summary(self, results_df: pd.DataFrame) -> str:
        """分析結果のサマリーを取得"""
        if results_df.empty:
            return "分析結果がありません。"
        
        total_keywords = len(results_df)
        completed = len(results_df[results_df['status'] == 'completed'])
        errors = len(results_df[results_df['status'] == 'error'])
        
        summary = f"""
=== 分析サマリー ===
総キーワード数: {total_keywords}件
完了: {completed}件
エラー: {errors}件
成功率: {(completed/total_keywords)*100:.1f}%

=== 統計情報 ===
総検索回数: {self.stats['total_searches']}回
成功: {self.stats['successful_searches']}回
レート制限: {self.stats['rate_limited']}回
エラー: {self.stats['errors']}回

=== 処理時間 ===
開始: {datetime.fromtimestamp(self.stats['start_time']).strftime('%Y-%m-%d %H:%M:%S') if self.stats['start_time'] else 'N/A'}
終了: {datetime.fromtimestamp(self.stats['end_time']).strftime('%Y-%m-%d %H:%M:%S') if self.stats['end_time'] else 'N/A'}
"""
        
        if self.stats['start_time'] and self.stats['end_time']:
            duration = self.stats['end_time'] - self.stats['start_time']
            summary += f"総処理時間: {duration/60:.1f}分"
        
        return summary

# テスト用コード
async def test_safe_analyzer():
    """安全な競合分析システムのテスト"""
    print("=== レート制限回避型競合分析システムテスト ===")
    
    analyzer = SafeCompetitorAnalyzer()
    
    # テスト用キーワード（少数でテスト）
    test_keywords = ["プログラミング学習", "料理 作り方"]
    
    print(f"\nテストキーワード: {test_keywords}")
    
    # 安全な分析を実行
    results_df = await analyzer.analyze_keywords_safely(
        keywords=test_keywords,
        batch_size=2,
        max_concurrent=1
    )
    
    # 結果を表示
    print(f"\n=== 分析結果 ===")
    print(results_df.to_string(index=False))
    
    # サマリーを表示
    print(analyzer.get_analysis_summary(results_df))
    
    # 結果を保存
    output_file = analyzer.save_results(results_df)
    print(f"\n✅ 結果を保存しました: {output_file}")

if __name__ == "__main__":
    asyncio.run(test_safe_analyzer())
