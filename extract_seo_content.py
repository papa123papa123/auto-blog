#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
既存のJSONファイルからSEO用のコンテンツを抽出するスクリプト
入力: serp_collected_[件数]件.json
出力: seo_content_[件数]件.txt
"""

import json
import os
from pathlib import Path
from typing import List, Dict, Any
import re

def extract_seo_content(serp_data: dict) -> List[str]:
    """SERPデータからSEO用の全コンテンツを抽出"""
    print("📝 SERPデータからSEO用コンテンツを抽出中...")
    all_content = []
    
    # 1. 既に処理済みのサジェスト（results.suggestions）
    if 'results' in serp_data and 'suggestions' in serp_data['results']:
        suggestions = serp_data['results']['suggestions']
        all_content.extend(suggestions)
        print(f"  📌 基本サジェスト: {len(suggestions)}件")
    
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
                    print(f"  📌 関連検索: {len(data['related_searches'])}件")
                
                # 関連質問
                if 'related_questions' in data:
                    for question in data['related_questions']:
                        if isinstance(question, dict):
                            if 'question' in question:
                                all_content.append(question['question'])
                            if 'snippet' in question:
                                all_content.append(question['snippet'])
                            
                            # テキストブロックからも情報を抽出
                            if 'text_blocks' in question:
                                for block in question['text_blocks']:
                                    if isinstance(block, dict):
                                        if 'snippet' in block:
                                            all_content.append(block['snippet'])
                                        if 'list' in block:
                                            for item in block['list']:
                                                if isinstance(item, dict):
                                                    if 'title' in item:
                                                        all_content.append(item['title'])
                                                    if 'snippet' in item:
                                                        all_content.append(item['snippet'])
                    print(f"  📌 関連質問: {len(data['related_questions'])}件")
                
                # People Also Ask
                if 'people_also_ask' in data:
                    for paa in data['people_also_ask']:
                        if isinstance(paa, dict):
                            if 'question' in paa:
                                all_content.append(paa['question'])
                            if 'answer' in paa:
                                all_content.append(paa['answer'])
                    print(f"  📌 よくある質問: {len(data['people_also_ask'])}件")
                
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
                    print(f"  📌 AI概要: 1件")
                
                # フィーチャースニペット
                if 'featured_snippet' in data:
                    snippet = data['featured_snippet']
                    if isinstance(snippet, dict):
                        if 'title' in snippet:
                            all_content.append(snippet['title'])
                        if 'snippet' in snippet:
                            all_content.append(snippet['snippet'])
                    print(f"  📌 フィーチャースニペット: 1件")
                
                # 検索結果タイトル
                if 'organic_results' in data:
                    for result in data['organic_results']:
                        if 'title' in result:
                            all_content.append(result['title'])
                    print(f"  📌 検索結果タイトル: {len(data['organic_results'])}件")
            
            elif 'suggestions' in serp_result:
                all_content.extend(serp_result['suggestions'])
    
    # 重複除去とソート
    unique_content = list(set(all_content))
    unique_content.sort()
    
    print(f"✅ 抽出完了: {len(all_content)}件 → {len(unique_content)}件（重複除去後）")
    
    return unique_content

def filter_content(content_list: List[str]) -> List[str]:
    """コンテンツをフィルタリングして品質を向上"""
    print("🔍 コンテンツのフィルタリング中...")
    
    filtered_content = []
    removed_count = 0
    
    # 現在の日付を取得
    from datetime import datetime, timedelta
    current_date = datetime.now()
    one_month_ago = current_date - timedelta(days=30)
    
    for content in content_list:
        # URLを除去
        if content.startswith('http') or '://' in content:
            removed_count += 1
            continue
        
        # 無意味な文字列（英数字のみ、または非常に短い）を除去
        if len(content) < 5 or content.isalnum():
            removed_count += 1
            continue
        
        # 長すぎるテキスト（200文字以上）を除去
        if len(content) > 200:
            removed_count += 1
            continue
        
        # 日付のみのテキストを除去
        if re.match(r'^\d{4}[-/]\d{2}[-/]\d{2}', content.strip()):
            removed_count += 1
            continue
        
        # 英数字のみの文字列を除去
        if re.match(r'^[a-zA-Z0-9_-]+$', content.strip()):
            removed_count += 1
            continue
        
        # ドメイン名を除去（.com, .jp, .co.jp など）
        if re.match(r'^[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$', content.strip()):
            removed_count += 1
            continue
        
        # 古い日付を含むコンテンツを除去（昨年版、2023年など）
        if re.search(r'202[0-3]年|昨年版|前年版|旧年版', content):
            removed_count += 1
            continue
        
        # より具体的な古い日付パターンを除去
        if re.search(r'202[0-3][-/]\d{2}', content):
            removed_count += 1
            continue
        
        filtered_content.append(content)
    
    print(f"✅ フィルタリング完了: {len(content_list)}件 → {len(filtered_content)}件（{removed_count}件除去）")
    return filtered_content

def save_to_text_file(content_list: List[str], output_filename: str, original_filename: str):
    """抽出されたコンテンツをテキストファイルに保存"""
    print(f"📄 結果をテキストファイルに保存中: {output_filename}")
    
    with open(output_filename, 'w', encoding='utf-8') as f:
        for i, content in enumerate(content_list, 1):
            f.write(f"{i:3d}. {content}\n")
    
    print(f"✅ テキストファイルの保存が完了しました: {output_filename}")

def main():
    """メイン実行関数"""
    print("🔍 SEO用コンテンツ抽出システム")
    print("=" * 50)
    
    # 入力ファイルを検索
    json_files = []
    
    # 現在のディレクトリを検索
    for file in os.listdir('.'):
        if (file.startswith('serp_collected_') or file.startswith('serp_optimized_collected_')) and file.endswith('.json'):
            json_files.append(file)
    
    # serp_resultsディレクトリも検索
    serp_results_dir = 'serp_results'
    if os.path.exists(serp_results_dir):
        for file in os.listdir(serp_results_dir):
            if (file.startswith('serp_collected_') or file.startswith('serp_optimized_collected_')) and file.endswith('.json'):
                json_files.append(os.path.join(serp_results_dir, file))
    
    if not json_files:
        print("❌ serp_*_collected_*.json ファイルが見つかりません")
        print("   先に collect_google_suggestions.py を実行してください")
        return
    
    # ファイル名から件数を抽出して、数値順でソート
    def extract_count(filename):
        try:
            # ファイル名から件数を抽出
            # 例: "serp_optimized_collected_141件.json" → 141
            # 例: "serp_collected_76件.json" → 76
            # 例: "serp_collected_323件.json" → 323
            
            # "件.json" の前の部分を取得
            if '件.json' in filename:
                parts = filename.split('件.json')[0].split('_')
                # 最後の部分が件数
                last_part = parts[-1]
                if last_part.isdigit():
                    return int(last_part)
            
            # 別のパターン: "件" の前の部分
            if '件' in filename:
                parts = filename.split('件')[0].split('_')
                last_part = parts[-1]
                if last_part.isdigit():
                    return int(last_part)
            
            return 0
        except:
            return 0
    
    # 件数順でソート（降順）
    json_files.sort(key=extract_count, reverse=True)
    
    # デバッグ出力
    print("🔍 検索されたファイル:")
    for i, file in enumerate(json_files[:10]):  # 上位10件を表示
        count = extract_count(file)
        print(f"  {i+1}. {file} (件数: {count}件)")
    
    # 141件ファイルが存在するかチェック
    target_file = None
    for file in json_files:
        if 'serp_optimized_collected_141件.json' in file:
            target_file = file
            break
    
    if target_file:
        selected_file = target_file
        print(f"🎯 指定された141件ファイルを選択: {selected_file}")
    else:
        selected_file = json_files[0]
        print(f"📁 自動選択されたファイル: {selected_file} (件数: {extract_count(selected_file)}件)")
    
    try:
        # JSONファイルを読み込み
        with open(selected_file, 'r', encoding='utf-8') as f:
            serp_data = json.load(f)
        
        print(f"✅ JSONファイルの読み込みが完了しました")
        
        # 全コンテンツを抽出
        all_content = extract_seo_content(serp_data)
        
        if not all_content:
            print("❌ 抽出されたコンテンツがありません")
            return
        
        # コンテンツをフィルタリング
        filtered_content = filter_content(all_content)
        
        # 結果をテキストファイルに保存
        # ファイル名にメインキーワードと作成日時を追加
        from datetime import datetime
        current_time = datetime.now()
        time_str = current_time.strftime("%Y%m%d_%H%M")
        
        # メインキーワードを取得（ファイル名から推測）
        main_keyword = "夏_おすすめ_酒"  # デフォルト値
        
        # 元ファイル名からキーワードを抽出
        if 'serp_optimized_collected_141件.json' in selected_file:
            main_keyword = "夏_おすすめ_酒"  # 141件ファイルの場合
        
        # 出力ディレクトリを作成
        output_dir = "seo_results"
        os.makedirs(output_dir, exist_ok=True)
        
        output_filename = f"seo_content_{main_keyword}_{time_str}_{len(filtered_content)}件.txt"
        output_filepath = os.path.join(output_dir, output_filename)
        save_to_text_file(filtered_content, output_filepath, selected_file)
        
        # 結果サマリー
        print(f"\n🎉 抽出処理が完了しました！")
        print(f"📊 抽出件数: {len(filtered_content)}件")
        print(f"📁 出力ファイル: {output_filepath}")
        
        # 最初の10件を表示
        print(f"\n📝 抽出されたコンテンツ（最初の10件）:")
        for i, content in enumerate(filtered_content[:10], 1):
            print(f"{i:2d}. {content}")
        
        if len(filtered_content) > 10:
            print(f"... 他 {len(filtered_content) - 10}件")
        
        # 統計情報
        print(f"\n📈 統計情報:")
        print(f"  - 元ファイル: {selected_file}")
        print(f"  - 抽出件数: {len(filtered_content)}件")
        print(f"  - 出力ファイル: {output_filepath}")
        
        # 目標件数との比較
        if len(filtered_content) >= 200:
            print(f"🎯 目標達成！ 200件以上（{len(filtered_content)}件）のコンテンツを抽出しました")
        else:
            print(f"⚠️  目標未達: {len(filtered_content)}件（目標: 200件以上）")
            
    except FileNotFoundError:
        print(f"❌ ファイルが見つかりません: {selected_file}")
    except json.JSONDecodeError:
        print(f"❌ JSONファイルの形式が正しくありません: {selected_file}")
    except Exception as e:
        print(f"❌ エラーが発生しました: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()
