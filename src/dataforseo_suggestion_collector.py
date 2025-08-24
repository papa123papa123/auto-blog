# src/dataforseo_suggestion_collector.py

import asyncio
import random
import time
import json
from typing import List, Set, Dict, Optional
from urllib.parse import quote_plus
import aiohttp
import requests


class DataForSEOSuggestionCollector:
    """
    Data for SEO APIを使用してメインKWから100以上のサジェストを収集するクラス
    単回APIで3つのソースからサジェストを取得
    ランダムなレイテンシーでレート制限を回避
    """
    
    def __init__(self, api_key: str, api_secret: str):
        self.api_key = api_key
        self.api_secret = api_secret
        self.base_url = "https://api.dataforseo.com/v3"
        
        self.collected_suggestions: Set[str] = set()
        self.suggestion_sources: Dict[str, List[str]] = {}
        
        # レート制限回避のための設定
        self.min_delay = 1.0  # 最小待機時間（秒）
        self.max_delay = 3.0  # 最大待機時間（秒）
        self.max_retries = 3   # 最大リトライ回数
        
        # セッション管理
        self.session = None
        
        print("[OK] DataForSEOSuggestionCollectorの初期化に成功しました")
    
    async def _get_session(self) -> aiohttp.ClientSession:
        """aiohttpセッションを取得"""
        if self.session is None or self.session.closed:
            import base64
            
            # Base64エンコードされた認証情報を使用
            auth_string = f"{self.api_key}:{self.api_secret}"
            encoded_auth = base64.b64encode(auth_string.encode()).decode()
            
            self.session = aiohttp.ClientSession(
                timeout=aiohttp.ClientTimeout(total=60),
                headers={
                    'Authorization': f'Basic {encoded_auth}',
                    'Content-Type': 'application/json'
                }
            )
        return self.session
    
    async def _random_delay(self):
        """ランダムな待機時間でレート制限を回避"""
        delay = random.uniform(self.min_delay, self.max_delay)
        print(f"  -> {delay:.1f}秒待機中...")
        await asyncio.sleep(delay)
    
    async def _get_google_suggestions(self, keyword: str) -> List[str]:
        """Data for SEO Google Suggest APIからサジェストを取得"""
        try:
            session = await self._get_session()
            
            # Google Suggest APIのエンドポイント
            endpoint = f"{self.base_url}/keywords_data/google/keyword_suggestions"
            
            # 正しいペイロード形式（配列）
            payload = [{
                "keyword": keyword,
                "location_code": 2840,  # 日本
                "language_code": "ja",  # 日本語
                "depth": 3,  # 深さ（1-3）
                "include_serp_info": False,
                "include_subdomains": False
            }]
            
            async with session.post(endpoint, json=payload) as response:
                if response.status == 200:
                    data = await response.json()
                    
                    if data.get("status_code") == 20000:  # 成功
                        tasks = data.get("tasks", [])
                        suggestions = []
                        
                        for task in tasks:
                            if task.get("result"):
                                for result in task["result"]:
                                    # キーワードサジェストを抽出
                                    if "keyword" in result:
                                        suggestions.append(result["keyword"])
                                    
                                    # 関連キーワードも抽出
                                    if "related_keywords" in result:
                                        for related in result["related_keywords"]:
                                            if "keyword" in related:
                                                suggestions.append(related["keyword"])
                        
                        # 重複除去
                        unique_suggestions = list(set(suggestions))
                        print(f"      -> Data for SEO Google: {len(unique_suggestions)}個")
                        return unique_suggestions
                    else:
                        print(f"      -> Data for SEO API エラー: {data.get('status_message', 'Unknown error')}")
                        return []
                else:
                    print(f"      -> HTTP エラー: {response.status}")
                    return []
                    
        except Exception as e:
            print(f"      -> Google Suggest エラー: {e}")
            return []
    
    async def _get_yahoo_suggestions(self, keyword: str) -> List[str]:
        """Data for SEO Yahoo Suggest APIからサジェストを取得"""
        try:
            session = await self._get_session()
            
            # Yahoo Suggest APIのエンドポイント
            endpoint = f"{self.base_url}/keywords_data/yahoo/keyword_suggestions"
            
            # 正しいペイロード形式（配列）
            payload = [{
                "keyword": keyword,
                "location_code": 2840,  # 日本
                "language_code": "ja",  # 日本語
                "depth": 3,  # 深さ（1-3）
                "include_serp_info": False
            }]
            
            async with session.post(endpoint, json=payload) as response:
                if response.status == 200:
                    data = await response.json()
                    
                    if data.get("status_code") == 20000:  # 成功
                        tasks = data.get("tasks", [])
                        suggestions = []
                        
                        for task in tasks:
                            if task.get("result"):
                                for result in task["result"]:
                                    # キーワードサジェストを抽出
                                    if "keyword" in result:
                                        suggestions.append(result["keyword"])
                                    
                                    # 関連キーワードも抽出
                                    if "related_keywords" in result:
                                        for related in result["related_keywords"]:
                                            if "keyword" in related:
                                                suggestions.append(related["keyword"])
                        
                        # 重複除去
                        unique_suggestions = list(set(suggestions))
                        print(f"      -> Data for SEO Yahoo: {len(unique_suggestions)}個")
                        return unique_suggestions
                    else:
                        print(f"      -> Data for SEO API エラー: {data.get('status_message', 'Unknown error')}")
                        return []
                else:
                    print(f"      -> HTTP エラー: {response.status}")
                    return []
                    
        except Exception as e:
            print(f"      -> Yahoo Suggest エラー: {e}")
            return []
    
    async def _get_related_searches(self, keyword: str) -> List[str]:
        """Data for SEO Related Searches APIから関連検索を取得"""
        try:
            session = await self._get_session()
            
            # Related Searches APIのエンドポイント
            endpoint = f"{self.base_url}/serp/google/organic/live/regular"
            
            # 正しいペイロード形式（配列）
            payload = [{
                "keyword": keyword,
                "location_code": 2840,  # 日本
                "language_code": "ja",  # 日本語
                "depth": 1,
                "include_serp_info": True
            }]
            
            async with session.post(endpoint, json=payload) as response:
                if response.status == 200:
                    data = await response.json()
                    
                    if data.get("status_code") == 20000:  # 成功
                        tasks = data.get("tasks", [])
                        suggestions = []
                        
                        for task in tasks:
                            if task.get("result"):
                                for result in task["result"]:
                                    # 関連検索を抽出
                                    if "related_searches" in result:
                                        for related in result["related_searches"]:
                                            if "keyword" in related:
                                                suggestions.append(related["keyword"])
                                    
                                    # People Also Askも抽出
                                    if "people_also_ask" in result:
                                        for paa in result["people_also_ask"]:
                                            if "question" in paa:
                                                suggestions.append(paa["question"])
                        
                        # 重複除去
                        unique_suggestions = list(set(suggestions))
                        print(f"      -> Data for SEO Related Searches: {len(unique_suggestions)}個")
                        return unique_suggestions
                    else:
                        print(f"      -> Data for SEO API エラー: {data.get('status_message', 'Unknown error')}")
                        return []
                else:
                    print(f"      -> HTTP エラー: {response.status}")
                    return []
                    
        except Exception as e:
            print(f"      -> Related Searches エラー: {e}")
            return []
    
    async def _collect_suggestions_with_retry(self, keyword: str, method: str) -> List[str]:
        """リトライ機能付きでサジェストを収集"""
        for attempt in range(self.max_retries):
            try:
                if method == "google":
                    suggestions = await self._get_google_suggestions(keyword)
                elif method == "yahoo":
                    suggestions = await self._get_yahoo_suggestions(keyword)
                else:  # related_searches
                    suggestions = await self._get_related_searches(keyword)
                
                if suggestions:
                    return suggestions
                
                print(f"    [{method.capitalize()}] 試行 {attempt + 1}/{self.max_retries}: サジェストが見つかりませんでした")
                
            except Exception as e:
                print(f"    [{method.capitalize()}] 試行 {attempt + 1}/{self.max_retries}: エラー - {e}")
            
            if attempt < self.max_retries - 1:
                await self._random_delay()
        
        return []
    
    async def collect_all_suggestions(self, main_keyword: str) -> Dict[str, List[str]]:
        """メインキーワードから100以上のサジェストを単回APIで収集"""
        print(f"\n=== メインキーワード「{main_keyword}」のサジェスト収集開始 ===")
        print("3つのAPIから同時にサジェストを収集します（深掘りなし）")
        
        suggestions = []
        
        # Google Suggestから収集
        print(f"  [Google Suggest] 「{main_keyword}」のサジェストを収集中...")
        google_suggestions = await self._collect_suggestions_with_retry(main_keyword, "google")
        suggestions.extend(google_suggestions)
        self.suggestion_sources["google_suggest"] = google_suggestions
        
        await self._random_delay()
        
        # Yahoo Suggestから収集
        print(f"  [Yahoo Suggest] 「{main_keyword}」のサジェストを収集中...")
        yahoo_suggestions = await self._collect_suggestions_with_retry(main_keyword, "yahoo")
        suggestions.extend(yahoo_suggestions)
        self.suggestion_sources["yahoo_suggest"] = yahoo_suggestions
        
        await self._random_delay()
        
        # Related Searchesから収集
        print(f"  [Related Searches] 「{main_keyword}」の関連検索を収集中...")
        related_suggestions = await self._collect_suggestions_with_retry(main_keyword, "related_searches")
        suggestions.extend(related_suggestions)
        self.suggestion_sources["related_searches"] = related_suggestions
        
        # 重複除去
        unique_suggestions = list(set(suggestions))
        self.collected_suggestions.update(unique_suggestions)
        
        # 結果の整理
        final_suggestions = sorted(list(self.collected_suggestions))
        
        result = {
            "main_keyword": main_keyword,
            "total_suggestions": len(final_suggestions),
            "suggestions": final_suggestions,
            "sources": self.suggestion_sources,
            "collection_stats": {
                "google_suggest": len(google_suggestions),
                "yahoo_suggest": len(yahoo_suggestions),
                "related_searches": len(related_suggestions),
                "unique_total": len(final_suggestions)
            }
        }
        
        print(f"\n=== 収集完了 ===")
        print(f"メインキーワード: {main_keyword}")
        print(f"総サジェスト数: {len(final_suggestions)}個")
        print(f"Google Suggest: {len(google_suggestions)}個")
        print(f"Yahoo Suggest: {len(yahoo_suggestions)}個")
        print(f"Related Searches: {len(related_suggestions)}個")
        
        if len(final_suggestions) >= 100:
            print(f"🎯 目標達成！ {len(final_suggestions)}個のサジェストを収集しました")
        else:
            print(f"⚠️  目標の100個には達しませんでした（{len(final_suggestions)}個）")
        
        return result
    
    def get_suggestions_for_sub_keyword_creation(self) -> List[str]:
        """サブキーワード作成用のサジェストリストを取得"""
        suggestions = list(self.collected_suggestions)
        
        # サジェストの品質フィルタリング
        filtered_suggestions = []
        for suggestion in suggestions:
            # 短すぎる、長すぎるものを除外
            if 2 <= len(suggestion) <= 50:
                # 特殊文字が多すぎるものを除外
                special_char_ratio = sum(1 for c in suggestion if not c.isalnum() and not c.isspace()) / len(suggestion)
                if special_char_ratio <= 0.3:
                    filtered_suggestions.append(suggestion)
        
        print(f"[フィルタリング] {len(suggestions)}個 → {len(filtered_suggestions)}個の高品質サジェスト")
        return filtered_suggestions
    
    async def close(self):
        """セッションを閉じる"""
        if self.session and not self.session.closed:
            await self.session.close()
