# run_final_extractor.py
"""
【最終版】複数のランキンググループ（各2枚）のスクリーンショットをAIで解析し、
すべての結果を、一つのテキストファイルに統合する、最後のスクリプト。
"""
import asyncio
import datetime
import os
import sys
from pathlib import Path
from collections import defaultdict

from dotenv import load_dotenv

# --- モジュール検索パスを追加 ---
sys.path.append(str(Path(__file__).resolve().parent.parent))
# --------------------------

async def main():
    """メインの実行関数"""
    load_dotenv()
    if not os.getenv("GEMINI_API_KEY"):
        print("[エラー] .envファイルに GEMINI_API_KEY が設定されていません。")
        return

    from final_spec_extractor import FinalSpecExtractor # 以前作成したものを再利用
    from src.gemini_generator import GeminiGenerator

    # --- 実行パラメータ ---
    TARGET_CATEGORY_NAME = "扇風機"
    # --------------------

    screenshot_dir = Path(f"screenshots_{TARGET_CATEGORY_NAME}")
    if not screenshot_dir.exists():
        print(f"[エラー] スクリーンショットフォルダ '{screenshot_dir}' が見つかりません。")
        return

    # グループごとに2枚の画像をまとめる
    image_groups = defaultdict(list)
    for img_path in sorted(screenshot_dir.glob("*.png")):
        group_name = "_".join(img_path.stem.split("_")[1:-2])
        image_groups[group_name].append(str(img_path))

    print(f"\n--- AIによるテキスト抽出を開始します ({len(image_groups)}グループ) ---")
    
    gemini = GeminiGenerator()
    extractor = FinalSpecExtractor(gemini)
    all_extracted_texts = []

    for group_name, img_paths in image_groups.items():
        print(f"\n--- グループ '{group_name}' を処理中 ---")
        if len(img_paths) == 2:
            # 2枚1組でAIに渡す
            extracted_text = extractor.extract_and_format_from_images(img_paths)
            all_extracted_texts.append(f"--- ランキンググループ: {group_name} ---\n\n{extracted_text}\n\n")
        else:
            print(f"[WARN] 画像が2枚揃っていないため、グループ '{group_name}' をスキップします。")

    if not all_extracted_texts:
        print("\n[処理中断] 抽出されたテキストがなかったため、ファイルは作成されませんでした。")
        return

    print("\n--- すべての抽出結果を単一ファイルに統合します ---")
    output_dir = Path("product_texts_final")
    output_dir.mkdir(exist_ok=True)
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    
    output_filename = f"【最終統合版】{TARGET_CATEGORY_NAME}_ランキング_{timestamp}.txt"
    output_filepath = output_dir / output_filename

    with open(output_filepath, "w", encoding="utf-8") as f:
        f.write("\n".join(all_extracted_texts))

    print(f"\n[★★★★★ 完 成 ★★★★★]")
    print(f"すべての処理が完了しました！ 最終成果物はこちらです！")
    print(f"-> {output_filepath}")


if __name__ == "__main__":
    if sys.platform == "win32":
        sys.stdout.reconfigure(encoding='utf-8')
        sys.stderr.reconfigure(encoding='utf-8')
    
    asyncio.run(main())
