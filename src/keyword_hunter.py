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
        
        # ステップ1: 初期シードとなるキーワードを収集
        print("\n[ステップ1/3] 初期シードとなるキーワード（関連検索・PAA）を収集中...")
        initial_keywords: Set[str] = set()

        related_searches = self.serp_analyzer.get_related_searches(main_keyword)
        initial_keywords.update(related_searches)
        print(f"  -> {len(related_searches)}個の「関連検索」をシードに追加しました。")

        related_questions = self.serp_analyzer.get_related_questions(main_keyword)
        initial_keywords.update(related_questions)
        print(f"  -> {len(related_questions)}個の「PAA」をシードに追加しました。")

        if not initial_keywords:
            print("[WARN] 初期シードとなるキーワードが見つかりませんでした。")
            return [main_keyword]

        print(f"  [OK] 合計 {len(initial_keywords)} 個のユニークなシードキーワードを確保しました。")

        # ステップ2: シードキーワードを元に、関連キーワードを並列で深掘り
        print("\n[ステップ2/3] シードキーワードを元に関連キーワードを並列で深掘りします...")
        expanded_keywords: Set[str] = set()
        
        seed_keywords_to_expand = sorted(list(initial_keywords))
        print(f"  -> {len(seed_keywords_to_expand)}個のシードを元に深掘り中...")
        with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
            future_to_seed = {executor.submit(self.serp_analyzer.get_related_searches, seed): seed for seed in seed_keywords_to_expand}
            for future in concurrent.futures.as_completed(future_to_seed):
                seed = future_to_seed[future]
                try:
                    newly_found_keywords = future.result()
                    if newly_found_keywords:
                        expanded_keywords.update(newly_found_keywords)
                except Exception as exc:
                    print(f"  -> [WARN] シード「{seed}」の拡張中にエラーが発生しました: {exc}")

        print(f"  -> {len(expanded_keywords)}個の新たなキーワードを発見しました。")

        # ステップ3: 全てのキーワードを統合
        print("\n[ステップ3/3] 全てのキーワードを統合しています...")
        final_keywords: Set[str] = set()
        final_keywords.update(initial_keywords)
        final_keywords.update(expanded_keywords)

        final_keyword_list = sorted(list(final_keywords))
        print(f"\n--- キーワード収集完了 ---")
        print(f"合計 {len(final_keyword_list)} 個のユニークなキーワード候補を収集しました。")
        
        # 収集したキーワード全てをログとして出力
        print(f"\n【収集されたキーワード一覧】")
        for i, keyword in enumerate(final_keyword_list, 1):
            print(f"  {i:2d}. {keyword}")
        print(f"\n[OK] {len(final_keyword_list)}個の関連キーワード候補を収集しました。")
        
        return final_keyword_list
