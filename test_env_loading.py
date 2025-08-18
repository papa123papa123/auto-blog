# test_env_loading.py
import os
from dotenv import load_dotenv
from pathlib import Path

print("--- .envファイル読み込みテストを開始 ---")

# プロジェクトルートにある .env ファイルのパスを明示的に指定
env_path = Path(__file__).resolve().parent / '.env'

if env_path.exists():
    print(f"発見した.envファイルのパス: {env_path}")
    load_dotenv(dotenv_path=env_path)
    
    gemini_api_key = os.getenv("GEMINI_API_KEY")

    if gemini_api_key:
        print("\n[成功] GEMINI_API_KEYの読み込みに成功しました。")
        # キーの一部だけを表示して、読み込めていることを確認
        print(f"  -> 読み込まれたキー（一部）: {gemini_api_key[:4]}...{gemini_api_key[-4:]}")
    else:
        print("\n[失敗] .envファイル内に GEMINI_API_KEY が見つかりませんでした。")
else:
    print(f"\n[失敗] .envファイルがパス '{env_path}' に見つかりませんでした。")

print("\n--- テスト完了 ---")

