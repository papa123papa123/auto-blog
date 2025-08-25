# test_new_prompt.py - 新しい見出し構成プロンプトのテスト用

import os
import sys
from pathlib import Path
from dotenv import load_dotenv

# --- モジュール検索パスを追加 ---
sys.path.append(str(Path(__file__).resolve().parent / 'src'))
# --------------------------

# 環境変数の読み込み
load_dotenv()

def test_new_prompt():
    """
    新しい見出し構成プロンプトをテストする
    """
    
    # テスト用の新しいプロンプト
    new_prompt = """以下のルールでH2とH3の見出し構成を出力してください。本文は不要です。

H2は2つ、必ずメインキーワードを含める。

各H2の下にH3を6個ずつ、合計12個作成する。

各H2の6個目のH3は必ず『まとめ』とする。

H3にはメインキーワードを含めない。

H3は簡潔で分かりやすい表現にする。

H3の表現は重複を避け、多様性を保つようにする。

検索意図を自然に網羅できるようにH2・H3を構成する。

アフィリエイトブログとして、読者の購買意欲を高め、商品・サービスへの導線を自然に作る構成にする。

各H3は以下の要素を含むように構成する：
- 基本情報・知識（信頼性の構築）
- 比較・選び方（購買判断のサポート）
- 体験談・レビュー（共感・安心感の醸成）
- 注意点・リスク（信頼性の向上）
- おすすめ・活用方法（購買への自然な誘導）
- まとめ（次の行動への促し）

メインキーワード: 夏 お酒 ピッタリ"""

    print("=== 新しいプロンプトのテスト ===")
    print("プロンプト:")
    print(new_prompt)
    print("\n" + "="*50)
    
    # GeminiGeneratorのインポートとテスト
    try:
        from src.gemini_generator import GeminiGenerator
        
        print("GeminiGeneratorをインポートしました。")
        print("実際のテストを実行しますか？ (y/n): ", end="")
        
        response = input().strip().lower()
        if response == 'y':
            # 実際のテスト実行
            gemini = GeminiGenerator()
            result = gemini.generate([new_prompt], model_type="flash", timeout=180)
            
            print("\n=== 生成結果 ===")
            print(result)
            
            # 結果をファイルに保存
            with open("test_new_prompt_result.txt", "w", encoding="utf-8") as f:
                f.write(result)
            print("\n結果を 'test_new_prompt_result.txt' に保存しました。")
            
        else:
            print("テストをスキップしました。")
            
    except ImportError as e:
        print(f"GeminiGeneratorのインポートに失敗しました: {e}")
        print("src/gemini_generator.py が存在するか確認してください。")
    except Exception as e:
        print(f"エラーが発生しました: {e}")

if __name__ == "__main__":
    test_new_prompt()
