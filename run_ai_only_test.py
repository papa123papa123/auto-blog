# run_ai_only_test.py
"""
【AI特化テスト】既存のスクリーンショット画像を使い、AIによるスペック抽出部分だけをテストするスクリプト。
"""
import asyncio
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
    # ★★★ 既存のスクリーンショットフォルダを指定 ★★★
    SCREENSHOT_DIR = Path("screenshots")
    # ★★★★★★★★★★★★★★★★★★★★★★★★★★★★★

    print("\n--- AIによる画像解析テストを開始します ---")

    if not SCREENSHOT_DIR.exists():
        print(f"[エラー] スクリーンショットフォルダが見つかりません: {SCREENSHOT_DIR}")
        return
        
    # フォルダ内のすべてのpngファイルを取得
    screenshot_paths = [str(p) for p in SCREENSHOT_DIR.glob("*.png")]
    if not screenshot_paths:
        print(f"[エラー] {SCREENSHOT_DIR} にpngファイルが見つかりません。")
        return

    print(f"[INFO] {len(screenshot_paths)}枚の画像を処理対象とします。")

    # AIに画像を渡す
    gemini = GeminiGenerator()
    extractor = SpecExtractor(gemini)
    final_json_string = extractor.extract_from_images(screenshot_paths)

    # 結果をファイルに保存
    print("\n--- 抽出結果をファイルに保存します ---")
    output_dir = Path("product_databases")
    output_dir.mkdir(exist_ok=True)
    timestamp = datetime.datetime.now().strftime("%Y-%m-%d_%H%M%S")
    safe_category_name = "".join(c for c in TARGET_CATEGORY_NAME if c.isalnum()).rstrip()
    output_filename = f"{timestamp}_{safe_category_name}_ai_only_db.json"
    output_filepath = output_dir / output_filename

    try:
        parsed_json = json.loads(final_json_string)
        with open(output_filepath, "w", encoding="utf-8") as f:
            json.dump(parsed_json, f, indent=2, ensure_ascii=False)
    except json.JSONDecodeError:
        output_filepath = output_filepath.with_suffix('.txt')
        with open(output_filepath, "w", encoding="utf-8") as f:
            f.write(final_json_string)

    print(f"[成功] 処理が完了しました！ 結果ファイル: {output_filepath}")


if __name__ == "__main__":
    if sys.platform == "win32":
        sys.stdout.reconfigure(encoding='utf-8')
        sys.stderr.reconfigure(encoding='utf-8')
    
    # このスクリプトは非同期処理が不要なため、asyncioを使わない
    main()
