# src/sub_keyword_selector.py

import json
import re
from src.gemini_generator import GeminiGenerator
from src.prompt_manager import PromptManager
from typing import List, Dict, Any

class SubKeywordSelector:
    def __init__(self, gemini_generator: GeminiGenerator, prompt_manager: PromptManager):
        self.gemini_generator = gemini_generator
        self.prompt_manager = prompt_manager

    def _extract_json_from_text(self, text: str, is_list: bool = False):
        """マークダウンのコードブロックやテキストからJSONオブジェクトまたはリストを抽出する。"""
        try:
            match = re.search(r'```json\s*([\s\S]*?)\s*```', text, re.DOTALL)
            if match:
                json_str = match.group(1)
            else:
                pattern = r'(\[[\s\S]*\])' if is_list else r'(\{[\s\S]*\})'
                match = re.search(pattern, text, re.DOTALL)
                if match:
                    json_str = match.group(0)
                else:
                    raise json.JSONDecodeError("応答からJSONデータが見つかりませんでした。", text, 0)
            return json.loads(json_str)
        except json.JSONDecodeError as e:
            print(f"    [ERROR] JSONのパースに失敗しました。エラー: {e}")
            print(f"    [DEBUG] 受け取ったテキスト(先頭300文字): {text[:300]}...")
            return None

    def design_article_structure(self, main_keyword: str, suggest_list: list[str]) -> Dict[str, Any]:
        """
        AIに記事構成案の設計を依頼し、一発で正しいJSONを返す。
        """
        print(f"  -> AIが「{main_keyword}」の記事構成案を設計中...")
        
        prompt = self.prompt_manager.create_outline_prompt(main_keyword, suggest_list)
        response = self.gemini_generator.generate([prompt], model_type="flash", timeout=180)
        
        if not response or response.startswith("エラー:"):
            print(f"    [NG] Geminiからの応答エラー: {response}")
            return None

        article_structure = self._extract_json_from_text(response)
        
        if not article_structure:
            print("    [NG] Geminiの応答を解析できませんでした。")
            return None
        
        print("    [OK] 記事構成案の生成が完了しました。")
        return article_structure

    def select_and_organize_sub_keywords(self, main_keyword: str, raw_suggestions: List[str]) -> List[str]:
        """
        【改修済み】既存のプロンプトシステムを使用して168件のサジェストから適切なサブキーワードを選択・整理する
        H2見出し2個、各H2の下にH3見出し6個ずつ（合計12個）の構成に最適化
        """
        print(f"  -> AIが「{main_keyword}」の168件サジェストから適切なサブキーワードを選択・整理中...")
        print("  -> 既存のプロンプトシステムを使用してH2×2、H3×12の構成に最適化します")
        
        # 既存のプロンプトシステムを使用して記事構成案を作成
        try:
            # まず、168件のサジェストから記事構成案を作成
            article_structure = self.design_article_structure(main_keyword, raw_suggestions)
            
            if article_structure and article_structure.get("outline"):
                # 構成案からH3見出しを抽出してサブキーワードとして使用
                selected_keywords = []
                for h2_section in article_structure["outline"]:
                    if "h3" in h2_section:
                        selected_keywords.extend(h2_section["h3"])
                
                if selected_keywords:
                    print(f"    [OK] 既存のプロンプトシステムで{len(selected_keywords)}個のサブキーワードを選択・整理しました")
                    print(f"    [構成] H2: {len(article_structure['outline'])}個、H3: {len(selected_keywords)}個")
                    return selected_keywords
                else:
                    print("    [WARN] 構成案からH3見出しを抽出できませんでした。フォールバックを使用します。")
                    return self._get_fallback_keywords(main_keyword)
            else:
                print("    [WARN] 記事構成案の作成に失敗しました。フォールバックを使用します。")
                return self._get_fallback_keywords(main_keyword)

        except Exception as e:
            print(f"    [ERROR] サブキーワード選択中にエラーが発生しました: {e}")
            return self._get_fallback_keywords(main_keyword)

    def _get_fallback_keywords(self, main_keyword: str) -> List[str]:
        """フォールバック用のデフォルトキーワードを返す"""
        fallback_keywords = [
            f"{main_keyword} おすすめ",
            f"{main_keyword} 選び方",
            f"{main_keyword} ランキング",
            f"{main_keyword} 比較",
            f"{main_keyword} 使い方",
            f"{main_keyword} 口コミ",
            f"{main_keyword} とは"
        ]
        print(f"    [INFO] フォールバックキーワード{len(fallback_keywords)}個を使用します")
        return fallback_keywords