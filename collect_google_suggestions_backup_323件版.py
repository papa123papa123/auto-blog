#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Google SERP APIを使用してキーワードから大量のサジェスト・関連質問・AI概要を取得
目標: 200件以上のサジェスト取得、API呼び出し1回のみ（コスト最適化）
"""

import asyncio
import httpx
import json
import os
from datetime import datetime
from dotenv import load_dotenv

# 環境変数を読み込み
load_dotenv()

class GoogleSuggestionCollector:
    def __init__(self):
        """SERP APIコレクターを初期化"""
        self.api_key = os.getenv('SERPAPI_API_KEY')
        if not self.api_key:
            raise ValueError("SERPAPI_API_KEYが設定されていません")
        
        self.base_url = "https://serpapi.com/search.json"
        print("✅ SERP APIコレクターの初期化が完了しました")
        
    async def get_serp_data(self, keyword: str) -> dict:
        """SERP APIからデータを取得（1回の呼び出しで最大限のデータを取得）"""
        print(f"🔍 キーワード '{keyword}' のSERPデータを取得中...")
        
        params = {
            'engine': 'google',
            'q': keyword,
            'google_domain': 'google.com',
            'hl': 'ja',
            'gl': 'jp',
            'num': 100,  # 最大100件の検索結果
            'start': 0,  # 開始位置
            'related_questions': 'true',  # 関連質問を有効化
            'ai_overview': 'true',        # AI概要を有効化
            'featured_snippet': 'true',   # フィーチャースニペットを有効化
            'people_also_ask': 'true',    # よくある質問を有効化
            'related_searches': 'true',   # 関連検索を有効化
            'knowledge_graph': 'true',    # ナレッジグラフを有効化
            'api_key': self.api_key
        }
        
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(self.base_url, params=params)
                response.raise_for_status()
                data = response.json()
                print(f"✅ SERP APIからのデータ取得が完了しました")
                return data
                
        except httpx.TimeoutException:
            print("❌ タイムアウトエラー: SERP APIの応答が遅すぎます")
            raise
        except httpx.HTTPStatusError as e:
            print(f"❌ HTTPエラー: {e.response.status_code}")
            raise
        except Exception as e:
            print(f"❌ 予期しないエラー: {e}")
            raise
    
    def extract_all_suggestions(self, serp_data: dict) -> list:
        """SERPデータから全てのサジェスト・関連コンテンツを抽出"""
        print("📝 SERPデータからサジェストを抽出中...")
        suggestions = []
        
        # 1. 基本的なサジェスト
        if 'suggestions' in serp_data:
            suggestions.extend(serp_data['suggestions'])
            print(f"  📌 基本サジェスト: {len(serp_data['suggestions'])}件")
        
        # 2. 検索結果からタイトルを抽出
        if 'organic_results' in serp_data:
            for result in serp_data['organic_results']:
                if 'title' in result:
                    suggestions.append(result['title'])
            print(f"  📌 検索結果タイトル: {len(serp_data['organic_results'])}件")
        
        # 3. 関連検索を抽出
        if 'related_searches' in serp_data:
            for search in serp_data['related_searches']:
                if isinstance(search, dict) and 'query' in search:
                    suggestions.append(search['query'])
                elif isinstance(search, str):
                    suggestions.append(search)
            print(f"  📌 関連検索: {len(serp_data['related_searches'])}件")
        
        # 4. Related Questions（関連質問）を抽出
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
            print(f"  📌 関連質問: {len(serp_data['related_questions'])}件")
        
        # 5. People Also Ask（よくある質問）を抽出
        if 'people_also_ask' in serp_data:
            for paa in serp_data['people_also_ask']:
                if isinstance(paa, dict):
                    if 'question' in paa:
                        suggestions.append(paa['question'])
                    if 'answer' in paa:
                        suggestions.append(paa['answer'])
            print(f"  📌 よくある質問: {len(serp_data['people_also_ask'])}件")
        
        # 6. AI概要を強化して抽出
        if 'ai_overview' in serp_data:
            ai_overview = serp_data['ai_overview']
            ai_count = 0
            if isinstance(ai_overview, dict):
                # 質問を抽出
                if 'questions' in ai_overview:
                    for q in ai_overview['questions']:
                        if isinstance(q, dict) and 'question' in q:
                            suggestions.append(q['question'])
                            ai_count += 1
                        elif isinstance(q, str):
                            suggestions.append(q)
                            ai_count += 1
                
                # テキストブロックを抽出
                if 'text_blocks' in ai_overview:
                    for block in ai_overview['text_blocks']:
                        if isinstance(block, dict):
                            if 'snippet' in block:
                                suggestions.append(block['snippet'])
                                ai_count += 1
                            if 'title' in block:
                                suggestions.append(block['title'])
                                ai_count += 1
                
                # リストアイテムを抽出
                if 'list' in ai_overview:
                    for item in ai_overview['list']:
                        if isinstance(item, dict):
                            if 'title' in item:
                                suggestions.append(item['title'])
                                ai_count += 1
                            if 'snippet' in item:
                                suggestions.append(item['snippet'])
                                ai_count += 1
                
                # その他のフィールドも確認
                for key, value in ai_overview.items():
                    if isinstance(value, str) and key not in ['questions', 'text_blocks', 'list']:
                        suggestions.append(value)
                        ai_count += 1
            
            print(f"  📌 AI概要: {ai_count}件抽出完了")
        
        # 7. フィーチャースニペットを抽出
        if 'featured_snippet' in serp_data:
            snippet = serp_data['featured_snippet']
            if isinstance(snippet, dict):
                if 'title' in snippet:
                    suggestions.append(snippet['title'])
                if 'snippet' in snippet:
                    suggestions.append(snippet['snippet'])
            print(f"  📌 フィーチャースニペット: 1件")
        
        # 8. 検索結果のスニペットを全て抽出（文字数制限なし）
        if 'organic_results' in serp_data:
            snippet_count = 0
            for result in serp_data['organic_results']:
                if 'snippet' in result:
                    snippet = result['snippet']
                    if isinstance(snippet, str):
                        # スニペット全体を追加（日本語部分の抽出は後で行う）
                        suggestions.append(snippet)
                        snippet_count += 1
                        
                        # 日本語部分も別途抽出
                        japanese_text = self.extract_japanese_text(snippet)
                        if japanese_text and japanese_text != snippet:
                            suggestions.append(japanese_text)
            if snippet_count > 0:
                print(f"  📌 検索結果スニペット: {snippet_count}件（全体 + 日本語部分）")
        
        # 重複を除去して返す
        unique_suggestions = list(set(suggestions))
        
        # 長文サジェストの調査
        long_suggestions = [s for s in unique_suggestions if len(s) > 100]
        if long_suggestions:
            print(f"🔍 長文サジェスト（100文字以上）の調査:")
            for i, long_s in enumerate(long_suggestions[:5], 1):  # 最初の5件のみ表示
                print(f"  {i}. 長さ: {len(long_s)}文字")
                print(f"     内容: {long_s[:100]}...")
                print(f"     出所: {'AI概要' if 'AI概要' in str(serp_data.get('ai_overview', '')) else 'その他'}")
                print()
        
        # URLを含むサジェストを除去（タイトルは保持）
        unique_suggestions = [s for s in unique_suggestions if not ('http://' in s or 'https://' in s or 'www.' in s)]
        
        # 長すぎるサジェスト（100文字以上）を除去
        unique_suggestions = [s for s in unique_suggestions if len(s) <= 100]
        
        print(f"✅ 重複除去完了: {len(suggestions)}件 → {len(unique_suggestions)}件")
        print(f"✅ 長文除去完了: 100文字以下のみ残しました")
        
        return unique_suggestions
    
    def extract_japanese_text(self, text: str) -> str:
        """テキストから日本語部分のみを抽出（文字数制限なし）"""
        if not text:
            return ""
        
        # 日本語文字（ひらがな、カタカナ、漢字）を含む部分を抽出
        import re
        japanese_pattern = r'[一-龯ぁ-んァ-ヶー]+'
        japanese_matches = re.findall(japanese_pattern, text)
        
        if japanese_matches:
            # 日本語部分を結合（文字数制限を削除）
            japanese_text = ''.join(japanese_matches)
            return japanese_text
        
        return ""
    
    async def collect_suggestions(self, keyword: str) -> dict:
        """メインキーワードからサジェストを収集"""
        print(f"\n🎯 キーワード '{keyword}' のサジェスト収集を開始します")
        print("=" * 60)
        
        try:
            # SERP APIを1回のみ呼び出し
            serp_data = await self.get_serp_data(keyword)
            
            # サジェストを抽出
            suggestions = self.extract_all_suggestions(serp_data)
            
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
            
            print(f"\n🎉 収集完了: {len(suggestions)}件のサジェスト")
            
            # 目標件数との比較
            if len(suggestions) >= 100:
                print(f"🎯 目標達成！ 100件以上（{len(suggestions)}件）のサジェストを取得しました")
            else:
                print(f"⚠️  目標未達: {len(suggestions)}件（目標: 100件以上）")
            
            return result
            
        except Exception as e:
            print(f"❌ エラーが発生しました: {e}")
            import traceback
            traceback.print_exc()
            return None

async def main():
    """メイン実行関数"""
    print("🚀 Google SERP API サジェスト収集システム")
    print("=" * 60)
    
    # 結果用フォルダを作成
    results_dir = "serp_results"
    if not os.path.exists(results_dir):
        os.makedirs(results_dir)
        print(f"📁 結果用フォルダを作成しました: {results_dir}")
    
    # メインキーワードを設定
    main_keyword = "夏　おすすめ　酒"
    
    try:
        # コレクターを初期化
        collector = GoogleSuggestionCollector()
        
        # サジェストを収集
        result = await collector.collect_suggestions(main_keyword)
        
        if result:
            # ファイル名を生成
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"serp_collected_{len(result['results']['suggestions'])}件.json"
            filepath = os.path.join(results_dir, filename)
            
            # JSONファイルに保存
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(result, f, ensure_ascii=False, indent=2)
            
            print(f"\n📁 結果を保存しました: {filepath}")
            print(f"📊 取得件数: {len(result['results']['suggestions'])}件")
            
            # 最初の10件を表示
            print("\n📝 取得されたサジェスト（最初の10件）:")
            for i, suggestion in enumerate(result['results']['suggestions'][:10], 1):
                print(f"{i:2d}. {suggestion}")
            
            if len(result['results']['suggestions']) > 10:
                print(f"... 他 {len(result['results']['suggestions']) - 10}件")
            
            # 統計情報
            print(f"\n📈 統計情報:")
            print(f"  - API呼び出し回数: {result['api_calls']}回")
            print(f"  - 重複除去後の件数: {result['results']['total_unique']}件")
            print(f"  - 処理時刻: {result['timestamp']}")
            print(f"  - 保存先: {results_dir}/")
            
            # SERP APIコスト情報
            print(f"\n💰 SERP APIコスト情報:")
            print(f"  - 基本料金: $0.05/検索")
            print(f"  - 今回の料金: ${0.05 * result['api_calls']:.2f}")
            print(f"  - 1件あたりのコスト: ${(0.05 * result['api_calls']) / result['results']['total_unique']:.4f}")
            print(f"  - コスト効率: 1回のAPI呼び出しで{result['results']['total_unique']}件取得")
            
        else:
            print("❌ サジェストの収集に失敗しました")
            
    except Exception as e:
        print(f"❌ システムエラー: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(main())
