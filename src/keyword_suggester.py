# src/keyword_suggester.py
import requests
import json
import time
import re
from typing import List, Set

class KeywordSuggester:
    """
    GoogleサジェストAPIを利用して、関連キーワードを収集するクラス。
    """

    def __init__(self):
        """
        初期化
        """
        print("[OK] KeywordSuggesterの初期化に成功しました。（高速モード）")

    def _fetch_google_suggest(self, query: str) -> List[str]:
        """
        GoogleのサジェストAPIにリクエストを送信し、サジェストキーワードのリストを取得する。
        より安定したJSON形式のレスポンスを返すエンドポイントを使用する。
        """
        if not query:
            return []
        
        # client=psy-ab を指定して、安定したJSON形式で取得
        url = f"https://www.google.com/complete/search?hl=ja&q={query}&client=psy-ab&output=json"
        
        try:
            response = requests.get(url, timeout=10)
            response.raise_for_status()
            
            # レスポンスをJSONとして解析
            data = json.loads(response.text)
            
            # 候補は data[1] のリストの各要素の先頭に格納されている
            # 例: [ "クエリ", [["候補1", 0], ["候補2", 0]], ... ]
            if len(data) > 1 and isinstance(data[1], list):
                suggestions = [item[0] for item in data[1]]
                return suggestions
            
            return []

        except requests.exceptions.RequestException as e:
            print(f"[NG] サジェスト取得中にネットワークエラーが発生しました (クエリ: {query}): {e}")
            return []
        except json.JSONDecodeError:
            # Googleから返されたものがJSONでない場合 (例: HTMLのエラーページ)
            print(f"[NG] サジェスト結果の解析に失敗しました。Googleからの応答がJSON形式ではありません (クエリ: {query})。")
            return []
        except Exception as e:
            print(f"[NG] サジェスト取得中に予期せぬエラーが発生しました (クエリ: {query}): {e}")
            return []

    def get_suggest_keywords(self, main_keyword: str) -> List[str]:
        """
        メインキーワードのみでサジェストキーワードを取得する。
        """
        print(f"メインキーワード「{main_keyword}」のサジェストキーワード収集を開始します。")
        all_suggestions: Set[str] = set()

        suggestions = self._fetch_google_suggest(main_keyword)
        all_suggestions.update(suggestions)
        
        final_list = sorted(list(all_suggestions))
        if main_keyword in final_list:
            final_list.remove(main_keyword)

        print(f"[OK] サジェストキーワードの収集が完了しました。合計 {len(final_list)} 個のキーワードが見つかりました。")
        return final_list
