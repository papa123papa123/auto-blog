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
        print(f"\n--- キーワードハンターが「{main_keyword}」の関連キーワードを網羅的に収集します ---")
        
        all_keywords: Set[str] = set()

        # 1. メインキーワードの「関連性の高い検索」から収集
        print("\n[ステップ1/3] メインキーワードの関連検索を収集中...")
        related_searches = self.serp_analyzer.get_related_searches(main_keyword)
        all_keywords.update(related_searches)
        print(f"  -> {len(related_searches)}個の関連検索キーワードを追加しました。")

        # 2. 【改善】厳選されたキーワードでの戦略的拡張（SerpAPI使用, 並列実行）
        print("\n[ステップ2/3] 戦略的キーワード拡張を並列実行します...")
        strategic_keywords: Set[str] = set()
        
        print(f"  -> {len(self.strategic_expansion_words)}個の厳選ワードを掛け合わせて並列で深掘り中...")
        with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
            future_to_query = {executor.submit(self.serp_analyzer.get_related_searches, f"{main_keyword} {word}"): f"{main_keyword} {word}" for word in self.strategic_expansion_words}
            for future in concurrent.futures.as_completed(future_to_query):
                query = future_to_query[future]
                try:
                    expanded_keywords = future.result()
                    if expanded_keywords:
                        strategic_keywords.update(expanded_keywords)
                except Exception as exc:
                    print(f"  -> [WARN] クエリ「{query}」の拡張中にエラーが発生しました: {exc}")

        all_keywords.update(strategic_keywords)
        print(f"  -> {len(strategic_keywords)}個の戦略的キーワードを追加しました。")

        # 3. 「他の人はこちらも質問 (PAA)」から収集
        print("\n[ステップ3/3] 「他の人はこちらも質問(PAA)」を収集中...")
        related_questions = self.serp_analyzer.get_related_questions(main_keyword)
        all_keywords.update(related_questions)
        print(f"  -> {len(related_questions)}個のPAAキーワードを追加しました。")

        final_keyword_list = sorted(list(all_keywords))
        print(f"\n--- キーワード収集完了 ---")
        print(f"合計 {len(final_keyword_list)} 個のユニークなキーワード候補を収集しました。")
        
        return final_keyword_list
