# final_spec_extractor.py
"""
【最終版】4枚1組のスクリーンショットを元に、AIがスペック情報を統合・清書するモジュール。
"""
import sys
from pathlib import Path
import json
import re
sys.path.append(str(Path(__file__).resolve().parent.parent))

from src.gemini_generator import GeminiGenerator
from typing import List, Dict

class FinalSpecExtractor:
    def __init__(self, gemini_generator: GeminiGenerator):
        self.gemini_generator = gemini_generator

    def extract_and_format_from_images(self, image_paths: List[str]) -> str:
        """
        4枚1組の画像からスペック情報を統合し、清書したテキストを返す。
        """
        if not all(Path(p).exists() for p in image_paths):
            return "[エラー] 画像ファイルの一部が見つかりません。"

        # ★★★ お客様の指示に基づく、最後の賢いプロンプト ★★★
        instructions = """ここに、同じ製品比較表を、4つの異なる角度（右上、右下、左下、左上）から撮影した4枚の画像があります。
これらの情報をすべて統合し、重複を除外した上で、各製品のスペック情報を、人間が読みやすいように、きれいに清書して、テキストで書き出してください。
"""
        
        # 4枚の画像を一度に渡す
        response_text = self.gemini_generator.generate_from_multimodal_prompt(
            instructions=instructions, user_text="", image_path=image_paths, timeout=600
        )
        
        if "エラー" in response_text:
            return f"[AIエラー] 画像からのテキスト抽出に失敗しました。"
        
        return response_text

if __name__ == '__main__':
    from dotenv import load_dotenv
    import os
    load_dotenv()
    
    if os.getenv("GEMINI_API_KEY"):
        print("--- FinalSpecExtractor テスト ---")
        # テスト用に、扇風機カテゴリの最初のグループの画像4枚を指定
        test_image_paths = [
            "screenshots_扇風機/扇風機_DCモーター扇風機_1_右上.png",
            "screenshots_扇風機/扇風機_DCモーター扇風機_2_右下.png",
            "screenshots_扇風機/扇風機_DCモーター扇風機_3_左下.png",
            "screenshots_扇風機/扇風機_DCモーター扇風機_4_左上.png"
        ]
        
        gemini = GeminiGenerator()
        extractor = FinalSpecExtractor(gemini)
        result_text = extractor.extract_and_format_from_images(test_image_paths)
        
        print("\n--- 統合・清書されたテキスト ---")
        print(result_text)
    else:
        print("環境変数 GEMINI_API_KEY が設定されていません。")
