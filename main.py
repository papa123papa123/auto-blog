# main.py

import os
import sys
from dotenv import load_dotenv
from pathlib import Path
from src.haru_system import HaruOrchestrator
from typing import Dict, Optional
import re
import argparse
try:
    import tkinter as tk
    from tkinter import filedialog
except ImportError:
    tk = None

load_dotenv()

def _confirm_action(prompt_message: str, auto_yes: bool = False) -> bool:
    if auto_yes:
        print(f"{prompt_message} (y/n): y (自動承認)")
        return True
    while True:
        try:
            user_input = input(f"{prompt_message} (y/n): ").lower().strip()
            if user_input == 'y': return True
            if user_input == 'n': return False
            print("無効な入力です。'y' または 'n' を入力してください。")
        except (KeyboardInterrupt, EOFError):
            print("処理を中断します。")
            sys.exit(0)

def _run_fast_test_mode(orchestrator: HaruOrchestrator, site_info: Dict, credentials: Dict, auto_yes: bool):
    """[メニュー7] 高品質なDBを使い、記事生成から投稿までを高速テストする"""
    print("\n--- 高速生成＆投稿テストモード ---")
    
    default_main_keyword = "日傘 おすすめ cokage"
    default_sub_keywords = [
        "Cokage日傘の購入を検討する前に知っておきたいこと", "サンバリア100とCokage日傘、どちらがおすすめ？徹底比較",
        "Cokage日傘と東レサマーシールド日傘、特徴を比較して選びたい", "Cokage日傘のサイズ選び、50cmと55cmどちらが良い？",
        "Cokage日傘はどこで買える？取扱店を調べてみた", "Cokage日傘の口コミ評判を参考に購入を検討中",
        "サンバリア100とCokage日傘、人気ランキングを比較", "田中みな実さん愛用日傘、Cokage日傘との違いは？",
        "重さ、持ち運びやすさを知りたい", "りたたみ式と2段式、どちらが使いやすい？", "選び方、UVカット率や色の選び方を徹底解説"
    ]

    main_keyword = default_main_keyword
    if not auto_yes:
        main_keyword = input(f"メインキーワードを入力 (デフォルト: {default_main_keyword}): ").strip() or default_main_keyword
    else:
        print(f"メインキーワード (デフォルト): {default_main_keyword}")
    print(f"\nデフォルトのサブキーワード（{len(default_sub_keywords)}個）を使用します。")
    
    if not _confirm_action("このキーワード設定で処理を開始しますか？", auto_yes):
        return

    db_cache_path = Path("test_database_cache.txt")
    if db_cache_path.exists() and _confirm_action("キャッシュされたDBを再利用しますか？", auto_yes):
        summarized_text = db_cache_path.read_text(encoding="utf-8")
    else:
        database_text = orchestrator.database_construction_flow.build_database_from_sub_keywords(main_keyword, default_sub_keywords)
        if not database_text: return
        summarization_prompt = orchestrator.prompt_manager.create_summarization_prompt(main_keyword, database_text)
        summarized_text = orchestrator.gemini_generator.generate(summarization_prompt)
        if summarized_text.startswith("エラー:"): return
        db_cache_path.write_text(summarized_text, encoding="utf-8")

    # テスト用に、まず構成案を生成する
    print("\nテスト用の記事構成案を生成中...")
    article_structure = orchestrator.sub_keyword_selector.design_article_structure(main_keyword, default_sub_keywords)
    if not article_structure:
        print("[NG] テスト用の構成案生成に失敗しました。")
        return

    # 記事と画像の生成・ローカル保存
    success = orchestrator.full_article_generation_flow.run(main_keyword, article_structure, summarized_text)

    # 投稿
    if success and _confirm_action("\n生成された記事と画像をWordPressに投稿しますか？", auto_yes):
        result = orchestrator.wordpress_connector.post_from_cache(site_info, credentials)
        if result.get("success"):
            print(f"\n[成功] 投稿が完了しました！ URL: {result.get('link')}")
            orchestrator.site_manager.update_article_count(site_info['id'])
        else:
            print(f"\n[失敗] 投稿中にエラーが発生しました: {result.get('error')}")

def _run_repost_from_cache(orchestrator: HaruOrchestrator, site_info: Dict, credentials: Dict, auto_yes: bool):
    """[メニュー9] ローカルキャッシュから記事と画像を再投稿する"""
    print("\n--- キャッシュから再投稿モード ---")
    if not Path("article_cache.md").exists() or not Path("image_prompts.json").exists():
        print("[エラー] 投稿に必要なキャッシュファイル (article_cache.md, image_prompts.json) が見つかりません。")
        return
    
    if _confirm_action("ローカルにキャッシュされた最新の記事と画像をWordPressに投稿しますか？", auto_yes):
        result = orchestrator.wordpress_connector.post_from_cache(site_info, credentials)
        if result.get("success"):
            print(f"\n[成功] 投稿が完了しました！ URL: {result.get('link')}")
            orchestrator.site_manager.update_article_count(site_info['id'])
        else:
            print(f"\n[失敗] 投稿中にエラーが発生しました: {result.get('error')}")

def execute_mode(orchestrator: HaruOrchestrator, choice: str, auto_yes: bool):
    """指定されたモードを実行する"""
    site_info, credentials = None, None
    if choice in ['1', '4', '5', '6', '7', '9']:
        site_info = orchestrator.site_manager.get_next_available_site()
        if not site_info:
            print("投稿可能なアクティブサイトが見つかりませんでした。")
            return
        credentials = orchestrator.site_manager.get_credentials_by_name(site_info['name'])
        if not credentials:
            print(f"エラー: サイト「{site_info['name']}」の認証情報が見つかりません。")
            return
    
    if choice == '1':
        orchestrator.run_full_article_creation_flow(site_info, credentials)
    elif choice == '2':
        orchestrator.run_manual_content_flow()
    elif choice == '3':
        orchestrator.run_keyword_research_flow()
    elif choice == '4':
        article_data, main_keyword = orchestrator.run_content_generation_flow(site_info, credentials)
        if article_data and _confirm_action("\n生成された記事と画像をWordPressに投稿しますか？", auto_yes):
            orchestrator.wordpress_connector.post_article_from_data(site_info, credentials, article_data, main_keyword)
    elif choice == '5':
        article_data, main_keyword = orchestrator.run_article_creation_flow(site_info, credentials)
        if article_data and _confirm_action("\n生成された記事と画像をWordPressに投稿しますか？", auto_yes):
            orchestrator.wordpress_connector.post_article_from_data(site_info, credentials, article_data, main_keyword)
    elif choice == '6':
        print("画像投稿テストには、元となる記事テキストが必要です。")
        root = tk.Tk()
        root.withdraw()
        article_text_path = filedialog.askopenfilename(
            title="記事テキストファイルを選択",
            filetypes=[("Markdown files", "*.md"), ("Text files", "*.txt")],
            initialdir=str(Path(".").resolve())
        )
        if article_text_path:
            try:
                article_text = Path(article_text_path).read_text(encoding="utf-8")
                orchestrator.run_image_post_test_flow(site_info, credentials, article_text)
            except Exception as e:
                print(f"ファイルの読み込みに失敗しました: {e}")
        else:
            print("ファイルが選択されませんでした。")
    elif choice == '7':
        _run_fast_test_mode(orchestrator, site_info, credentials, auto_yes)
    elif choice == '8':
        orchestrator.run_database_and_summary_test()
    elif choice == '9':
        _run_repost_from_cache(orchestrator, site_info, credentials, auto_yes)
    elif choice == '10':
        orchestrator.run_strategic_keyword_flow(auto_yes)
    else:
        print("無効な選択です。")

def main():
    parser = argparse.ArgumentParser(description="Haru Blog System")
    parser.add_argument("--mode", type=str, help="実行するモードの番号")
    parser.add_argument("--yes", action="store_true", help="全ての確認プロンプトに自動で 'yes' と応答する")
    args = parser.parse_args()

    if not os.getenv("GEMINI_API_KEY"):
        print("エラー: 環境変数 'GEMINI_API_KEY' が設定されていません。")
        sys.exit(1)

    try:
        orchestrator = HaruOrchestrator()
    except Exception as e:
        print(f"エラー: 初期化中に問題が発生しました。詳細: {e}")
        return

    if args.mode:
        execute_mode(orchestrator, args.mode, args.yes)
    else:
        while True:
            print("\n--- Haru Blog System メインメニュー ---")
            print("1: [統合フロー] キーワード選定から記事生成・投稿まで")
            print("2: [手動KW選定] スクショ/コピペからAIが見出し作成")
            print("3: [キーワード発見・分析] 競合度チェック")
            print("4: [本文生成] 要約テキストを元に記事を作成")
            print("5: [記事生成テスト] キーワード入力から記事生成まで")
            print("6: [画像投稿テスト] 生成済みテキストから画像のみ投稿")
            print("7: [高速テストモード] DBを使って生成から投稿まで")
            print("8: [テスト用] 本文収集＆要約フロー")
            print("9: [再投稿] ローカルキャッシュから記事と画像を再投稿")
            print("10: [旧KW選定] AIアイデア出しと競合分析（自動収集）")
            print("0: 終了")
            choice = input("実行したいモードの番号を入力してください: ").strip()

            if choice == '0':
                break
            
            execute_mode(orchestrator, choice, args.yes)

            if not _confirm_action("続けて他のモードを実行しますか？", args.yes):
                break
    print("プログラムを終了します。")

if __name__ == "__main__":
    main()
