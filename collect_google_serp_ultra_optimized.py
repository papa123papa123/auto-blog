#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
SERP APIを使用したGoogleサジェスト収集 - 超最適化版
API呼び出しを3-4回に抑えて100件のサジェストを取得
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

class SERPUltraOptimizedCollector:
    def __init__(self):
        self.serp_api_key = os.getenv('SERPAPI_API_KEY')
        if not self.serp_api_key:
            raise ValueError("SERPAPI_API_KEY が設定されていません")
        
        self.base_url = "https://serpapi.com/search"
        self.collected_keywords = set()
        
    async def get_comprehensive_serp_data(self, keyword: str, start_position: int = 0) -> Dict[str, Any]:
        """包括的なSERPデータを取得（1回のAPI呼び出しで最大限の情報を取得）"""
        print(f"🔍 キーワード「{keyword}」から包括的SERPデータ取得中... (開始位置: {start_position})")
        
        params = {
            'q': keyword,
            'api_key': self.serp_api_key,
            'engine': 'google',
            'gl': 'jp',  # 日本
            'hl': 'ja',  # 日本語
            'num': 100,  # 最大結果数
            'start': start_position,
            'safe': 'active'
        }
        
        try:
            async with httpx.AsyncClient(timeout=90) as client:
                response = await client.get(self.base_url, params=params)
                response.raise_for_status()
                data = response.json()
                
                suggestions = []
                
                # 1. 検索結果のタイトルとスニペットからキーワード抽出
                if 'organic_results' in data:
                    for result in data['organic_results']:
                        title = result.get('title', '')
                        snippet = result.get('snippet', '')
                        
                        # タイトルから関連キーワードを抽出
                        title_keywords = self.extract_keywords_from_text(title, keyword)
                        suggestions.extend(title_keywords)
                        
                        # スニペットからも関連キーワードを抽出
                        snippet_keywords = self.extract_keywords_from_text(snippet, keyword)
                        suggestions.extend(snippet_keywords)
                
                # 2. Related Searches（関連検索）
                if 'related_searches' in data:
                    for rel_search in data['related_searches']:
                        query = rel_search.get('query', '')
                        if query and len(query) >= 3:
                            suggestions.append(query)
                
                # 3. People Also Ask（よくある質問）
                if 'related_questions' in data:
                    for question in data['related_questions']:
                        question_text = question.get('question', '')
                        if question_text and len(question_text) >= 5:
                            suggestions.append(question_text)
                
                # 4. 検索ボックスサジェスト
                if 'search_information' in data:
                    search_info = data['search_information']
                    if 'suggested_searches' in search_info:
                        for suggestion in search_info['suggested_searches']:
                            if suggestion and len(suggestion) >= 3:
                                suggestions.append(suggestion)
                
                # 5. パンくずリストからもキーワード抽出
                if 'breadcrumbs' in data:
                    for breadcrumb in data['breadcrumbs']:
                        breadcrumb_text = breadcrumb.get('text', '')
                        if breadcrumb_text and len(breadcrumb_text) >= 3:
                            suggestions.append(breadcrumb_text)
                
                # 重複除去
                unique_suggestions = list(set(suggestions))
                print(f"✅ 包括的SERP取得完了: {len(unique_suggestions)}件")
                
                return {
                    'keyword': keyword,
                    'suggestions': unique_suggestions,
                    'serp_data': data,
                    'start_position': start_position
                }
                
        except Exception as e:
            print(f"❌ SERP取得エラー: {e}")
            return {'keyword': keyword, 'suggestions': [], 'serp_data': {}, 'start_position': start_position}
    
    def extract_keywords_from_text(self, text: str, main_keyword: str) -> List[str]:
        """テキストから関連キーワードを抽出"""
        keywords = []
        
        if not text or len(text) < 3:
            return keywords
        
        # メインキーワードに関連する語句を抽出
        related_terms = [
            'おすすめ', 'ランキング', '比較', '選び方', '飲み方', '作り方', 'レシピ',
            '夏', '冬', '春', '秋', '暑い', '寒い', '冷たい', 'ひやおろし',
            '日本酒', 'ワイン', 'ビール', '焼酎', '梅酒', 'リキュール',
            'カクテル', 'ジン', 'ウォッカ', 'テキーラ', 'ラム', 'ブランデー',
            '初心者', '女性', '男性', 'プレゼント', 'おつまみ', '宅飲み',
            'コンビニ', 'スーパー', '居酒屋', 'バー', 'パブ', 'レストラン',
            '効果', '効能', 'カロリー', '糖質', 'アルコール度数', '賞味期限'
        ]
        
        # テキストから関連語句を含むフレーズを抽出
        for term in related_terms:
            if term in text:
                # テキストから該当部分を抽出
                start_idx = text.find(term)
                if start_idx >= 0:
                    # 前後の文脈を含めて抽出（より長いフレーズを取得）
                    context_start = max(0, start_idx - 15)
                    context_end = min(len(text), start_idx + len(term) + 15)
                    extracted = text[context_start:context_end].strip()
                    
                    # 適切な長さのフレーズのみを採用
                    if 5 <= len(extracted) <= 50:
                        # 特殊文字を除去
                        cleaned = extracted.replace('\n', ' ').replace('\r', ' ').strip()
                        if cleaned and len(cleaned) >= 5:
                            keywords.append(cleaned)
        
        return keywords
    
    async def collect_suggestions_ultra_optimized(self, strategy_keywords: List[str]) -> Dict[str, Any]:
        """超最適化された方法でサジェスト収集を実行"""
        print(f"🚀 超最適化戦略でサジェスト収集開始")
        print("=" * 60)
        
        all_suggestions = []
        serp_results = []
        
        # 戦略1: 汎用的なキーワードで包括的取得
        print("\n📊 戦略1: 汎用的キーワードで包括的取得")
        for keyword in strategy_keywords[:2]:  # 最初の2つのキーワード
            # 複数の開始位置から取得（より多くの結果を取得）
            for start_pos in [0, 10, 20]:  # 3つの開始位置
                result = await self.get_comprehensive_serp_data(keyword, start_pos)
                if result['suggestions']:
                    all_suggestions.extend(result['suggestions'])
                    serp_results.append(result)
                
                # API制限を避けるため待機
                await asyncio.sleep(2)
        
        # 戦略2: 季節性・用途別キーワードで補完
        print("\n📊 戦略2: 季節性・用途別キーワードで補完")
        for keyword in strategy_keywords[2:]:  # 残りのキーワード
            result = await self.get_comprehensive_serp_data(keyword, 0)
            if result['suggestions']:
                all_suggestions.extend(result['suggestions'])
                serp_results.append(result)
            
            # API制限を避けるため待機
            await asyncio.sleep(2)
        
        # 重複除去とフィルタリング
        unique_suggestions = list(set(all_suggestions))
        
        # 品質フィルタリング（短すぎる、長すぎるものを除去）
        filtered_suggestions = []
        for suggestion in unique_suggestions:
            if 5 <= len(suggestion) <= 50:  # 適切な長さ
                if not suggestion.startswith('http'):  # URLでない
                    if not suggestion.isdigit():  # 数字のみでない
                        filtered_suggestions.append(suggestion)
        
        # 結果の保存
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"serp_ultra_optimized_{len(filtered_suggestions)}件.json"
        
        result_data = {
            "collection_method": "SERP API超最適化版",
            "timestamp": timestamp,
            "api_calls": len(strategy_keywords) * 3,  # キーワード数 × 平均3回
            "strategy_keywords": strategy_keywords,
            "results": {
                "total_unique": len(filtered_suggestions),
                "suggestions": filtered_suggestions,
                "serp_results": serp_results
            }
        }
        
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(result_data, f, ensure_ascii=False, indent=2)
        
        # テキストファイルも作成
        txt_filename = f"serp_ultra_optimized_{len(filtered_suggestions)}件.txt"
        with open(txt_filename, 'w', encoding='utf-8') as f:
            f.write(f"=== SERP API超最適化サジェスト収集結果 ===\n")
            f.write(f"収集方法: SERP API超最適化版\n")
            f.write(f"API呼び出し回数: {result_data['api_calls']}回\n")
            f.write(f"収集日時: {timestamp}\n")
            f.write(f"\n")
            f.write(f"=== 収集結果 ===\n")
            f.write(f"総ユニーク数: {len(filtered_suggestions)}件\n")
            f.write(f"\n")
            f.write(f"【戦略キーワード】\n")
            for i, keyword in enumerate(strategy_keywords, 1):
                f.write(f"{i}. {keyword}\n")
            f.write(f"\n")
            f.write(f"【全サジェスト一覧】\n")
            for i, suggestion in enumerate(filtered_suggestions, 1):
                f.write(f"{i:3d}. {suggestion}\n")
        
        print(f"\n🎉 SERP API超最適化サジェスト収集完了！")
        print(f"📁 結果ファイル: {filename}")
        print(f"📄 テキストファイル: {txt_filename}")
        print(f"📊 総収集数: {len(filtered_suggestions)}件")
        print(f"💰 API呼び出し回数: {result_data['api_calls']}回")
        
        return result_data
    
    async def collect_single_keyword_suggestions(self, main_keyword: str) -> Dict[str, Any]:
        """単一キーワード（語群）からサジェスト収集を実行"""
        print(f"🚀 キーワード「{main_keyword}」から超最適化サジェスト収集開始")
        print("=" * 60)
        
        # 1つのキーワード（語群）から包括的なSERPデータを取得
        result = await self.get_comprehensive_serp_data(main_keyword)
        
        all_suggestions = result['suggestions'] if result['suggestions'] else []
        serp_results = [result] if result else []
        
        # 重複除去とフィルタリング
        unique_suggestions = list(set(all_suggestions))
        
        # 品質フィルタリング（短すぎる、長すぎるものを除去）
        filtered_suggestions = []
        for suggestion in unique_suggestions:
            if 5 <= len(suggestion) <= 50:  # 適切な長さ
                if not suggestion.startswith('http'):  # URLでない
                    if not suggestion.isdigit():  # 数字のみでない
                        filtered_suggestions.append(suggestion)
        
        # 結果の保存
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"serp_ultra_optimized_{len(filtered_suggestions)}件.json"
        
        result_data = {
            "collection_method": "SERP API超最適化版（単一語群）",
            "timestamp": timestamp,
            "api_calls": 1,  # 1回のAPI呼び出し
            "main_keyword": main_keyword,
            "results": {
                "total_unique": len(filtered_suggestions),
                "suggestions": filtered_suggestions,
                "serp_results": serp_results
            }
        }
        
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(result_data, f, ensure_ascii=False, indent=2)
        
        # テキストファイルも作成
        txt_filename = f"serp_ultra_optimized_{len(filtered_suggestions)}件.txt"
        with open(txt_filename, 'w', encoding='utf-8') as f:
            f.write(f"=== SERP API超最適化サジェスト収集結果 ===\n")
            f.write(f"収集方法: SERP API超最適化版（単一語群）\n")
            f.write(f"API呼び出し回数: 1回\n")
            f.write(f"収集日時: {timestamp}\n")
            f.write(f"\n")
            f.write(f"=== 収集結果 ===\n")
            f.write(f"総ユニーク数: {len(filtered_suggestions)}件\n")
            f.write(f"\n")
            f.write(f"【メインキーワード】\n")
            f.write(f"{main_keyword}\n")
            f.write(f"\n")
            f.write(f"【全サジェスト一覧】\n")
            for i, suggestion in enumerate(filtered_suggestions, 1):
                f.write(f"{i:3d}. {suggestion}\n")
        
        print(f"\nSERP API超最適化サジェスト収集完了！")
        print(f"📁 結果ファイル: {filename}")
        print(f"📄 テキストファイル: {txt_filename}")
        print(f"📊 総収集数: {len(filtered_suggestions)}件")
        print(f"💰 API呼び出し回数: 1回")
        
        return result_data

async def main():
    """メイン実行関数"""
    try:
        print("SERP API超最適化サジェスト収集ツール")
        print("=" * 50)
        
        # ユーザーからキーワード入力を取得
        print("\n📝 キーワードを入力してください（スペース区切りで複数入力可能）:")
        print("例: 酒 おすすめ 夏")
        print("例: お酒 初心者 選び方")
        print("例: 夏 お酒 暑い カクテル")
        
        user_input = input("\nキーワード: ").strip()
        
        if not user_input:
            print("❌ キーワードが入力されていません")
            return
        
        # 入力されたキーワードを1つの語群として処理
        main_keyword = user_input.strip()
        
        print(f"\n🎯 入力されたキーワード: {main_keyword}")
        print(f"📊 処理方法: 1つの語群としてSERP API呼び出し")
        print(f"💰 予想API呼び出し回数: 1回")
        
        # 実行確認
        confirm = input("\n実行しますか？ (y/N): ").strip().lower()
        if confirm not in ['y', 'yes', 'はい']:
            print("❌ 実行をキャンセルしました")
            return
        
        print("\n" + "=" * 60)
        
        collector = SERPUltraOptimizedCollector()
        result = await collector.collect_single_keyword_suggestions(main_keyword)
        
        if result['results']['total_unique'] >= 100:
            print(f"\n目標達成！100件以上のサジェストを取得しました")
            print(f"🎯 効率: {result['results']['total_unique']}件 ÷ {result['api_calls']}回 = {result['results']['total_unique']/result['api_calls']:.1f}件/回")
        else:
            print(f"\n目標未達成。現在{result['results']['total_unique']}件です")
            print("キーワードを調整するか、より具体的な語群を試してください")
        
    except Exception as e:
        print(f"エラーが発生しました: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(main())
