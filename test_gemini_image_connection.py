# test_gemini_image_connection.py
"""
【最終接続テスト】Gemini APIへの画像を使った接続、そのものに問題がないかを確認する、究極にシンプルなスクリプト。
"""
import os
import sys
from pathlib import Path
import google.generativeai as genai
from dotenv import load_dotenv
from PIL import Image

def main():
    """メインの実行関数"""
    print("\n--- Gemini API 最終接続テストを開始します ---")

    # 1. .envファイルの読み込み
    load_dotenv()
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        print("[失敗] .envファイルから GEMINI_API_KEY が読み込めませんでした。")
        return
    print("[成功] APIキーの読み込みに成功しました。")

    # 2. Gemini APIの設定
    try:
        genai.configure(api_key=api_key)
        model = genai.GenerativeModel('gemini-1.5-pro-latest')
        print("[成功] Geminiモデルの初期化に成功しました。")
    except Exception as e:
        print(f"[失敗] Geminiの初期化中にエラーが発生しました: {e}")
        return

    # 3. 画像ファイルの準備
    image_path = Path("screenshots/comparison_final_1.png")
    if not image_path.exists():
        print(f"[失敗] テスト用の画像ファイルが見つかりません: {image_path}")
        return
    print(f"[INFO] テスト画像: {image_path}")

    # 4. APIへの接続と質問
    try:
        print("\n[INFO] AIに画像を送信し、応答を待っています... (タイムアウト: 120秒)")
        img = Image.open(image_path)
        
        # ★★★ これ以上なくシンプルな、ただ一つのAPIコール ★★★
        response = model.generate_content(
            ["この画像は何の画像ですか？簡潔に答えてください。", img],
            request_options={'timeout': 120}
        )
        # ★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★

        print("\n[成功] AIからの応答がありました！")
        print("--- AIの応答 ---")
        print(response.text)
        print("-----------------")

    except Exception as e:
        print(f"\n[失敗] AIへの接続中に、致命的なエラーが発生しました。")
        print(f"  -> エラー内容: {e}")

    print("\n--- テスト完了 ---")


if __name__ == "__main__":
    if sys.platform == "win32":
        sys.stdout.reconfigure(encoding='utf-8')
        sys.stderr.reconfigure(encoding='utf-8')
    main()
