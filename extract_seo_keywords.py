#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
既存のJSONファイルからSEO用単語を抽出するスクリプト
"""

import json
import re
from pathlib import Path

def extract_all_content_for_seo(serp_data: dict) -> list:
    """SERPデータからSEO用の全コンテンツを抽出"""
    all_content = []
    
    # 1. 既に処理済みのサジェスト（results.suggestions）
    if 'results' in serp_data and 'suggestions' in serp_data['results']:
        all_content.extend(serp_data['results']['suggestions'])
    
    # 2. SERPデータから直接抽出
    if 'results' in serp_data and 'serp_results' in serp_data['results']:
        for serp_result in serp_data['results']['serp_results']:
            if 'serp_data' in serp_result:
                data = serp_result['serp_data']
                
                # 関連検索
                if 'related_searches' in data:
                    for search in data['related_searches']:
                        if isinstance(search, dict) and 'query' in search:
                            all_content.append(search['query'])
                        elif isinstance(search, str):
                            all_content.append(search)
                
                # 関連質問
                if 'related_questions' in data:
                    for question in data['related_questions']:
                        if isinstance(question, dict):
                            if 'question' in question:
                                all_content.append(question['question'])
                            if 'snippet' in question:
                                all_content.append(question['snippet'])
                
                # People Also Ask
                if 'people_also_ask' in data:
                    for paa in data['people_also_ask']:
                        if isinstance(paa, dict):
                            if 'question' in paa:
                                all_content.append(paa['question'])
                            if 'answer' in paa:
                                all_content.append(paa['answer'])
                
                # AI概要
                if 'ai_overview' in data:
                    ai_data = data['ai_overview']
                    if isinstance(ai_data, dict):
                        if 'questions' in ai_data:
                            for q in ai_data['questions']:
                                if isinstance(q, dict) and 'question' in q:
                                    all_content.append(q['question'])
                                elif isinstance(q, str):
                                    all_content.append(q)
                
                # フィーチャースニペット
                if 'featured_snippet' in data:
                    snippet = data['featured_snippet']
                    if isinstance(snippet, dict):
                        if 'title' in snippet:
                            all_content.append(snippet['title'])
                        if 'snippet' in snippet:
                            all_content.append(snippet['snippet'])
            
            elif 'suggestions' in serp_result:
                all_content.extend(serp_result['suggestions'])
    
    # 重複除去とソート
    unique_content = list(set(all_content))
    unique_content.sort()
    
    return unique_content

def main():
    json_file = "serp_optimized_collected_76件.json"
    
    try:
        # JSONファイルを読み込み
        with open(json_file, 'r', encoding='utf-8') as f:
            serp_data = json.load(f)
        
        print(f"📁 ファイル読み込み完了: {json_file}")
        
        # 全コンテンツを抽出
        all_content = extract_all_content_for_seo(serp_data)
        
        print(f"📊 抽出完了: {len(all_content)}件のコンテンツ")
        
        # 結果をテキストファイルに保存
        output_file = f"seo_all_content_{len(all_content)}件.txt"
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(f"=== SEO用全コンテンツ抽出結果 ===\n")
            f.write(f"元ファイル: {json_file}\n")
            f.write(f"抽出件数: {len(all_content)}件\n")
            f.write(f"\n")
            f.write(f"【全コンテンツ一覧】\n")
            for i, content in enumerate(all_content, 1):
                f.write(f"{i:3d}. {content}\n")
        
        print(f"📄 結果を保存しました: {output_file}")
        print(f"📊 抽出件数: {len(all_content)}件")
        
        # 最初の10件を表示
        print(f"\n📝 抽出されたコンテンツ（最初の10件）:")
        for i, content in enumerate(all_content[:10], 1):
            print(f"{i}. {content}")
        
        if len(all_content) > 10:
            print(f"... 他 {len(all_content) - 10}件")
            
    except FileNotFoundError:
        print(f"❌ ファイルが見つかりません: {json_file}")
    except json.JSONDecodeError:
        print(f"❌ JSONファイルの形式が正しくありません: {json_file}")
    except Exception as e:
        print(f"❌ エラーが発生しました: {e}")

if __name__ == "__main__":
    main()
