# src/flows/manual_content_flow.py
import sys
from PyQt6.QtWidgets import QApplication
# from src.user_input_collector import UserInputCollector # 旧UI
from src.advanced_user_input_collector import AdvancedUserInputCollector # 新UI
from src.spec_extractor import SpecExtractor
from src.sub_keyword_selector import SubKeywordSelector
from src.gemini_generator import GeminiGenerator

class ManualContentFlow:
    """
    ユーザーの手動入力（スクショ/コピペ）からサブキーワードを生成するフロー。
    """

    def __init__(self, spec_extractor: SpecExtractor, sub_keyword_selector: SubKeywordSelector, gemini_generator: GeminiGenerator):
        # self.user_input_collector = UserInputCollector() # 旧UI
        self.spec_extractor = spec_extractor
        self.sub_keyword_selector = sub_keyword_selector
        self.gemini_generator = gemini_generator

    def run(self):
        """
        フローを実行する。
        """
        print("\n--- [手動入力] サブキーワード生成フロー ---")
        
        # 1. 新しいUIを呼び出してユーザーから情報を収集
        app = QApplication.instance()  # 既存のインスタンスを取得
        if app is None:  # インスタンスがなければ作成
            app = QApplication(sys.argv)
        
        collector_ui = AdvancedUserInputCollector()
        collector_ui.show()
        app.exec()

        main_keyword, pasted_text, screenshot_paths = (
            collector_ui.main_keyword,
            collector_ui.suggested_text,
            collector_ui.image_paths
        )

        if not main_keyword:
            print("メインキーワードが入力されなかったため、処理を中断します。")
            return None, None

        if not screenshot_paths and not pasted_text:
            print("情報（スクリーンショットまたはテキスト）が何も入力されなかったため、処理を中断します。")
            return None, None

        # 2. 収集した情報をテキストに変換・統合
        context_text = ""
        if screenshot_paths:
            print("\nスクリーンショットの画像を解析しています...")
            # 画像からのテキスト抽出処理はSpecExtractorが担当
            extracted_text = self.spec_extractor.extract_from_images(screenshot_paths)
            context_text += f"--- 画像からの情報 ---\n{extracted_text}\n\n"
            print("[OK] 画像の解析が完了しました。")

        if pasted_text:
            # 貼り付けられたテキストはそのままコンテキストに追加
            context_text += f"--- 貼り付けられたサジェスト情報 ---\n{pasted_text}\n\n"

        if not context_text.strip():
            print("[NG] 解析の結果、有効な情報が得られませんでした。処理を中断します。")
            return None, None
        
        # デバッグ用に統合したコンテキストを出力（コメントアウト）
        # print("\n--- AIに渡すコンテキスト情報 ---")
        # print(context_text)
        # print("---------------------------------")

        # 3. 統合した情報を元に、サブキーワードを生成
        final_sub_keywords = self.sub_keyword_selector.select_and_order_keywords(main_keyword, [context_text])
        if not final_sub_keywords:
            print("[NG] サブキーワードの生成に失敗しました。")
            return None, None

        print("\n--- フロー完了 ---")
        print(f"メインキーワード: {main_keyword}")
        print("最終選定サブキーワード:")
        for i, kw in enumerate(final_sub_keywords, 1):
            print(f"  {i:2d}. {kw}")
        
        return main_keyword, final_sub_keywords
