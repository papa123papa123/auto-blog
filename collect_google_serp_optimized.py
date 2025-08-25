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
        
        async with httpx.AsyncClient() as client:
            response = await client.get(self.base_url, params=params)
            response.raise_for_status()
            return response.json()
    
    def extract_suggestions(self, serp_data: dict) -> list:
        """SERPデータからサジェストを抽出"""
        suggestions = []
        
        # 基本的なサジェスト抽出
        if 'suggestions' in serp_data:
            suggestions.extend(serp_data['suggestions'])
        
        # 検索結果からタイトルを抽出
        if 'organic_results' in serp_data:
            for result in serp_data['organic_results']:
                if 'title' in result:
                    suggestions.append(result['title'])
        
        # 関連検索を抽出
        if 'related_searches' in serp_data:
            for search in serp_data['related_searches']:
                if isinstance(search, dict) and 'query' in search:
                    suggestions.append(search['query'])
                elif isinstance(search, str):
                    suggestions.append(search)
        
        # Related Questions（関連質問）を抽出
        if 'related_questions' in serp_data:
            for question_data in serp_data['related_questions']:
                if isinstance(question_data, dict):
                    # 質問文を抽出
                    if 'question' in question_data:
                        suggestions.append(question_data['question'])
                    
                    # テキストブロックからも情報を抽出
                    if 'text_blocks' in question_data:
                        for block in question_data['text_blocks']:
                            if isinstance(block, dict):
                                # スニペットを抽出
                                if 'snippet' in block:
                                    suggestions.append(block['snippet'])
                                
                                # リストアイテムを抽出
                                if 'list' in block:
                                    for item in block['list']:
                                        if isinstance(item, dict):
                                            if 'title' in item:
                                                suggestions.append(item['title'])
                                            if 'snippet' in item:
                                                suggestions.append(item['snippet'])
        
        # People Also Ask（よくある質問）を抽出
        if 'people_also_ask' in serp_data:
            for paa in serp_data['people_also_ask']:
                if isinstance(paa, dict):
                    if 'question' in paa:
                        suggestions.append(paa['question'])
                    if 'answer' in paa:
                        suggestions.append(paa['answer'])
        
        # AI概要を抽出
        if 'ai_overview' in serp_data:
            ai_overview = serp_data['ai_overview']
            if isinstance(ai_overview, dict):
                if 'questions' in ai_overview:
                    for q in ai_overview['questions']:
                        if isinstance(q, dict) and 'question' in q:
                            suggestions.append(q['question'])
                        elif isinstance(q, str):
                            suggestions.append(q)
        
        # フィーチャースニペットを抽出
        if 'featured_snippet' in serp_data:
            snippet = serp_data['featured_snippet']
            if isinstance(snippet, dict):
                if 'title' in snippet:
                    suggestions.append(snippet['title'])
                if 'snippet' in snippet:
                    suggestions.append(snippet['snippet'])
        
        # 重複を除去して返す
        return list(set(suggestions))
    
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
                "api_calls": 1,
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
    # メインキーワードを設定
    main_keyword = "夏　おすすめ　酒"
    
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
