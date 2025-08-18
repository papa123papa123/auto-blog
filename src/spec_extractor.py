# src/spec_extractor.py
"""
【最終版v7】スクリーンショット画像から、製品情報を「テキストとして」書き出す、究極にシンプルなモジュール。
"""
import sys
from pathlib import Path
from typing import List
sys.path.append(str(Path(__file__).resolve().parent.parent))

from src.gemini_generator import GeminiGenerator

class SpecExtractor:
    def __init__(self, gemini_generator: GeminiGenerator):
        self.gemini_generator = gemini_generator

    def extract_text_from_image(self, image_path: str) -> str:
        """
        単一の画像から、製品情報をテキストとして書き出す。
        """
        if not Path(image_path).exists():
            return f"[エラー] 画像ファイルが見つかりません: {image_path}"

        instructions = "この画像の内容を、テキストで、書き出して。"
        
        # `generate` メソッドにリスト形式でプロンプトを渡す
        prompt_parts = [instructions, image_path]
        response_text = self.gemini_generator.generate(prompt_parts, timeout=120)
        
        if "エラー" in response_text:
            return f"[AIエラー] 画像からのテキスト抽出に失敗しました: {image_path}"
        
        return response_text

    def extract_from_images(self, image_paths: List[str]) -> str:
        """
        複数の画像から、製品情報をまとめてテキストとして書き出す。
        """
        valid_image_paths = [path for path in image_paths if Path(path).exists()]
        if not valid_image_paths:
            return "[エラー] 有効な画像ファイルが見つかりません。"

        instructions = "これらの画像に書かれているテキストを、順番に、全て書き出してください。"
        
        # `generate` メソッドにリスト形式でプロンプトを渡す
        prompt_parts = [instructions] + valid_image_paths
        response_text = self.gemini_generator.generate(prompt_parts, timeout=240)
        
        if "エラー" in response_text:
            return f"[AIエラー] 複数の画像からのテキスト抽出に失敗しました。"
        
        return response_text
