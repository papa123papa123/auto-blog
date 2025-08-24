# run_dataforseo_suggestions.py
# 単回API × 3ソース（Google/Yahoo/Related）を並列実行 → マージ・重複排除して出力
# 使い方:  python run_dataforseo_suggestions.py "日傘 cokage"

import os, sys, base64, json
from typing import List, Dict
try:
    from dotenv import load_dotenv
    load_dotenv()
except Exception:
    pass

import httpx


async def main():
    """メインの実行関数"""
    print("=== Data for SEO メインKWサジェスト収集システム ===")
    
    # .envファイルから環境変数を読み込み
    load_dotenv()
    
    # Data for SEO API認証情報の取得
    api_key = os.getenv('DATAFORSEO_LOGIN')
    api_secret = os.getenv('DATAFORSEO_PASSWORD')
    base64_format = os.getenv('DATAFORSEO_BASE64_FORMAT')
    
    # Base64形式が設定されている場合はそれを使用
    if base64_format:
        import base64
        try:
            decoded_auth = base64.b64decode(base64_format).decode()
            api_key, api_secret = decoded_auth.split(':', 1)
            print(f"✅ Data for SEO Base64認証情報を読み込みました")
            print(f"Base64 Format: {base64_format[:12]}...{base64_format[-4:] if len(base64_format) > 12 else '***'}")
        except Exception as e:
            print(f"❌ Base64認証情報のデコードに失敗: {e}")
            return
    elif api_key and api_secret:
        print(f"✅ Data for SEO API認証情報を読み込みました")
        print(f"Login: {api_key[:8]}...{api_key[-4:] if len(api_key) > 8 else '***'}")
        print(f"Password: {api_secret[:8]}...{api_secret[-4:] if len(api_secret) > 8 else '***'}")
    else:
        print("❌ .envファイルにData for SEOのAPI認証情報が設定されていません")
        print("以下のいずれかの環境変数を設定してください:")
        print("  DATAFORSEO_BASE64_FORMAT=your_base64_encoded_credentials")
        print("  または")
        print("  DATAFORSEO_LOGIN=your_login")
        print("  DATAFORSEO_PASSWORD=your_password")
        return
    
    # メインキーワードの設定
    main_keyword = input("\n分析したいメインキーワードを入力してください: ").strip()
    if not main_keyword:
        print("メインキーワードが入力されませんでした。処理を中断します。")
        return
    
    print(f"\nメインキーワード: 「{main_keyword}」")
    print("Data for SEO APIからサジェストを段階的に収集します。")
    print("ランダムなレイテンシーでレート制限を回避します。")
    
    # 出力ディレクトリの作成
    output_dir = Path("collected_suggestions")
    output_dir.mkdir(exist_ok=True)
    
    # DataForSEOSuggestionCollectorの初期化
    collector = DataForSEOSuggestionCollector(api_key, api_secret)
    
    try:
        # サジェスト収集の実行
        print("\nサジェスト収集を開始します...")
        result = await collector.collect_all_suggestions(main_keyword)
        
        if not result["suggestions"]:
            print("[警告] サジェストが収集できませんでした。")
            return
        
        # 結果の保存
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        safe_keyword = "".join(c for c in main_keyword if c.isalnum() or c in (' ', '_', '-')).rstrip()
        
        # JSONファイルに保存
        json_filename = f"{timestamp}_{safe_keyword}_dataforseo_suggestions.json"
        json_path = output_dir / json_filename
        
        with open(json_path, "w", encoding="utf-8") as f:
            json.dump(result, f, ensure_ascii=False, indent=2)
        
        # テキストファイルに保存（サブKW作成用）
        txt_filename = f"{timestamp}_{safe_keyword}_dataforseo_suggestions.txt"
        txt_path = output_dir / txt_filename
        
        with open(txt_path, "w", encoding="utf-8") as f:
            f.write(f"メインキーワード: {main_keyword}\n")
            f.write(f"収集日時: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write(f"総サジェスト数: {len(result['suggestions'])}個\n")
            f.write("=" * 50 + "\n\n")
            
            for i, suggestion in enumerate(result["suggestions"], 1):
                f.write(f"{i:3d}. {suggestion}\n")
        
        # フィルタリング済みサジェストの取得
        filtered_suggestions = collector.get_suggestions_for_sub_keyword_creation()
        
        # フィルタリング済みサジェストも保存
        filtered_txt_filename = f"{timestamp}_{safe_keyword}_dataforseo_filtered_suggestions.txt"
        filtered_txt_path = output_dir / filtered_txt_filename
        
        with open(filtered_txt_path, "w", encoding="utf-8") as f:
            f.write(f"メインキーワード: {main_keyword}\n")
            f.write(f"収集日時: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write(f"フィルタリング済みサジェスト数: {len(filtered_suggestions)}個\n")
            f.write("=" * 50 + "\n\n")
            
            for i, suggestion in enumerate(filtered_suggestions, 1):
                f.write(f"{i:3d}. {suggestion}\n")
        
        # 結果の表示
        print(f"\n=== 収集結果 ===")
        print(f"メインキーワード: {main_keyword}")
        print(f"総サジェスト数: {len(result['suggestions'])}個")
        print(f"フィルタリング済み: {len(filtered_suggestions)}個")
        print(f"\n保存ファイル:")
        print(f"  - JSON: {json_path}")
        print(f"  - 全サジェスト: {txt_path}")
        print(f"  - フィルタリング済み: {filtered_txt_path}")
        
        # サブKW作成への移行案内
        if len(filtered_suggestions) >= 100:
            print(f"\n🎯 目標達成！ {len(filtered_suggestions)}個のサジェストを収集しました。")
            print("次のステップ: サブキーワード作成に移行できます。")
            
            # サブKW作成の実行確認
            proceed = input("\nサブキーワード作成を実行しますか？ (y/n): ").strip().lower()
            if proceed in ['y', 'yes', 'はい']:
                print("\nサブキーワード作成を開始します...")
                await run_sub_keyword_creation(main_keyword, filtered_suggestions)
            else:
                print("サブキーワード作成は後で実行してください。")
        else:
            print(f"\n⚠️  目標の100個には達しませんでした（{len(filtered_suggestions)}個）")
            print("設定の調整や再実行を検討してください。")
    
    finally:
        # セッションを閉じる
        await collector.close()


async def run_sub_keyword_creation(main_keyword: str, suggestions: list):
    """サブキーワード作成の実行"""
    try:
        # 既存のサブキーワード作成フローを呼び出し
        from src.sub_keyword_selector import SubKeywordSelector
        from src.gemini_generator import GeminiGenerator
        
        print("サブキーワード作成システムを初期化中...")
        gemini = GeminiGenerator()
        selector = SubKeywordSelector(gemini)
        
        print(f"収集された{len(suggestions)}個のサジェストからサブキーワードを作成中...")
        
        # サジェストをテキスト形式に変換
        suggestions_text = "\n".join([f"- {s}" for s in suggestions[:100]])  # 最初の100個を使用
        
        # サブキーワード作成の実行
        result = selector.create_sub_keywords_from_suggestions(main_keyword, suggestions_text)
        
        if result:
            print("✅ サブキーワード作成が完了しました！")
            print(f"結果: {result}")
        else:
            print("❌ サブキーワード作成に失敗しました。")
    
    except ImportError as e:
        print(f"⚠️  サブキーワード作成システムのインポートに失敗: {e}")
        print("手動でサブキーワード作成を実行してください。")
    except Exception as e:
        print(f"❌ サブキーワード作成中にエラーが発生: {e}")


if __name__ == "__main__":
    # Windows環境での文字エンコーディング設定
    if os.name == 'nt':
        import sys
        sys.stdout.reconfigure(encoding='utf-8')
    
    # 非同期メイン関数の実行
    asyncio.run(main())
