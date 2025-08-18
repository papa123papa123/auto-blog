# run_simple_extraction.py
"""
【最終版v2】既存のスクリーンショット画像を一枚ずつ処理し、
AIが書き出したテキストを、個別のテキストファイルとして保存する、究極にシンプルなスクリプト。
"""
import datetime
import os
import sys
from pathlib import Path

# ★★★ すべての処理の最初に .env を読み込む ★★★
from dotenv import load_dotenv
load_dotenv()
# ★★★★★★★★★★★★★★★★★★★★★★★★★★★★★

# --- モジュール検索パスを追加 ---
sys.path.append(str(Path(__file__).resolve().parent / 'src'))
# --------------------------

def main():
    """メインの実行関数"""
    if not os.getenv("GEMINI_API_KEY"):
        print("[エラー] .envファイルに GEMINI_API_KEY が設定されていません。")
        return

    from spec_extractor import SpecExtractor
    from gemini_generator import GeminiGenerator

    # --- 実行パラメータ ---
    TARGET_CATEGORY_NAME = "扇風機"
    SCREENSHOT_DIR = Path("screenshots")
    # --------------------

    print("\n--- AIによる画像からのテキスト書き出しを開始します ---")

    if not SCREENSHOT_DIR.exists():
        print(f"[エラー] スクリーンショットフォルダが見つかりません: {SCREENSHOT_DIR}")
        return
        
    screenshot_paths = sorted([str(p) for p in SCREENSHOT_DIR.glob("*.png")])
    if not screenshot_paths:
        print(f"[エラー] {SCREENSHOT_DIR} にpngファイルが見つかりません。")
        return

    print(f"[INFO] {len(screenshot_paths)}枚の画像を処理対象とします。")

    gemini = GeminiGenerator()
    extractor = SpecExtractor(gemini)
    
    output_dir = Path("product_texts")
    output_dir.mkdir(exist_ok=True)

    for i, image_path in enumerate(screenshot_paths):
        print(f"\n--- [{i+1}/{len(screenshot_paths)}] 画像を処理中: {image_path} ---")
        
        extracted_text = extractor.extract_text_from_image(image_path)
        
        timestamp = datetime.datetime.now().strftime("%Y-%m-%d_%H%M%S")
        output_filename = f"{timestamp}_{TARGET_CATEGORY_NAME}_{i+1}.txt"
        output_filepath = output_dir / output_filename

        with open(output_filepath, "w", encoding="utf-8") as f:
            f.write(extracted_text)
            
        print(f"[OK] 抽出したテキストをファイルに保存しました: {output_filepath}")

    print("\n--- すべての処理が完了しました ---")


if __name__ == "__main__":
    if sys.platform == "win32":
        sys.stdout.reconfigure(encoding='utf-8')
        sys.stderr.reconfigure(encoding='utf-8')
    
    main()