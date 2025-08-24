# src/api_based_suggestion_collector.py

import asyncio
import random
import time
import json
from typing import List, Set, Dict, Optional
from urllib.parse import quote_plus
import aiohttp
import requests


class ApiBasedSuggestionCollector:
    """
    APIベースでメインKWから100以上のサジェストを収集するクラス
    Google Suggest APIとYahoo Suggest APIを使用
    ランダムなレイテンシーでレート制限を回避
    """
    
    def __init__(self):
        self.collected_suggestions: Set[str] = set()
        self.suggestion_sources: Dict[str, List[str]] = {}
        
        # レート制限回避のための設定
        self.min_delay = 1.0  # 最小待機時間（秒）
        self.max_delay = 3.0  # 最大待機時間（秒）
        self.max_retries = 3   # 最大リトライ回数
        
        # セッション管理
        self.session = None
        
        print("[OK] ApiBasedSuggestionCollectorの初期化に成功しました")
    
    async def _get_session(self) -> aiohttp.ClientSession:
        """aiohttpセッションを取得"""
        if self.session is None or self.session.closed:
            self.session = aiohttp.ClientSession(
                timeout=aiohttp.ClientTimeout(total=30),
                headers={
                    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36'
                }
            )
        return self.session
    
    async def _random_delay(self):
        """ランダムな待機時間でレート制限を回避"""
        delay = random.uniform(self.min_delay, self.max_delay)
        print(f"  -> {delay:.1f}秒待機中...")
        await asyncio.sleep(delay)
    
    async def _get_google_suggestions(self, keyword: str) -> List[str]:
        """Google Suggest APIからサジェストを取得"""
        try:
            session = await self._get_session()
            
            # Google Suggest APIの複数のエンドポイントを試行
            endpoints = [
                f"https://suggestqueries.google.com/complete/search?client=firefox&q={quote_plus(keyword)}",
                f"https://suggestqueries.google.com/complete/search?client=chrome&q={quote_plus(keyword)}",
                f"https://suggestqueries.google.com/complete/search?client=opera&q={quote_plus(keyword)}",
                f"https://suggestqueries.google.com/complete/search?client=ie&q={quote_plus(keyword)}"
            ]
            
            suggestions = []
            
            for endpoint in endpoints:
                try:
                    async with session.get(endpoint) as response:
                        if response.status == 200:
                            data = await response.json()
                            if isinstance(data, list) and len(data) > 1:
                                # Google Suggest APIの形式: [query, [suggestions], ...]
                                keyword_suggestions = data[1]
                                if isinstance(keyword_suggestions, list):
                                    suggestions.extend(keyword_suggestions)
                                    print(f"      -> Google API ({endpoint.split('client=')[1].split('&')[0]}): {len(keyword_suggestions)}個")
                                    break
                except Exception as e:
                    print(f"      -> Google API エンドポイント {endpoint} でエラー: {e}")
                    continue
            
            # 重複除去
            unique_suggestions = list(set(suggestions))
            print(f"    [Google] {len(unique_suggestions)}個のサジェストを取得")
            
            return unique_suggestions
            
        except Exception as e:
            print(f"    [Google] エラー: {e}")
            return []
    
    async def _get_yahoo_suggestions(self, keyword: str) -> List[str]:
        """Yahoo Suggest APIからサジェストを取得"""
        try:
            session = await self._get_session()
            
            # Yahoo Suggest APIのエンドポイント
            endpoints = [
                f"https://search.yahoo.co.jp/sugg/ff?command={quote_plus(keyword)}",
                f"https://search.yahoo.co.jp/sugg/ff?command={quote_plus(keyword)}&ei=UTF-8",
                f"https://search.yahoo.co.jp/sugg/ff?command={quote_plus(keyword)}&output=json"
            ]
            
            suggestions = []
            
            for endpoint in endpoints:
                try:
                    async with session.get(endpoint) as response:
                        if response.status == 200:
                            data = await response.json()
                            
                            # Yahoo Suggest APIの形式を解析
                            if isinstance(data, dict) and 'gossip' in data:
                                # 新しい形式
                                for item in data['gossip'].get('results', []):
                                    if 'key' in item:
                                        suggestions.append(item['key'])
                            elif isinstance(data, list) and len(data) > 0:
                                # 古い形式
                                for item in data:
                                    if isinstance(item, str):
                                        suggestions.append(item)
                                    elif isinstance(item, dict) and 'key' in item:
                                        suggestions.append(item['key'])
                            
                            if suggestions:
                                print(f"      -> Yahoo API: {len(suggestions)}個")
                                break
                                
                except Exception as e:
                    print(f"      -> Yahoo API エンドポイント {endpoint} でエラー: {e}")
                    continue
            
            # 重複除去
            unique_suggestions = list(set(suggestions))
            print(f"    [Yahoo] {len(unique_suggestions)}個のサジェストを取得")
            
            return unique_suggestions
            
        except Exception as e:
            print(f"    [Yahoo] エラー: {e}")
            return []
    
    def _get_google_suggestions_sync(self, keyword: str) -> List[str]:
        """同期版Google Suggest API（フォールバック用）"""
        try:
            endpoints = [
                f"https://suggestqueries.google.com/complete/search?client=firefox&q={quote_plus(keyword)}",
                f"https://suggestqueries.google.com/complete/search?client=chrome&q={quote_plus(keyword)}"
            ]
            
            suggestions = []
            
            for endpoint in endpoints:
                try:
                    response = requests.get(endpoint, timeout=10)
                    if response.status_code == 200:
                        data = response.json()
                        if isinstance(data, list) and len(data) > 1:
                            keyword_suggestions = data[1]
                            if isinstance(keyword_suggestions, list):
                                suggestions.extend(keyword_suggestions)
                                break
                except Exception:
                    continue
            
            return list(set(suggestions))
            
        except Exception:
            return []
    
    def _get_yahoo_suggestions_sync(self, keyword: str) -> List[str]:
        """同期版Yahoo Suggest API（フォールバック用）"""
        try:
            endpoint = f"https://search.yahoo.co.jp/sugg/ff?command={quote_plus(keyword)}"
            response = requests.get(endpoint, timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                suggestions = []
                
                if isinstance(data, dict) and 'gossip' in data:
                    for item in data['gossip'].get('results', []):
                        if 'key' in item:
                            suggestions.append(item['key'])
                elif isinstance(data, list):
                    for item in data:
                        if isinstance(item, str):
                            suggestions.append(item)
                        elif isinstance(item, dict) and 'key' in item:
                            suggestions.append(item['key'])
                
                return list(set(suggestions))
            
        except Exception:
            pass
        
        return []
    
    async def _collect_suggestions_with_retry(self, keyword: str, engine: str) -> List[str]:
        """リトライ機能付きでサジェストを収集"""
        for attempt in range(self.max_retries):
            try:
                if engine == "google":
                    suggestions = await self._get_google_suggestions(keyword)
                else:  # yahoo
                    suggestions = await self._get_yahoo_suggestions(keyword)
                
                if suggestions:
                    return suggestions
                
                print(f"    [{engine.capitalize()}] 試行 {attempt + 1}/{self.max_retries}: サジェストが見つかりませんでした")
                
            except Exception as e:
                print(f"    [{engine.capitalize()}] 試行 {attempt + 1}/{self.max_retries}: エラー - {e}")
            
            if attempt < self.max_retries - 1:
                await self._random_delay()
        
        # 非同期が失敗した場合、同期版を試行
        print(f"    [{engine.capitalize()}] 非同期版が失敗、同期版を試行...")
        try:
            if engine == "google":
                return self._get_google_suggestions_sync(keyword)
            else:
                return self._get_yahoo_suggestions_sync(keyword)
        except Exception as e:
            print(f"    [{engine.capitalize()}] 同期版も失敗: {e}")
            return []
    
    async def collect_main_keyword_suggestions(self, main_keyword: str) -> List[str]:
        """メインキーワードからサジェストを収集（第1段階）"""
        print(f"\n--- 第1段階: メインキーワード「{main_keyword}」のサジェスト収集 ---")
        
        suggestions = []
        
        # Googleから収集
        print(f"  [Google] 「{main_keyword}」のサジェストを収集中...")
        google_suggestions = await self._collect_suggestions_with_retry(main_keyword, "google")
        suggestions.extend(google_suggestions)
        self.suggestion_sources["google_main"] = google_suggestions
        
        await self._random_delay()
        
        # Yahooから収集
        print(f"  [Yahoo] 「{main_keyword}」のサジェストを収集中...")
        yahoo_suggestions = await self._collect_suggestions_with_retry(main_keyword, "yahoo")
        suggestions.extend(yahoo_suggestions)
        self.suggestion_sources["yahoo_main"] = yahoo_suggestions
        
        # 重複除去
        unique_suggestions = list(set(suggestions))
        self.collected_suggestions.update(unique_suggestions)
        
        print(f"[OK] 第1段階完了: {len(unique_suggestions)}個のユニークなサジェストを収集")
        return unique_suggestions
    
    async def collect_secondary_suggestions(self, primary_suggestions: List[str]) -> List[str]:
        """第1段階のサジェストから第2段階のサジェストを収集"""
        print(f"\n--- 第2段階: {len(primary_suggestions)}個のサジェストから深掘り収集 ---")
        
        # 第1段階のサジェストをシャッフルして処理順序をランダム化
        shuffled_suggestions = primary_suggestions.copy()
        random.shuffle(shuffled_suggestions)
        
        # 目標: 100個以上のサジェストを収集
        target_count = 100
        processed_count = 0
        
        for suggestion in shuffled_suggestions:
            if len(self.collected_suggestions) >= target_count:
                print(f"[目標達成] {target_count}個以上のサジェストを収集しました")
                break
            
            print(f"  [{processed_count + 1}/{len(shuffled_suggestions)}] 「{suggestion}」から深掘り中...")
            
            secondary_suggestions = []
            
            # Googleから収集
            google_suggestions = await self._collect_suggestions_with_retry(suggestion, "google")
            secondary_suggestions.extend(google_suggestions)
            
            await self._random_delay()
            
            # Yahooから収集
            yahoo_suggestions = await self._collect_suggestions_with_retry(suggestion, "yahoo")
            secondary_suggestions.extend(yahoo_suggestions)
            
            # 新しいサジェストのみを追加
            new_suggestions = [s for s in secondary_suggestions if s not in self.collected_suggestions]
            self.collected_suggestions.update(new_suggestions)
            
            print(f"    -> {len(new_suggestions)}個の新しいサジェストを発見（累計: {len(self.collected_suggestions)}個）")
            
            # レート制限回避のための待機
            await self._random_delay()
            
            processed_count += 1
            
            # 進捗表示
            if processed_count % 10 == 0:
                print(f"  [進捗] {processed_count}/{len(shuffled_suggestions)} 完了、累計サジェスト: {len(self.collected_suggestions)}個")
        
        return list(self.collected_suggestions)
    
    async def collect_all_suggestions(self, main_keyword: str) -> Dict[str, List[str]]:
        """メインキーワードから100以上のサジェストを完全収集"""
        print(f"\n=== メインキーワード「{main_keyword}」のサジェスト完全収集を開始 ===")
        
        # 第1段階: メインキーワードからサジェスト収集
        primary_suggestions = await self.collect_main_keyword_suggestions(main_keyword)
        
        if not primary_suggestions:
            print("[警告] 第1段階でサジェストが取得できませんでした")
            return {"main_keyword": main_keyword, "suggestions": [], "sources": self.suggestion_sources}
        
        # 第2段階: 深掘り収集
        all_suggestions = await self.collect_secondary_suggestions(primary_suggestions)
        
        # 最終結果の整理
        final_suggestions = sorted(list(self.collected_suggestions))
        
        result = {
            "main_keyword": main_keyword,
            "total_suggestions": len(final_suggestions),
            "suggestions": final_suggestions,
            "sources": self.suggestion_sources,
            "collection_stats": {
                "primary_stage": len(primary_suggestions),
                "secondary_stage": len(final_suggestions) - len(primary_suggestions),
                "unique_ratio": len(final_suggestions) / max(len(primary_suggestions), 1)
            }
        }
        
        print(f"\n=== 収集完了 ===")
        print(f"メインキーワード: {main_keyword}")
        print(f"総サジェスト数: {len(final_suggestions)}個")
        print(f"第1段階: {len(primary_suggestions)}個")
        print(f"第2段階: {len(final_suggestions) - len(primary_suggestions)}個")
        print(f"ユニーク率: {result['collection_stats']['unique_ratio']:.2f}")
        
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
