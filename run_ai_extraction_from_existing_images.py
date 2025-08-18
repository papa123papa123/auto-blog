# run_ai_extraction_from_existing_images.py
"""
【最終版v3】既存のスクリーンショット画像を使い、AIによるスペック抽出を実行し、
すべての結果を、単一のJSONファイルに統合して出力するスクリプト。
"""
import datetime
import json
import os
import sys
from pathlib import Path
import re

from dotenv import load_dotenv

# --- モジュール検索パスを追加 ---
sys.path.append(str(Path(__file__).resolve().parent / 'src'))
# --------------------------

def main():
    """メインの実行関数"""
    load_dotenv()
    if not os.getenv("GEMINI_API_KEY"):
        print("[エラー] .envファイルに GEMINI_API_KEY が設定されていません。")
        return

    from spec_extractor import SpecExtractor
    from gemini_generator import GeminiGenerator

    # --- 実行パラメータ ---
    TARGET_CATEGORY_NAME = "扇風機"
    SCREENSHOT_DIR = Path("screenshots")
    # --------------------

    print("\n--- AIによる既存画像からのスペック抽出を開始します ---")

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
    
    # ★★★ spec_extractorの新しいロジックを呼び出す ★★★
    final_json_string = extractor.extract_from_images(screenshot_paths)

    print("\n--- すべての抽出結果を単一ファイルに保存します ---")
    
    if not final_json_string or final_json_string == "[]":
        print("[処理中断] 抽出された製品情報が1件もなかったため、ファイルは作成されませんでした。")
        return

    output_dir = Path("product_databases")
    output_dir.mkdir(exist_ok=True)
    timestamp = datetime.datetime.now().strftime("%Y-%m-%d_%H%M%S")
    safe_category_name = "".join(c for c in TARGET_CATEGORY_NAME if c.isalnum()).rstrip()
    output_filename = f"{timestamp}_{safe_category_name}_integrated_db.json"
    output_filepath = output_dir / output_filename

    # ★★★ spec_extractorが既にJSON文字列を返すので、そのまま保存 ★★★
    try:
        parsed_json = json.loads(final_json_string)
        with open(output_filepath, "w", encoding="utf-8") as f:
            json.dump(parsed_json, f, indent=2, ensure_ascii=False)
        print(f"[成功] 処理が完了しました！ 統合ファイル: {output_filepath}")
        print(f"合計 {len(parsed_json)}件の製品情報が保存されました。")
    except json.JSONDecodeError:
        # 念のため、パースに失敗した場合は生のテキストを保存
        output_filepath = output_filepath.with_suffix('.txt')
        with open(output_filepath, "w", encoding="utf-8") as f:
            f.write(final_json_string)
        print(f"[WARN] JSON解析に失敗したため、生のテキストとして保存しました: {output_filepath}")


if __name__ == "__main__":
    if sys.platform == "win32":
        sys.stdout.reconfigure(encoding='utf-8')
        sys.stderr.reconfigure(encoding='utf-8')
    
    main()