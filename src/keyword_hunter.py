# src/keyword_hunter.py

from typing import List, Set
from src.serp_analyzer import SerpAnalyzer
from src.keyword_suggester import KeywordSuggester
import time
import concurrent.futures
import concurrent.futures

class KeywordHunter:
    """
    要件定義に基づき、複数のソースから網羅的にキーワードを収集するクラス。
    - Googleサジェスト (基本 + 戦略的拡張)
    - Google検索結果 (PAA, 関連性の高い検索)
    """

    def __init__(self, serp_analyzer: SerpAnalyzer, keyword_suggester: KeywordSuggester):
        self.serp_analyzer = serp_analyzer
        self.keyword_suggester = keyword_suggester
        # 戦略的キーワード拡張のための、より厳選されたリスト
        self.strategic_expansion_words = [
            "おすすめ", "比較", "ランキング", "選び方",  # 購入意図
            "やり方", "使い方",                          # 方法・実行意図
            "デメリット", "注意点", "口コミ",            # 懸念・比較検討意図
            "とは"                                     # 知識意図
        ]
        print("[OK] KeywordHunterの初期化に成功しました。（戦略的収集モード v2）")

    def gather_all_keywords(self, main_keyword: str) -> List[str]:
        print(f"\n--- キーワードハンターが「{main_keyword}」の関連キーワードを動的に収集します ---")
        
        # 【改修済み】古いSERP API処理を削除し、モード10のシステムの結果を使用
        print("\n【改修済み】古いSERP API処理は削除され、モード10のシステムの結果を使用します")
        
        # モード10の結果からキーワードを抽出
        try:
            import glob
            import os
            seo_files = glob.glob("seo_results/seo_content_*.txt")
            if seo_files:
                # 最新のファイルを取得
                latest_file = max(seo_files, key=os.path.getctime)
                with open(latest_file, 'r', encoding='utf-8') as f:
                    content_lines = f.readlines()
                
                # 番号を除去してコンテンツのみを抽出
                keywords = []
                for line in content_lines:
                    if line.strip() and '. ' in line:
                        content = line.split('. ', 1)[1].strip()
                        if content:
                            keywords.append(content)
                
                print(f"✅ モード10の結果から{len(keywords)}個のキーワードを抽出しました")
                print(f"📁 読み込みファイル: {latest_file}")
                
                # キーワード一覧を表示
                print(f"\n【抽出されたキーワード一覧】")
                for i, keyword in enumerate(keywords, 1):
                    print(f"  {i:2d}. {keyword}")
                
                return keywords
            else:
                print("⚠️ モード10の結果ファイルが見つかりません。デフォルトキーワードを使用します。")
                # フォールバック：デフォルトの戦略的キーワード
                default_keywords = [
                    f"{main_keyword} おすすめ",
                    f"{main_keyword} 比較",
                    f"{main_keyword} ランキング",
                    f"{main_keyword} 選び方",
                    f"{main_keyword} 使い方",
                    f"{main_keyword} 口コミ",
                    f"{main_keyword} とは"
                ]
                print(f"✅ デフォルトキーワード{len(default_keywords)}個を使用します")
                return default_keywords
                
        except Exception as e:
            print(f"⚠️ キーワード抽出でエラーが発生しました: {e}")
            print("デフォルトキーワードを使用します。")
            # フォールバック：デフォルトの戦略的キーワード
            default_keywords = [
                f"{main_keyword} おすすめ",
                f"{main_keyword} 比較",
                f"{main_keyword} ランキング",
                f"{main_keyword} 選び方",
                f"{main_keyword} 使い方",
                f"{main_keyword} 口コミ",
                f"{main_keyword} とは"
            ]
            return default_keywords
