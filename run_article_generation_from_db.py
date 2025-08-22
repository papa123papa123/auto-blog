# run_article_generation_from_db.py
import json
from pathlib import Path
import sys
from dotenv import load_dotenv

# Tkinterをインポートしてファイルダイアログを使用
try:
    import tkinter as tk
    from tkinter import filedialog
except ImportError:
    tk = None

def run_generation_test():
    """
    既存のデータベースJSONを元に、記事生成フローのみを実行する。
    """
    print("--- 既存DBからの記事生成テスト ---")

    # 1. データベースJSONファイルの選択
    if not tk:
        print("[エラー] GUIライブラリ(tkinter)が見つかりません。ファイルパスを直接指定してください。")
        db_path_str = input("データベースJSONファイルのパスを入力してください: ").strip()
        if not db_path_str:
            print("パスが入力されませんでした。")
            return
        db_path = Path(db_path_str)
    else:
        root = tk.Tk()
        root.withdraw() # メインウィンドウを非表示
        db_path_str = filedialog.askopenfilename(
            title="使用するデータベースJSONファイルを選択してください",
            initialdir=Path("summarized_texts").resolve(),
            filetypes=[("JSON files", "*.json")]
        )
        if not db_path_str:
            print("ファイルが選択されませんでした。処理を中止します。")
            return
        db_path = Path(db_path_str)

    if not db_path.exists():
        print(f"[エラー] ファイルが見つかりません: {db_path}")
        return

    print(f"[OK] データベースファイルを使用します: {db_path.name}")
    database_content = db_path.read_text(encoding="utf-8")

    # 2. テスト用のキーワードと構成案を定義
    main_keyword = "夏 お酒 ピッタリ"
    # 本来は動的に生成されるが、テスト用に固定の構成案を用意
    article_structure = {
        "title": "【2025年夏】プロが選ぶ！夏にピッタリのお酒おすすめ12選＆最高のペアリング",
        "meta_description": "暑い夏に最適な、スッキリ飲める日本酒、ビール、ワインなどを厳選！夏料理との最高のペアリング（マリアージュ）や、夏酒の選び方を専門家が徹底解説します。",
        "tags": "夏, お酒, おすすめ, 日本酒, ビール, ワイン, ペアリング",
        "outline": [
            {
                "h2": "夏にピッタリのお酒、どう選ぶ？プロが教える3つのポイント",
                "h3": [
                    "爽快感が決め手！「のどごし」で選ぶ夏のお酒",
                    "アルコール度数低めがトレンド！軽やかに楽しむお酒",
                    "夏野菜やBBQと相性抜群！フードペアリングで選ぶ"
                ]
            },
            {
                "h2": "【シーン別】夏におすすめのお酒人気ランキング",
                "h3": [
                    "【おうち飲みに】コスパ最高！夏の定番ビール＆チューハイ",
                    "【女子会に】おしゃれで美味しい！フルーツを使ったカクテル",
                    "【プレゼントに】ちょっと贅沢な気分を味わえる夏限定の日本酒"
                ]
            }
        ]
    }
    print(f"[OK] テスト用のキーワード「{main_keyword}」と構成案を準備しました。")


    # 3. 記事生成フローの実行
    print("\n[実行] 記事生成フローを開始します...")
    
    load_dotenv()
    from src.haru_system import HaruOrchestrator

    try:
        orchestrator = HaruOrchestrator()
        # データベース構築をスキップし、記事生成フローのみを実行
        success = orchestrator.full_article_generation_flow.run(
            main_keyword,
            article_structure,
            database_content
        )
        if success:
            print("\n[成功] 記事と画像の生成が完了しました。")
            print("成果物は 'article_cache.md' と 'generated_images' フォルダを確認してください。")
        else:
            print("\n[失敗] 記事と画像の生成中にエラーが発生しました。")

    except Exception as e:
        import traceback
        print(f"エラー: テスト実行中に予期せぬ問題が発生しました。")
        print("\n--- GEMINI DEBUG LOG ---")
        print(f"ERROR_TYPE: {type(e).__name__}")
        print(f"ERROR_MESSAGE: {e}")
        print("--- TRACEBACK ---")
        traceback.print_exc()
        print("--- END DEBUG LOG ---")
        sys.exit(1)


if __name__ == "__main__":
    run_generation_test()
