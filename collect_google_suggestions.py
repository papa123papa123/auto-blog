#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
SERP APIを使用したGoogleサジェスト収集 - 最適化版
API呼び出しを最小限に抑えて100件のサジェストを取得
"""

import asyncio
import httpx
import json
import os
from datetime import datetime
from dotenv import load_dotenv

# 環境変数を読み込み
load_dotenv()

class SERPCollector:
    def __init__(self):
        self.api_key = os.getenv('SERPAPI_API_KEY')
        if not self.api_key:
            raise ValueError("SERPAPI_API_KEYが設定されていません")
        
        self.base_url = "https://serpapi.com/search.json"
        
    async def get_ai_overview_details(self, page_token: str) -> dict:
        """AI概要の詳細を取得"""
        params = {
            'engine': 'google_ai_overview',
            'page_token': page_token,
            'api_key': self.api_key
        }
        
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(self.base_url, params=params)
                response.raise_for_status()
                return response.json()
        except Exception as e:
            print(f"  ⚠️ AI概要詳細取得でエラー: {e}")
            return {}

    async def get_serp_data(self, keyword: str) -> dict:
        """SERP APIからデータを取得"""
        params = {
            'engine': 'google',
            'q': keyword,
            'google_domain': 'google.com',
            'hl': 'ja',
            'gl': 'jp',
            'num': 100,
            'related_questions': 'true',
            'ai_overview': 'true',
            'featured_snippet': 'true',
            'people_also_ask': 'true',
            'api_key': self.api_key
        }
        
        # 1回のAPI呼び出しでデータを取得
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(self.base_url, params=params)
            response.raise_for_status()
            serp_data = response.json()
            
            # AI概要の詳細を取得
            if 'ai_overview' in serp_data and 'page_token' in serp_data['ai_overview']:
                print(f"  🔍 AI概要の詳細を取得中...")
                ai_details = await self.get_ai_overview_details(serp_data['ai_overview']['page_token'])
                if ai_details:
                    # AI概要の詳細を統合
                    if 'ai_overview' in serp_data:
                        serp_data['ai_overview'].update(ai_details)
                    print(f"  ✅ AI概要の詳細取得完了")
            
            return serp_data
    
    def extract_suggestions(self, serp_data: dict) -> list:
        """SERPデータからサジェストを抽出"""
        suggestions = []
        
        # 基本的なサジェスト抽出
        if 'suggestions' in serp_data:
            suggestions.extend(serp_data['suggestions'])
            print(f"  📌 基本サジェスト: {len(serp_data['suggestions'])}件")
        
        # 検索結果タイトルは除外（SEO対策には不要）
        # if 'organic_results' in serp_data:
        #     title_count = 0
        #     for result in serp_data['organic_results']:
        #         if 'title' in result:
        #             suggestions.append(result['title'])
        #             title_count += 1
        #     print(f"  📌 検索結果タイトル: {title_count}件")
        
        # 関連検索を抽出
        if 'related_searches' in serp_data:
            search_count = 0
            for search in serp_data['related_searches']:
                if isinstance(search, dict) and 'query' in search:
                    suggestions.append(search['query'])
                    search_count += 1
                elif isinstance(search, str):
                    suggestions.append(search)
                    search_count += 1
            print(f"  📌 関連検索: {search_count}件")
        
        # Related Questions（関連質問）を抽出
        if 'related_questions' in serp_data:
            question_count = 0
            for question_data in serp_data['related_questions']:
                if isinstance(question_data, dict):
                    # 質問文を抽出
                    if 'question' in question_data:
                        suggestions.append(question_data['question'])
                        question_count += 1
                    
                    # テキストブロックからも情報を抽出
                    if 'text_blocks' in question_data:
                        for block in question_data['text_blocks']:
                            if isinstance(block, dict):
                                # スニペットを抽出
                                if 'snippet' in block:
                                    suggestions.append(block['snippet'])
                                    question_count += 1
                                
                                # リストアイテムを抽出
                                if 'list' in block:
                                    for item in block['list']:
                                        if isinstance(item, dict):
                                            if 'title' in item:
                                                suggestions.append(item['title'])
                                                question_count += 1
                                            if 'snippet' in item:
                                                suggestions.append(item['snippet'])
                                                question_count += 1
            print(f"  📌 関連質問: {question_count}件")
        
        # People Also Ask（よくある質問）を抽出
        if 'people_also_ask' in serp_data:
            paa_count = 0
            for paa in serp_data['people_also_ask']:
                if isinstance(paa, dict):
                    if 'question' in paa:
                        suggestions.append(paa['question'])
                        paa_count += 1
                    if 'answer' in paa:
                        suggestions.append(paa['answer'])
                        paa_count += 1
            print(f"  📌 よくある質問: {paa_count}件")
        
        # AI概要を抽出
        if 'ai_overview' in serp_data:
            ai_count = 0
            ai_overview = serp_data['ai_overview']
            print(f"  🔍 AI概要データ構造: {list(ai_overview.keys()) if isinstance(ai_overview, dict) else 'dictではない'}")
            
            if isinstance(ai_overview, dict):
                # AI概要の全ての文字列データを抽出（制限なし）
                for key, value in ai_overview.items():
                    if isinstance(value, str):
                        suggestions.append(value)
                        ai_count += 1
                        print(f"    📝 AI概要文字列: {key} = {value[:50]}...")
                    elif isinstance(value, list):
                        for item in value:
                            if isinstance(item, str):
                                suggestions.append(item)
                                ai_count += 1
                            elif isinstance(item, dict):
                                # 辞書の全ての文字列値を抽出
                                for sub_key, sub_value in item.items():
                                    if isinstance(sub_value, str):
                                        suggestions.append(sub_value)
                                        ai_count += 1
                    elif isinstance(value, dict):
                        # 辞書の全ての文字列値を抽出
                        for sub_key, sub_value in value.items():
                            if isinstance(sub_value, str):
                                suggestions.append(sub_value)
                                ai_count += 1
                            elif isinstance(sub_value, list):
                                for sub_item in sub_value:
                                    if isinstance(sub_item, str):
                                        suggestions.append(sub_item)
                                        ai_count += 1
                                    elif isinstance(sub_item, dict):
                                        for sub_sub_key, sub_sub_value in sub_item.items():
                                            if isinstance(sub_sub_value, str):
                                                suggestions.append(sub_sub_value)
                                                ai_count += 1
            
            print(f"  📌 AI概要: {ai_count}件")
        
        # フィーチャースニペットを抽出
        if 'featured_snippet' in serp_data:
            snippet_count = 0
            snippet = serp_data['featured_snippet']
            if isinstance(snippet, dict):
                if 'title' in snippet:
                    suggestions.append(snippet['title'])
                    snippet_count += 1
                if 'snippet' in snippet:
                    suggestions.append(snippet['snippet'])
                    snippet_count += 1
            print(f"  📌 フィーチャースニペット: {snippet_count}件")
        
        # 重複を除去して返す
        unique_suggestions = list(set(suggestions))
        print(f"✅ 重複除去完了: {len(suggestions)}件 → {len(unique_suggestions)}件")
        return unique_suggestions
    
    async def collect_suggestions(self, keyword: str) -> dict:
        """メインキーワードからサジェストを収集"""
        print(f"キーワード '{keyword}' のサジェストを収集中...")
        
        try:
            # SERP APIを呼び出し
            serp_data = await self.get_serp_data(keyword)
            
            # サジェストを抽出
            suggestions = self.extract_suggestions(serp_data)
            
            # 結果を整理
            result = {
                "collection_method": "SERP API最適化版（単一語群）",
                "timestamp": datetime.now().strftime("%Y%m%d_%H%M%S"),
                "api_calls": 2,
                "main_keyword": keyword,
                "results": {
                    "total_unique": len(suggestions),
                    "suggestions": suggestions,
                    "serp_results": [{
                        "keyword": keyword,
                        "suggestions": suggestions,
                        "serp_data": serp_data
                    }]
                }
            }
            
            print(f"✅ 収集完了: {len(suggestions)}件のサジェスト")
            return result
            
        except Exception as e:
            print(f"❌ エラーが発生しました: {e}")
            import traceback
            traceback.print_exc()
            return None

async def main():
    # 環境変数からメインキーワードを取得（連続実行モードから渡される）
    main_keyword = os.environ.get('MAIN_KEYWORD', '')
    
    if not main_keyword:
        # 環境変数がない場合はデフォルト値を使用
        main_keyword = "夏　おすすめ　酒"
        print(f"⚠️  環境変数MAIN_KEYWORDが設定されていないため、デフォルト値を使用: {main_keyword}")
    else:
        print(f"🔍 環境変数から取得されたキーワード: {main_keyword}")
    
    # コレクターを初期化
    collector = SERPCollector()
    
    # サジェストを収集
    result = await collector.collect_suggestions(main_keyword)
    
    if result:
        # ファイル名を生成
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"serp_optimized_collected_{len(result['results']['suggestions'])}件.json"
        
        # JSONファイルに保存
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(result, f, ensure_ascii=False, indent=2)
        
        print(f"📁 結果を保存しました: {filename}")
        print(f"📊 取得件数: {len(result['results']['suggestions'])}件")
        
        # 最初の10件を表示
        print("\n📝 取得されたサジェスト（最初の10件）:")
        for i, suggestion in enumerate(result['results']['suggestions'][:10], 1):
            print(f"{i}. {suggestion}")
        
        if len(result['results']['suggestions']) > 10:
            print(f"... 他 {len(result['results']['suggestions']) - 10}件")

if __name__ == "__main__":
    asyncio.run(main())

