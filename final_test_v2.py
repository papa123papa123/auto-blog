# -*- coding: utf-8 -*-
# final_test_v2.py

import os
import re
from src.gemini_generator import GeminiGenerator
from dotenv import load_dotenv

def post_process_keywords(keywords_text: str, main_keyword: str) -> str:
    """プログラムでキーワードを強制的に整形し、重複を排除する。"""
    print("\n[Post-Process] AIの出力をプログラムで強制的に整形します...")
    
    keywords = keywords_text.strip().split('\n')
    if not keywords or (len(keywords) == 1 and keywords[0] == ''):
        print("[警告] AIからの出力が空です。")
        return ""

    main_keyword_parts = [part for part in main_keyword.lower().split() if part]
    
    usage_limits = {}
    if len(main_keyword_parts) > 0:
        usage_limits[main_keyword_parts[0]] = 4
    if len(main_keyword_parts) > 1:
        usage_limits[main_keyword_parts[1]] = 6

    usage_counts = {part: 0 for part in main_keyword_parts}
    
    processed_keywords = []
    for kw in keywords:
        temp_kw = kw
        
        # この見出しで、既に使用回数が上限に達した単語を削除する
        for part, limit in usage_limits.items():
            if usage_counts.get(part, 0) >= limit:
                temp_kw = re.sub(rf'\b{re.escape(part)}\b', '', temp_kw, flags=re.IGNORECASE)

        # 整形後の見出しで、実際に使われている単語の回数をカウントアップ
        # ただし、削除されずに残った単語のみカウント
        original_kw_lower = kw.lower()
        temp_kw_lower = temp_kw.lower()
        for part in main_keyword_parts:
            if part in original_kw_lower and part in temp_kw_lower:
                 usage_counts[part] = usage_counts.get(part, 0) + 1
        
        processed_keywords.append(re.sub(r'\s+', ' ', temp_kw).strip())

    print("\n--- プログラムによる整形後のキーワード ---")
    final_output = "\n".join(processed_keywords)
    print(final_output)
    return final_output

def main():
    """
    最終ロジック（AI生成＋プログラムによる強制整形）の性能を評価するためのテストスクリプト。
    """
    load_dotenv()
    
    main_keyword = "ワークマン　空調服"
    
    related_suggests = """
    （省略：前回のプロンプトと同じ関連サジェスト一覧）
    """

    instructions = f"""
あなたはプロのSEO編集長です。
メインキーワード「{main_keyword}」と、ユーザーが提供する関連キーワードを基に、読者の検索意図を完璧に満たす、質の高い記事見出しを12個作成してください。
あなたの仕事は、現段階ではキーワードの重複を気にせず、最高のアイデアを出すことです。
"""
    
    try:
        print("[テスト開始] 最終ロジックでキーワードを生成・整形します...")
        gemini = GeminiGenerator()
        
        print("\n[AI] AIがキーワード案を生成中...")
        raw_keywords_text = gemini.generate(instructions + "\n" + related_suggests)
        
        print("\n--- AIによって生成されたキーワード（整形前） ---")
        print(raw_keywords_text)
        
        # ポストプロセスで強制整形
        final_keywords = post_process_keywords(raw_keywords_text, main_keyword)
        
        # 最終結果をファイルに保存
        with open("final_result_output.txt", "w", encoding="utf-8") as f:
            f.write(final_keywords)
        print("\n[成功] 最終結果を 'final_result_output.txt' に保存しました。")

    except Exception as e:
        print(f"\n[エラー] テスト中にエラーが発生しました: {e}")

if __name__ == "__main__":
    main()
