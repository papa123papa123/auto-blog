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

    def _validate_and_correct_h3s(self, main_keyword: str, article_structure: Dict[str, Any]) -> Dict[str, Any]:
        """
        生成された構成案のH3見出しを検証し、ルール違反があればAIに自己修正させる。
        """
        max_retries = 2
        for attempt in range(max_retries):
            forbidden_words = re.split(r'[\s　]+', main_keyword.strip())
            all_h3s = [h3 for h2 in article_structure.get("outline", []) for h3 in h2.get("h3", [])]
            
            # 最後のまとめH3以外をチェック
            incorrect_h3s = [
                h3 for h3 in all_h3s[:-1] 
                if any(word in h3 for word in forbidden_words)
            ]

            if not incorrect_h3s:
                print("    [OK] H3見出しのキーワードルールチェックをクリアしました。")
                return article_structure # 成功

            print(f"    [WARN] H3見出しに禁止キーワードが含まれています。({len(incorrect_h3s)}件)")
            print(f"    -> 違反見出し: {', '.join(incorrect_h3s)}")
            print(f"    -> AIに自己修正を指示します... (試行 {attempt + 1}/{max_retries})")

            correction_prompt = self.prompt_manager.create_h3_correction_prompt(main_keyword, forbidden_words, incorrect_h3s)
            response = self.gemini_generator.generate([correction_prompt], model_type="flash", timeout=180)
            
            if not response or response.startswith("エラー:"):
                print(f"    [NG] AIからの修正応答エラー: {response}")
                continue

            corrected_h3_list = self._extract_json_from_text(response, is_list=True)

            if corrected_h3_list and isinstance(corrected_h3_list, list) and len(corrected_h3_list) == 12:
                print("    [OK] H3見出しの修正に成功しました。")
                # 構成案のH3を修正後のものに差し替える
                article_structure["outline"][0]["h3"] = corrected_h3_list[:6]
                article_structure["outline"][1]["h3"] = corrected_h3_list[6:]
            else:
                print(f"    [NG] 修正されたH3リストの形式が不正です。")

        print("[CRITICAL] AIによるH3見出しの自己修正がリトライ上限に達しました。処理を中断します。")
        return None # 最終的に失敗

    def design_article_structure(self, main_keyword: str, suggest_list: list[str]) -> Dict[str, Any]:
        """
        AIに記事構成案の設計を依頼し、検証と自己修正を経て、最終的なJSONを返す。
        """
        print(f"  -> AIが「{main_keyword}」の記事構成案を設計中...")
        
        prompt = self.prompt_manager.create_outline_prompt(main_keyword, suggest_list)
        response = self.gemini_generator.generate([prompt], model_type="flash", timeout=180)
        
        if not response or response.startswith("エラー:"):
            print(f"    [NG] Geminiからの初回応答エラー: {response}")
            return None

        initial_structure = self._extract_json_from_text(response)
        
        if not initial_structure:
            print("    [NG] Geminiの初回応答を解析できませんでした。")
            return None
        
        print("    [OK] 記事構成案の初回生成が完了。H3キーワードの検証と修正を開始します...")
        
        # 検証と自己修正のプロセスを呼び出す
        final_structure = self._validate_and_correct_h3s(main_keyword, initial_structure)
        
        if final_structure:
            print("    [OK] 全ての検証と修正が完了し、最終的な構成案が確定しました。")
        
        return final_structure