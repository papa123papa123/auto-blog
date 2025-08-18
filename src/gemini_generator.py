# src/gemini_generator.py

import google.generativeai as genai
from google.api_core.exceptions import ResourceExhausted, DeadlineExceeded
import os
from typing import Callable, List, Any
import time
from PIL import Image
import re

class GeminiGenerator:
    """
    Gemini APIとの通信を管理するクラス。
    高性能なProモデルと、高速・安価なFlashモデルの切り替えに対応。
    """

    def __init__(self):
        try:
            api_key = os.getenv("GEMINI_API_KEY")
            if not api_key:
                raise ValueError("環境変数 'GEMINI_API_KEY' が設定されていません。")

            genai.configure(api_key=api_key)
            # 両方のモデルを初期化
            self.pro_model = genai.GenerativeModel("gemini-1.5-pro-latest")
            self.flash_model = genai.GenerativeModel("gemini-1.5-flash-latest")
            
            self.chat = None
            self.chat_model_type = "pro" # チャットは常にProモデルを使用

        except Exception as e:
            print(f"[NG] GeminiGeneratorの初期化中にエラーが発生しました: {e}")
            raise
        print(f"[OK] GeminiGeneratorの初期化に成功しました。（Pro/Flash両対応）")

    def _execute_api_call_with_retry(self, api_call_func: Callable, timeout: int) -> str:
        max_retries = 4
        wait_time = 5
        for attempt in range(max_retries):
            try:
                response = api_call_func()
                time.sleep(1) 
                return response.text
            except ResourceExhausted as e:
                print(f"  L [WARN] API利用制限（429エラー）を検知しました。 (試行 {attempt + 1}/{max_retries})")
                if attempt < max_retries - 1:
                    print(f"  L {wait_time}秒待機して再試行します...")
                    time.sleep(wait_time)
                    wait_time *= 2
                else:
                    print("[NG] リトライ上限に達しました。処理を中断します。")
                    return f"エラー: APIの利用制限を解消できませんでした。詳細: {e}"
            except DeadlineExceeded:
                error_message = f"[NG] Gemini APIがタイムアウトしました ({timeout}秒)。"
                print(error_message)
                return f"エラー: {error_message}"
            except Exception as e:
                error_message = str(e)
                print(f"[NG] Gemini APIでエラーが発生しました: {error_message}")
                return f"エラー: 予期せぬAPIエラーが発生しました。詳細: {error_message}"
        return "エラー: リトライ処理が正常に完了しませんでした。"

    def start_new_chat(self, model_type: str = "pro"):
        """チャットセッションを開始する。デフォルトはProモデル。"""
        self.chat_model_type = model_type
        model_to_use = self.pro_model if model_type == "pro" else self.flash_model
        self.chat = model_to_use.start_chat(history=[])
        print(f"[CHAT] 新しいチャットセッションを開始しました。（モデル: {model_type}）")

    def send_message_to_chat(self, message: str, timeout: int = 600) -> str:
        if self.chat is None:
            self.start_new_chat(self.chat_model_type)
        
        print(f"  L プロンプトをAPIに送信します... (モデル: {self.chat_model_type}, タイムアウト: {timeout}秒)")
        api_call = lambda: self.chat.send_message(
            message,
            request_options={'timeout': timeout}
        )
        return self._execute_api_call_with_retry(api_call, timeout)

    def generate(self, prompt_parts: List[Any], model_type: str = "pro", timeout: int = 600) -> str:
        """
        コンテンツを生成する。'pro'または'flash'モデルを指定可能。
        """
        model_to_use = self.pro_model if model_type == "pro" else self.flash_model
        print(f"  L Gemini APIに応答を待っています... (モデル: {model_type}, タイムアウト: {timeout}秒)")
        
        contents = []
        for part in prompt_parts:
            # 文字列であり、かつ実在するファイルパスであり、かつ画像ファイル拡張子を持つ場合のみ画像として読み込む
            if isinstance(part, str) and os.path.isfile(part):
                image_extensions = ['.png', '.jpg', '.jpeg', '.webp', '.gif', '.bmp']
                if any(part.lower().endswith(ext) for ext in image_extensions):
                    try:
                        print(f"  L 画像を読み込んでいます: {part}")
                        img = Image.open(part)
                        contents.append(img)
                    except Exception as e:
                        return f"エラー: 画像ファイル '{part}' の読み込みに失敗しました。詳細: {e}"
                else:
                    contents.append(part)
            else:
                contents.append(part)

        api_call = lambda: model_to_use.generate_content(
            contents,
            request_options={'timeout': timeout}
        )
        return self._execute_api_call_with_retry(api_call, timeout)
