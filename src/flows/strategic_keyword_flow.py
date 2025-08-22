# src/flows/strategic_keyword_flow.py

from src.keyword_hunter import KeywordHunter
from src.sub_keyword_selector import SubKeywordSelector

class StrategicKeywordFlow:
    def __init__(self, keyword_hunter: KeywordHunter, sub_keyword_selector: SubKeywordSelector):
        self.keyword_hunter = keyword_hunter
        self.sub_keyword_selector = sub_keyword_selector

    def run(self, auto_yes: bool = False):
        """
        戦略的キーワードフローを実行する。
        キーワード収集からAIによる構成案設計までを一気通貫で行う。
        """
        print("\n--- [新] 戦略的キーワード選定＆構成案作成フロー ---")
        
        main_keyword = "夏 お酒 ピッタリ"
        if not auto_yes:
            main_keyword_input = input(f"分析したいメインキーワードを入力してください (デフォルト: {main_keyword}): ").strip()
            if main_keyword_input:
                main_keyword = main_keyword_input
        else:
            print(f"分析したいメインキーワードを入力してください (デフォルト: {main_keyword}): {main_keyword} (自動入力)")
        
        if not main_keyword:
            print("メインキーワードが入力されなかったため、処理を中断します。")
            return None, None

        # 1. 網羅的なキーワード収集
        print("\n[ステップ 1/2] 関連キーワードを網羅的に収集中...")
        all_collected_keywords = self.keyword_hunter.gather_all_keywords(main_keyword)
        if not all_collected_keywords:
            print("[NG] キーワードの収集に失敗したため、処理を中断します。")
            return None, None
        print(f"[OK] {len(all_collected_keywords)}個の関連キーワード候補を収集しました。")

        # 2. AIによる記事構成案の設計
        print("\n[ステップ 2/2] AIによる最終的な記事構成案の作成中...")
        article_structure = self.sub_keyword_selector.design_article_structure(main_keyword, all_collected_keywords)
        if not article_structure:
            print("[NG] 記事構成案の設計に失敗したため、処理を中断します。")
            return None, None

        # 3. 結果を分かりやすく表示
        print("\n--- 構成案の設計完了 ---")
        print(f"■ メインキーワード: {main_keyword}")
        print(f"■ 記事タイトル案: {article_structure.get('title', 'N/A')}")
        print("■ 構成案:")
        for h2_section in article_structure.get("outline", []):
            print(f"  見出し(H2): {h2_section.get('h2', 'N/A')}")
            for h3 in h2_section.get('h3', []):
                print(f"    - {h3}")
        
        return main_keyword, article_structure
