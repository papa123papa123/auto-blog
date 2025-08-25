#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Data for SEOを使用したGoogleサジェスト収集 - 全自動版
ローカルアルゴリズムでキーワードを自動選定し、API呼び出しを最小限に抑える
"""

import asyncio
import httpx
import json
import os
from datetime import datetime
from typing import List, Dict, Any, Tuple
from dotenv import load_dotenv

# 環境変数の読み込み
from pathlib import Path
load_dotenv(dotenv_path=Path(__file__).parent / ".env")

class GoogleSuggestionCollector:
    def __init__(self):
        self.login = os.getenv('DATAFORSEO_LOGIN')
        self.password = os.getenv('DATAFORSEO_PASSWORD')
        self.language_code = os.getenv('DATAFORSEO_LANGUAGE_CODE', 'ja')  # 日本語
        self.location_code = int(os.getenv('DATAFORSEO_LOCATION_CODE', '2392'))  # 日本
        
        if not self.login or not self.password:
            raise ValueError("DATAFORSEO_LOGIN または DATAFORSEO_PASSWORD が設定されていません")
        
        self.base_url = "https://api.dataforseo.com/v3"
        self.collected_keywords = set()
        
    async def get_autocomplete_batch(self, keyword: str) -> List[str]:
        """複数のカーソルでGoogle Autocompleteを取得"""
        print(f"🔍 キーワード「{keyword}」のAutocomplete取得中...")
        
        # より多くのカーソルを使用してサジェスト数を増やす
        cursors = [0, 1, 2, 3, 4, 5, 6, 7, 8, 9]
        all_suggestions = []
        
        async with httpx.AsyncClient(timeout=120) as client:
            tasks = []
            for cursor in cursors:
                task = self._get_autocomplete_single(client, keyword, cursor)
                tasks.append(task)
            
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            for i, result in enumerate(results):
                if isinstance(result, Exception):
                    print(f"⚠️ カーソル {cursors[i]} でエラー: {result}")
                elif result:
                    all_suggestions.extend(result)
        
        # 重複除去
        unique_suggestions = list(set(all_suggestions))
        print(f"✅ Autocomplete取得完了: {len(unique_suggestions)}件")
        return unique_suggestions
    
    async def _get_autocomplete_single(self, client: httpx.AsyncClient, keyword: str, cursor: int) -> List[str]:
        """単一カーソルでAutocompleteを取得"""
        url = f"{self.base_url}/serp/google/autocomplete/live/advanced"
        
        payload = [{
            "language_code": self.language_code,
            "location_code": self.location_code,
            "keyword": keyword,
            "client": "chrome-omni",
            "cursor_pointer": cursor
        }]
        
        try:
            response = await client.post(url, json=payload, auth=(self.login, self.password))
            response.raise_for_status()
            data = response.json()
            
            if data.get("status_code") == 20000:
                suggestions = []
                print(f"🔍 カーソル {cursor} のレスポンス解析中...")
                for task in data.get("tasks", []):
                    for result in task.get("result", []):
                        for item in result.get("items", []):
                            suggestion = item.get("suggestion")
                            if suggestion:
                                suggestions.append(suggestion)
                                print(f"   ✅ サジェスト: {suggestion}")
                print(f"   📊 カーソル {cursor} で {len(suggestions)}件取得")
                return suggestions
            else:
                print(f"⚠️ カーソル {cursor} でAPIエラー: {data.get('status_message', 'Unknown error')}")
                return []
                
        except Exception as e:
            print(f"⚠️ カーソル {cursor} で通信エラー: {e}")
            return []
    
    async def get_related_searches_and_paa(self, keywords: List[str]) -> Tuple[List[str], List[str]]:
        """複数キーワードのRelated SearchesとPeople Also Askを一括取得"""
        print(f"🔍 {len(keywords)}個のキーワードからRelated Searches + PAA取得中...")
        
        url = f"{self.base_url}/serp/google/organic/live/advanced"
        
        # バッチ処理用のペイロード作成
        payload = [
            {
                "language_code": self.language_code,
                "location_code": self.location_code,
                "keyword": keyword,
                "depth": 2,
                "include_serp_info": True
            }
            for keyword in keywords
        ]
        
        try:
            async with httpx.AsyncClient(timeout=120) as client:
                response = await client.post(url, json=payload, auth=(self.login, self.password))
                response.raise_for_status()
                data = response.json()
                
                all_related_searches = []
                all_paa_questions = []
                
                for task in data.get("tasks", []):
                    if task.get("status_code") == 20000:
                        for result in task.get("result", []):
                            # Related Searchesの取得
                            for item in result.get("items", []):
                                if item.get("type") == "related_searches":
                                    if "items" in item and isinstance(item["items"], list):
                                        for rel_item in item["items"]:
                                            if isinstance(rel_item, str):
                                                all_related_searches.append(rel_item)
                                            elif isinstance(rel_item, dict):
                                                suggestion = rel_item.get("text") or rel_item.get("suggestion")
                                                if suggestion:
                                                    all_related_searches.append(suggestion)
                            
                            # People Also Askの取得
                            for item in result.get("items", []):
                                if item.get("type") == "people_also_ask":
                                    if "items" in item and isinstance(item["items"], list):
                                        for paa_item in item["items"]:
                                            if isinstance(paa_item, dict):
                                                question = paa_item.get("question")
                                                if question:
                                                    all_paa_questions.append(question)
                
                # 重複除去
                unique_related = list(set(all_related_searches))
                unique_paa = list(set(all_paa_questions))
                
                print(f"✅ Related Searches + PAA取得完了:")
                print(f"   - Related Searches: {len(unique_related)}件")
                print(f"   - People Also Ask: {len(unique_paa)}件")
                
                return unique_related, unique_paa
                
        except Exception as e:
            print(f"❌ Related Searches + PAA取得エラー: {e}")
            import traceback
            traceback.print_exc()
            return [], []
    
    def analyze_and_select_keywords(self, keywords: List[str], target_count: int = 5) -> List[str]:
        """ローカルアルゴリズムでキーワードを自動選定"""
        print(f"🤖 {len(keywords)}個のキーワードを自動分析・選定中...")
        
        # キーワードスコアリング
        scored_keywords = []
        for keyword in keywords:
            score = 0
            
            # 長さスコア（適度な長さを好む）
            length = len(keyword)
            if 5 <= length <= 20:
                score += 3
            elif 3 <= length <= 25:
                score += 2
            else:
                score += 1
            
            # 関連性スコア（メインキーワードとの関連性）
            main_keywords = ["夏", "おすすめ", "お酒"]
            relevance_count = sum(1 for main_kw in main_keywords if main_kw in keyword)
            score += relevance_count * 2
            
            # 検索意図スコア
            intent_indicators = ["おすすめ", "ランキング", "比較", "選び方", "飲み方", "作り方"]
            if any(indicator in keyword for indicator in intent_indicators):
                score += 2
            
            # 季節性・トレンド性スコア
            seasonal_terms = ["夏", "暑い", "冷たい", "ひやおろし"]
            if any(term in keyword for term in seasonal_terms):
                score += 2
            
            # 具体性スコア（具体的な内容を含む）
            specific_terms = ["カクテル", "日本酒", "ビール", "ワイン", "焼酎"]
            if any(term in keyword for term in specific_terms):
                score += 1
            
            scored_keywords.append((keyword, score))
        
        # スコアでソート
        scored_keywords.sort(key=lambda x: x[1], reverse=True)
        
        # 上位キーワードを選択
        selected = [kw for kw, score in scored_keywords[:target_count]]
        
        print(f"✅ 自動選定完了: 上位{len(selected)}個を選択")
        for i, keyword in enumerate(selected, 1):
            score = next(score for kw, score in scored_keywords if kw == keyword)
            print(f"   {i}. {keyword} (スコア: {score})")
        
        return selected
    
    async def collect_suggestions_automated(self, main_keyword: str) -> Dict[str, Any]:
        """全自動でサジェスト収集を実行"""
        print(f"🚀 メインキーワード「{main_keyword}」から全自動サジェスト収集開始")
        print("=" * 60)
        
        # ステップ1: メインキーワードのAutocomplete取得
        print("\n📊 ステップ1: メインキーワードのAutocomplete取得")
        autocomplete_suggestions = await self.get_autocomplete_batch(main_keyword)
        
        if not autocomplete_suggestions:
            print("❌ Autocompleteが取得できませんでした")
            return {"error": "Autocomplete取得失敗"}
        
        print(f"✅ ステップ1完了: {len(autocomplete_suggestions)}件のサジェスト")
        
        # ステップ2: 自動選定
        print("\n🤖 ステップ2: ローカルアルゴリズムによる自動選定")
        selected_keywords = self.analyze_and_select_keywords(autocomplete_suggestions, target_count=10)
        
        if not selected_keywords:
            print("❌ キーワード選定に失敗しました")
            return {"error": "キーワード選定失敗"}
        
        print(f"✅ ステップ2完了: {len(selected_keywords)}個のキーワードを選定")
        
        # ステップ3: 選定されたキーワードからRelated Searches + PAA取得
        print("\n🔍 ステップ3: 選定キーワードからRelated Searches + PAA取得")
        related_searches, paa_questions = await self.get_related_searches_and_paa(selected_keywords)
        
        # 結果の統合
        all_suggestions = list(set(autocomplete_suggestions + related_searches + paa_questions))
        
        # 結果の保存
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"automated_collected_{main_keyword.replace(' ', '_')}_{len(all_suggestions)}件.json"
        
        result_data = {
            "main_keyword": main_keyword,
            "collection_method": "全自動（ローカルアルゴリズム）",
            "timestamp": timestamp,
            "api_calls": 2,  # Autocomplete + Related Searches/PAA
            "results": {
                "autocomplete": autocomplete_suggestions,
                "selected_for_expansion": selected_keywords,
                "related_searches": related_searches,
                "people_also_ask": paa_questions,
                "total_unique": len(all_suggestions)
            }
        }
        
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(result_data, f, ensure_ascii=False, indent=2)
        
        # テキストファイルも作成
        txt_filename = f"automated_collected_{main_keyword.replace(' ', '_')}_{len(all_suggestions)}件.txt"
        with open(txt_filename, 'w', encoding='utf-8') as f:
            f.write(f"=== 全自動サジェスト収集結果 ===\n")
            f.write(f"メインキーワード: {main_keyword}\n")
            f.write(f"収集方法: 全自動（ローカルアルゴリズム）\n")
            f.write(f"API呼び出し回数: 2回\n")
            f.write(f"収集日時: {timestamp}\n")
            f.write(f"\n")
            f.write(f"=== 収集結果 ===\n")
            f.write(f"総ユニーク数: {len(all_suggestions)}件\n")
            f.write(f"\n")
            f.write(f"【Autocomplete】\n")
            for i, suggestion in enumerate(autocomplete_suggestions, 1):
                f.write(f"{i:2d}. {suggestion}\n")
            f.write(f"\n")
            f.write(f"【選定されたキーワード（拡張用）】\n")
            for i, keyword in enumerate(selected_keywords, 1):
                f.write(f"{i}. {keyword}\n")
            f.write(f"\n")
            f.write(f"【Related Searches】\n")
            for i, suggestion in enumerate(related_searches, 1):
                f.write(f"{i:2d}. {suggestion}\n")
            f.write(f"\n")
            f.write(f"【People Also Ask】\n")
            for i, question in enumerate(paa_questions, 1):
                f.write(f"{i:2d}. {question}\n")
            f.write(f"\n")
            f.write(f"【全サジェスト一覧】\n")
            for i, suggestion in enumerate(all_suggestions, 1):
                f.write(f"{i:3d}. {suggestion}\n")
        
        print(f"\n🎉 全自動サジェスト収集完了！")
        print(f"📁 結果ファイル: {filename}")
        print(f"📄 テキストファイル: {txt_filename}")
        print(f"📊 総収集数: {len(all_suggestions)}件")
        print(f"💰 API呼び出し回数: 2回")
        
        return result_data

async def main():
    """メイン実行関数"""
    try:
        collector = GoogleSuggestionCollector()
        
        # コマンドライン引数からキーワードを取得
        import sys
        if len(sys.argv) > 1:
            main_keyword = " ".join(sys.argv[1:])
        else:
            main_keyword = "夏 おすすめ お酒"  # デフォルトキーワード
        
        print(f"🎯 メインキーワード: {main_keyword}")
        print("=" * 60)
        
        # 全自動収集実行
        result = await collector.collect_suggestions_automated(main_keyword)
        
        if "error" in result:
            print(f"❌ エラーが発生しました: {result['error']}")
            return 1
        
        print("\n✅ 正常終了")
        return 0
        
    except Exception as e:
        print(f"❌ 予期しないエラーが発生しました: {e}")
        import traceback
        traceback.print_exc()
        return 1

if __name__ == "__main__":
    exit_code = asyncio.run(main())
    exit(exit_code)
