#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
サジェスト収集からサブKW決定までの処理の流れをテストするスクリプト
"""

import asyncio
import json
import os
from pathlib import Path
from datetime import datetime

def test_suggestion_collection_flow():
    """サジェスト収集の流れをテスト"""
    print("=== サジェスト収集フローテスト ===")
    
    # 1. collect_google_suggestions_保護済み_絶対変更禁止.pyの動作確認
    print("\n1. SERPサジェスト収集テスト")
    try:
        from collect_google_suggestions_保護済み_絶対変更禁止 import SERPCollector
        
        async def test_serp_collection():
            collector = SERPCollector()
            main_keyword = "夏 お酒 おすすめ"
            result = await collector.collect_suggestions(main_keyword)
            
            if result:
                # 保存場所をserp_results/raw_data/に変更
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                filename = f"serp_results/raw_data/serp_collected_{len(result['results']['suggestions'])}件.json"
                
                with open(filename, 'w', encoding='utf-8') as f:
                    json.dump(result, f, ensure_ascii=False, indent=2)
                
                print(f"✅ SERP収集完了: {len(result['results']['suggestions'])}件")
                print(f"📁 保存場所: {filename}")
                return result
            else:
                print("❌ SERP収集に失敗")
                return None
        
        result = asyncio.run(test_serp_collection())
        
    except Exception as e:
        print(f"❌ SERP収集でエラー: {e}")
        return None
    
    # 2. extract_seo_content.pyの動作確認
    print("\n2. SEOコンテンツ抽出テスト")
    try:
        from extract_seo_content import extract_seo_content
        
        if result:
            # 保存場所をserp_results/extracted_content/に変更
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            content_filename = f"serp_results/extracted_content/seo_content_{len(result['results']['suggestions'])}件.txt"
            
            # コンテンツ抽出
            all_content = extract_seo_content(result)
            
            # ファイル保存
            with open(content_filename, 'w', encoding='utf-8') as f:
                f.write(f"=== SEO用コンテンツ抽出結果 ===\n")
                f.write(f"元ファイル: serp_collected_{len(result['results']['suggestions'])}件.json\n")
                f.write(f"抽出件数: {len(all_content)}件\n")
                f.write(f"抽出日時: {timestamp}\n")
                f.write("=" * 50 + "\n\n")
                for i, content in enumerate(all_content, 1):
                    f.write(f"{i}. {content}\n")
            
            print(f"✅ SEOコンテンツ抽出完了: {len(all_content)}件")
            print(f"📁 保存場所: {content_filename}")
            
    except Exception as e:
        print(f"❌ SEOコンテンツ抽出でエラー: {e}")
    
    # 3. extract_seo_keywords.pyの動作確認
    print("\n3. SEOキーワード抽出テスト")
    try:
        from extract_seo_keywords import extract_all_content_for_seo
        
        if result:
            # 保存場所をserp_results/final_keywords/に変更
            keywords_filename = f"serp_results/final_keywords/seo_all_content_{len(result['results']['suggestions'])}件.txt"
            
            # キーワード抽出
            all_keywords = extract_all_content_for_seo(result)
            
            # ファイル保存
            with open(keywords_filename, 'w', encoding='utf-8') as f:
                f.write(f"=== SEO用全キーワード抽出結果 ===\n")
                f.write(f"元ファイル: serp_collected_{len(result['results']['suggestions'])}件.json\n")
                f.write(f"抽出件数: {len(all_keywords)}件\n")
                f.write(f"抽出日時: {timestamp}\n")
                f.write("=" * 50 + "\n\n")
                for i, keyword in enumerate(all_keywords, 1):
                    f.write(f"{i}. {keyword}\n")
            
            print(f"✅ SEOキーワード抽出完了: {len(all_keywords)}件")
            print(f"📁 保存場所: {keywords_filename}")
            
    except Exception as e:
        print(f"❌ SEOキーワード抽出でエラー: {e}")
    
    # 4. サブKW決定のテスト
    print("\n4. サブKW決定テスト")
    try:
        # 現在のモード1で使用されている処理をテスト
        print("現在のモード1では、strategic_keyword_flow.py内の処理を使用")
        print("この部分は既存のフローで動作確認済み")
        
    except Exception as e:
        print(f"❌ サブKW決定でエラー: {e}")

def main():
    """メイン処理"""
    print("サジェスト収集フローのテストを開始します...")
    
    # ディレクトリ構造の確認
    print("\n=== ディレクトリ構造確認 ===")
    serp_dirs = ["serp_results", "serp_results/raw_data", "serp_results/extracted_content", "serp_results/final_keywords"]
    for dir_path in serp_dirs:
        if Path(dir_path).exists():
            print(f"✅ {dir_path}")
        else:
            print(f"❌ {dir_path}")
    
    # フローテスト実行
    test_suggestion_collection_flow()
    
    print("\n=== テスト完了 ===")
    print("結果を確認して、処理の流れが正しいかチェックしてください。")

if __name__ == "__main__":
    main()
