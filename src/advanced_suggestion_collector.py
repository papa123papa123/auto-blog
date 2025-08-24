# src/advanced_suggestion_collector.py

import asyncio
import random
import time
from typing import List, Set, Dict, Optional
from urllib.parse import quote_plus
from playwright.async_api import Browser, Page
from playwright_stealth.stealth import Stealth


class AdvancedSuggestionCollector:
    """
    メインKWから100以上のサジェストを収集するクラス
    YahooとGoogleの両方から、ページ最下部のサジェストを段階的に収集
    ランダムなレイテンシーでレート制限を回避
    """
    
    def __init__(self, browser: Browser):
        self.browser = browser
        self.stealth = Stealth()
        self.collected_suggestions: Set[str] = set()
        self.suggestion_sources: Dict[str, List[str]] = {}
        
        # レート制限回避のための設定
        self.min_delay = 2.0  # 最小待機時間（秒）
        self.max_delay = 5.0  # 最大待機時間（秒）
        self.max_retries = 3   # 最大リトライ回数
        
        print("[OK] AdvancedSuggestionCollectorの初期化に成功しました")
    
    async def _get_stealth_page(self) -> Page:
        """ステルス機能付きのページを作成"""
        page = await self.browser.new_page()
        await self.stealth.apply_stealth_async(page)
        return page
    
    async def _random_delay(self):
        """ランダムな待機時間でレート制限を回避"""
        delay = random.uniform(self.min_delay, self.max_delay)
        print(f"  -> {delay:.1f}秒待機中...")
        await asyncio.sleep(delay)
    
    async def _get_google_suggestions(self, keyword: str, page: Page) -> List[str]:
        """Googleからサジェストを取得（ページ最下部の「他の人はこちらも検索」と中段の「関連する質問」）"""
        try:
            # Google検索ページにアクセス
            search_url = f"https://www.google.com/search?q={quote_plus(keyword)}&hl=ja&gl=jp"
            await page.goto(search_url, wait_until="domcontentloaded", timeout=30000)
            
            suggestions = []
            
            # 1. 中段の「関連する質問」（PAA）を取得
            print("      -> PAA（関連する質問）を収集中...")
            paa_selectors = [
                "div[jsname='NkuQd'] span",
                ".related-question-pair span",
                "[data-ved] .wDYxhc span",
                ".wDYxhc .Lt3Tzc"
            ]
            
            for selector in paa_selectors:
                try:
                    elements = await page.query_selector_all(selector)
                    for element in elements:
                        text = await element.inner_text()
                        if text and len(text.strip()) > 1 and text.strip() != keyword:
                            suggestions.append(text.strip())
                except Exception:
                    continue
            
            # PAAの「もっと見る」ボタンをクリックして追加の質問を表示
            try:
                more_questions_selectors = [
                    "span:has-text('もっと見る')",
                    "span:has-text('さらに表示')",
                    ".wDYxhc button",
                    "[jsname='NkuQd'] button"
                ]
                
                for selector in more_questions_selectors:
                    try:
                        more_button = await page.query_selector(selector)
                        if more_button:
                            await more_button.click()
                            await asyncio.sleep(random.uniform(1.0, 2.0))
                            print("      -> PAAの「もっと見る」をクリックして追加質問を表示")
                            break
                    except Exception:
                        continue
                
                # 追加表示されたPAAも取得
                for selector in paa_selectors:
                    try:
                        elements = await page.query_selector_all(selector)
                        for element in elements:
                            text = await element.inner_text()
                            if text and len(text.strip()) > 1 and text.strip() != keyword:
                                suggestions.append(text.strip())
                    except Exception:
                        continue
                        
            except Exception as e:
                print(f"      -> PAA拡張でエラー: {e}")
            
            # 2. ページ最下部までスクロール
            await page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
            await asyncio.sleep(random.uniform(1.0, 2.0))
            
            # 3. ページ最下部の「他の人はこちらも検索」を取得
            print("      -> 「他の人はこちらも検索」を収集中...")
            related_search_selectors = [
                "div[data-ved] a[href*='search']",
                ".k8XOCe a",
                ".BNeawe a",
                "[data-ved] a[ping]",
                ".brs_col a",
                ".commercial-unit-desktop-top a"
            ]
            
            for selector in related_search_selectors:
                try:
                    elements = await page.query_selector_all(selector)
                    for element in elements:
                        text = await element.inner_text()
                        if text and len(text.strip()) > 1 and text.strip() != keyword:
                            suggestions.append(text.strip())
                except Exception:
                    continue
            
            # 重複除去
            unique_suggestions = list(set(suggestions))
            print(f"    [Google] {len(unique_suggestions)}個のサジェストを取得（PAA: {len([s for s in suggestions if s in suggestions[:len(suggestions)//2]])}個、関連検索: {len([s for s in suggestions if s not in suggestions[:len(suggestions)//2]])}個）")
            
            return unique_suggestions
            
        except Exception as e:
            print(f"    [Google] エラー: {e}")
            return []
    
    async def _get_yahoo_suggestions(self, keyword: str, page: Page) -> List[str]:
        """Yahooからサジェストを取得（ページ最下部の「他の人はこちらも検索」と中段の「関連する質問」）"""
        try:
            # Yahoo検索ページにアクセス
            search_url = f"https://search.yahoo.co.jp/search?p={quote_plus(keyword)}&ei=UTF-8"
            await page.goto(search_url, wait_until="domcontentloaded", timeout=30000)
            
            suggestions = []
            
            # 1. 中段の「関連する質問」（PAA）を取得
            print("      -> PAA（関連する質問）を収集中...")
            paa_selectors = [
                ".Algo .sw-Card__title",
                ".sw-Card__title",
                ".Algo .sw-Card__content",
                ".sw-Card__content",
                ".Algo .sw-Card__description",
                ".sw-Card__description"
            ]
            
            for selector in paa_selectors:
                try:
                    elements = await page.query_selector_all(selector)
                    for element in elements:
                        text = await element.inner_text()
                        if text and len(text.strip()) > 1 and text.strip() != keyword:
                            suggestions.append(text.strip())
                except Exception:
                    continue
            
            # 2. ページ最下部までスクロール
            await page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
            await asyncio.sleep(random.uniform(1.0, 2.0))
            
            # 3. ページ最下部の「他の人はこちらも検索」を取得
            print("      -> 「他の人はこちらも検索」を収集中...")
            related_search_selectors = [
                ".Algo .sw-Card__title a",
                ".sw-Card__title a",
                ".Algo a[href*='search']",
                ".sw-Card a",
                ".Algo .sw-Card__link",
                ".sw-Card__link"
            ]
            
            for selector in related_search_selectors:
                try:
                    elements = await page.query_selector_all(selector)
                    for element in elements:
                        text = await element.inner_text()
                        if text and len(text.strip()) > 1 and text.strip() != keyword:
                            suggestions.append(text.strip())
                except Exception:
                    continue
            
            # 重複除去
            unique_suggestions = list(set(suggestions))
            print(f"    [Yahoo] {len(unique_suggestions)}個のサジェストを取得（PAA: {len([s for s in suggestions if s in suggestions[:len(suggestions)//2]])}個、関連検索: {len([s for s in suggestions if s not in suggestions[:len(suggestions)//2]])}個）")
            
            return unique_suggestions
            
        except Exception as e:
            print(f"    [Yahoo] エラー: {e}")
            return []
    
    async def _collect_suggestions_with_retry(self, keyword: str, engine: str, page: Page) -> List[str]:
        """リトライ機能付きでサジェストを収集"""
        for attempt in range(self.max_retries):
            try:
                if engine == "google":
                    suggestions = await self._get_google_suggestions(keyword, page)
                else:  # yahoo
                    suggestions = await self._get_yahoo_suggestions(keyword, page)
                
                if suggestions:
                    return suggestions
                
                print(f"    [{engine.capitalize()}] 試行 {attempt + 1}/{self.max_retries}: サジェストが見つかりませんでした")
                
            except Exception as e:
                print(f"    [{engine.capitalize()}] 試行 {attempt + 1}/{self.max_retries}: エラー - {e}")
            
            if attempt < self.max_retries - 1:
                await self._random_delay()
        
        return []
    
    async def collect_main_keyword_suggestions(self, main_keyword: str) -> List[str]:
        """メインキーワードからサジェストを収集（第1段階）"""
        print(f"\n--- 第1段階: メインキーワード「{main_keyword}」のサジェスト収集 ---")
        
        page = await self._get_stealth_page()
        try:
            suggestions = []
            
            # Googleから収集
            print(f"  [Google] 「{main_keyword}」のサジェストを収集中...")
            google_suggestions = await self._collect_suggestions_with_retry(main_keyword, "google", page)
            suggestions.extend(google_suggestions)
            self.suggestion_sources["google_main"] = google_suggestions
            
            await self._random_delay()
            
            # Yahooから収集
            print(f"  [Yahoo] 「{main_keyword}」のサジェストを収集中...")
            yahoo_suggestions = await self._collect_suggestions_with_retry(main_keyword, "yahoo", page)
            suggestions.extend(yahoo_suggestions)
            self.suggestion_sources["yahoo_main"] = yahoo_suggestions
            
            # 重複除去
            unique_suggestions = list(set(suggestions))
            self.collected_suggestions.update(unique_suggestions)
            
            print(f"[OK] 第1段階完了: {len(unique_suggestions)}個のユニークなサジェストを収集")
            return unique_suggestions
            
        finally:
            await page.close()
    
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
            
            page = await self._get_stealth_page()
            try:
                secondary_suggestions = []
                
                # Googleから収集
                google_suggestions = await self._collect_suggestions_with_retry(suggestion, "google", page)
                secondary_suggestions.extend(google_suggestions)
                
                await self._random_delay()
                
                # Yahooから収集
                yahoo_suggestions = await self._collect_suggestions_with_retry(suggestion, "yahoo", page)
                secondary_suggestions.extend(yahoo_suggestions)
                
                # 新しいサジェストのみを追加
                new_suggestions = [s for s in secondary_suggestions if s not in self.collected_suggestions]
                self.collected_suggestions.update(new_suggestions)
                
                print(f"    -> {len(new_suggestions)}個の新しいサジェストを発見（累計: {len(self.collected_suggestions)}個）")
                
                # レート制限回避のための待機
                await self._random_delay()
                
            finally:
                await page.close()
            
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
