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