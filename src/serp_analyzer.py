# src/serp_analyzer.py

import requests
import time
from typing import List, Dict, Any, Optional

class SerpAnalyzer:
    def __init__(self, api_key: str):
        if not api_key or not isinstance(api_key, str):
            raise ValueError("SerpAPIのAPIキーが無効です。")
        self.api_key = api_key
        
        # 弱いライバルの定義
        self.qa_sites = [
            "chiebukuro.yahoo.co.jp", "okwave.jp", "oshiete.goo.ne.jp", 
            "komachi.yomiuri.co.jp", "qa.itmedia.co.jp", "teratail.com", 
            "stackexchange.com", "quora.com", "reddit.com"
        ]
        self.sns_sites = [
            "x.com", "twitter.com", "instagram.com", "facebook.com", 
            "youtube.com", "tiktok.com", "pinterest.jp", "pinterest.com"
        ]
        self.free_blog_sites = [
            "ameblo.jp", "hatenablog.com", "note.com", "livedoor.jp", 
            "fc2.com", "seesaa.net", "jugem.jp", "exblog.jp", 
            "rakuten.co.jp/plaza", "goo.ne.jp/blog"
        ]
        self.all_weak_sites = self.qa_sites + self.sns_sites + self.free_blog_sites
        print("[OK] SerpAnalyzerの初期化に成功しました。")

    def _get_api_response(self, query: str) -> Optional[Dict[str, Any]]:
        """指定されたクエリでSerpAPIを呼び出し、JSONレスポンスを返す"""
        params = {
            'engine': 'google',
            'q': query,
            'api_key': self.api_key,
            'gl': 'jp',
            'hl': 'ja'
        }
        try:
            response = requests.get('https://serpapi.com/search.json', params=params)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            print(f"[NG] APIリクエストエラー: {e}")
            return None

    def analyze_top10_serps(self, keyword: str):
        """
        キーワードの競合性を分析する。(既存のメソッド)
        """
        allintitle_count, intitle_count, weak_ranks = None, None, {'Q&Aサイト': None, 'SNS': None, '無料ブログ': None}
        try:
            # allintitle (ダブルクォーテーションを削除)
            allintitle_data = self._get_api_response(f'allintitle:{keyword}')
            if allintitle_data and 'search_information' in allintitle_data:
                allintitle_count = allintitle_data['search_information'].get('total_results', 0)
            time.sleep(1)
            
            # intitle (ダブルクォーテーションを削除)
            intitle_data = self._get_api_response(f'intitle:{keyword}')
            if intitle_data and 'search_information' in intitle_data:
                intitle_count = intitle_data['search_information'].get('total_results', 0)
            time.sleep(1)

            # standard search for weak sites
            standard_data = self._get_api_response(keyword)
            if standard_data and 'organic_results' in standard_data:
                for result in standard_data['organic_results']:
                    rank, link = result.get('position'), result.get('link', '')
                    if not rank or rank > 10: continue
                    if weak_ranks['Q&Aサイト'] is None and any(site in link for site in self.qa_sites): weak_ranks['Q&Aサイト'] = rank
                    if weak_ranks['SNS'] is None and any(site in link for site in self.sns_sites): weak_ranks['SNS'] = rank
                    if weak_ranks['無料ブログ'] is None and any(site in link for site in self.free_blog_sites): weak_ranks['無料ブログ'] = rank
        except Exception as e:
            print(f"[NG] 競合サイトの分析中にエラー: {e}")
        return allintitle_count, intitle_count, weak_ranks

    def get_strong_competitors_info(self, keyword: str, num_results: int = 10) -> List[Dict[str, str]]:
        """
        キーワードで検索し、弱いサイトを除外した上位の競合サイト情報（URL, title, snippet）のリストを返す。
        インテリジェント・サイトセレクションのために、情報をリッチにする。
        """
        print(f"  -> 「{keyword}」で、競合サイト情報を検索中...")
        data = self._get_api_response(keyword)
        if not data or 'organic_results' not in data:
            return []

        strong_competitors = []
        for result in data['organic_results']:
            link = result.get('link', '')
            title = result.get('title', '')
            snippet = result.get('snippet', '')

            if link and title and not any(weak_site in link for weak_site in self.all_weak_sites):
                strong_competitors.append({
                    "url": link,
                    "title": title,
                    "snippet": snippet
                })
            
            if len(strong_competitors) >= num_results:
                break
        
        time.sleep(1)
        return strong_competitors

    def get_strong_competitor_urls(self, keyword: str, num_results: int = 3) -> List[str]:
        """
        [旧メソッド・互換性のために残置]
        キーワードで検索し、弱いサイトを除外した上位のURLリストを返す。
        新しい処理では get_strong_competitors_info を使用することを推奨。
        """
        competitors_info = self.get_strong_competitors_info(keyword, num_results)
        return [info["url"] for info in competitors_info]

    def get_related_questions(self, keyword: str) -> List[str]:
        """
        「他の人はこちらも質問 (PAA)」を取得する。
        """
        print(f"  -> 「{keyword}」の「他の人はこちらも質問」を取得中...")
        data = self._get_api_response(keyword)
        
        if data and 'related_questions' in data:
            questions = [item['question'] for item in data['related_questions'] if 'question' in item]
            print(f"    [OK] {len(questions)}件の質問を取得しました。")
            time.sleep(1)
            return questions
        
        print("    [INFO] 「他の人はこちらも質問」は見つかりませんでした。")
        time.sleep(1)
        return []

    def get_related_searches(self, keyword: str) -> List[str]:
        """
        「関連性の高い検索」のキーワードを取得する。
        """
        data = self._get_api_response(keyword)

        if data and 'related_searches' in data:
            searches = [item['query'] for item in data['related_searches'] if 'query' in item]
            print(f"    [OK] {len(searches)}件の関連キーワードを取得しました。")
            time.sleep(1)
            return searches

        print("    [INFO] 「関連性の高い検索」は見つかりませんでした。")
        time.sleep(1)
        return []

# テスト用のコード
if __name__ == '__main__':
    import os
    from dotenv import load_dotenv

    # .envファイルから環境変数を読み込む (プロジェクトルートに.envがあると仮定)
    # このテストを実行する際は、プロジェクトルートに SERPAPI_API_KEY を設定した .env ファイルが必要です。
    dotenv_path = os.path.join(os.path.dirname(__file__), '..', '.env')
    load_dotenv(dotenv_path=dotenv_path)
    
    serp_api_key = os.getenv("SERPAPI_API_KEY")

    if not serp_api_key:
        print("[NG] 環境変数 SERPAPI_API_KEY が設定されていません。テストをスキップします。")
    else:
        analyzer = SerpAnalyzer(api_key=serp_api_key)
        main_keyword = "プログラミングスクール"

        print(f"\n--- 「{main_keyword}」のPAA (他の人はこちらも質問) ---")
        related_questions = analyzer.get_related_questions(main_keyword)
        if related_questions:
            for q in related_questions:
                print(f"- {q}")
        
        print(f"\n--- 「{main_keyword}」の関連性の高い検索 ---")
        related_searches = analyzer.get_related_searches(main_keyword)
        if related_searches:
            for s in related_searches:
                print(f"- {s}")