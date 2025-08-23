# src/yahoo_keyword_hunter.py
# Yahoo検索ベースのキーワード収集システム（SERP API不要）

import asyncio
from typing import List, Set
from src.yahoo_keyword_collector import YahooKeywordCollector
import logging

# ロガーの設定
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

class YahooKeywordHunter:
    """
    Yahoo検索ベースで複数のソースから網羅的にキーワードを収集するクラス。
    SERP APIを使わず、HTML解析でキーワードを収集します。
    
    - Yahoo検索結果からの関連キーワード抽出
    - 戦略的キーワード拡張（並列実行）
    - 深掘りキーワード収集
    """

    def __init__(self, yahoo_collector: YahooKeywordCollector):
        self.yahoo_collector = yahoo_collector
        
        # 戦略的キーワード拡張のための、より厳選されたリスト
        self.strategic_expansion_words = [
            "おすすめ", "比較", "ランキング", "選び方",  # 購入意図
            "やり方", "使い方",                          # 方法・実行意図
            "デメリット", "注意点", "口コミ",            # 懸念・比較検討意図
            "とは"                                     # 知識意図
        ]
        
        print("[OK] YahooKeywordHunterの初期化に成功しました。（Yahoo検索ベース・SERP API不要）")

    async def gather_all_keywords(self, main_keyword: str) -> List[str]:
        """
        メインキーワードから関連キーワードを網羅的に収集する。
        既存のKeywordHunterと同じインターフェースを提供。
        """
        print(f"\n=== 「{main_keyword}」の関連キーワード収集開始 ===")
        
        all_keywords: Set[str] = set()
        
        # 1. メインキーワードの基本検索から関連キーワードを収集
        print("\n[ステップ1/3] メインキーワードの基本検索から関連キーワードを収集中...")
        basic_keywords = await self._collect_basic_keywords(main_keyword)
        all_keywords.update(basic_keywords)
        print(f"  -> {len(basic_keywords)}個の基本キーワードを収集しました。")
        
        # 2. 戦略的キーワード拡張（並列実行）
        print("\n[ステップ2/3] 戦略的キーワード拡張を並列実行中...")
        strategic_keywords = await self._collect_strategic_keywords(main_keyword)
        all_keywords.update(strategic_keywords)
        print(f"  -> {len(strategic_keywords)}個の戦略的キーワードを収集しました。")
        
        # 3. 関連検索の深掘り
        print("\n[ステップ3/3] 関連検索の深掘りを実行中...")
        deep_keywords = await self._collect_deep_keywords(main_keyword, list(all_keywords)[:10])
        all_keywords.update(deep_keywords)
        print(f"  -> {len(deep_keywords)}個の深掘りキーワードを収集しました。")
        
        # 結果を整理
        final_keywords = sorted(list(all_keywords))
        print(f"\n✅ キーワード収集完了！ 合計 {len(final_keywords)}個のユニークキーワードを収集しました。")
        
        return final_keywords
    
    async def _collect_basic_keywords(self, main_keyword: str) -> List[str]:
        """メインキーワードの基本検索から関連キーワードを収集"""
        return await self.yahoo_collector._collect_basic_keywords(main_keyword)
    
    async def _collect_strategic_keywords(self, main_keyword: str) -> List[str]:
        """戦略的キーワード拡張を並列実行"""
        return await self.yahoo_collector._collect_strategic_keywords(main_keyword)
    
    async def _collect_deep_keywords(self, main_keyword: str, seed_keywords: List[str]) -> List[str]:
        """収集されたキーワードからさらに深掘り"""
        return await self.yahoo_collector._collect_deep_keywords(main_keyword, seed_keywords)
    
    def get_strategic_expansion_words(self) -> List[str]:
        """戦略的拡張ワードのリストを取得"""
        return self.strategic_expansion_words.copy()
    
    def add_strategic_word(self, word: str):
        """戦略的拡張ワードを追加"""
        if word not in self.strategic_expansion_words:
            self.strategic_expansion_words.append(word)
            print(f"[INFO] 戦略的拡張ワード「{word}」を追加しました。")
    
    def remove_strategic_word(self, word: str):
        """戦略的拡張ワードを削除"""
        if word in self.strategic_expansion_words:
            self.strategic_expansion_words.remove(word)
            print(f"[INFO] 戦略的拡張ワード「{word}」を削除しました。")

# テスト用コード
async def test_yahoo_keyword_hunter():
    """YahooKeywordHunterのテスト"""
    print("=== YahooKeywordHunterテスト ===")
    
    # YahooKeywordCollectorを初期化
    yahoo_collector = YahooKeywordCollector()
    
    # YahooKeywordHunterを初期化
    hunter = YahooKeywordHunter(yahoo_collector)
    
    # テスト用キーワード
    test_keywords = [
        "プログラミング学習",
        "料理 作り方"
    ]
    
    for keyword in test_keywords:
        print(f"\n{'='*60}")
        print(f"テストキーワード: {keyword}")
        print(f"{'='*60}")
        
        # キーワード収集を実行
        collected_keywords = await hunter.gather_all_keywords(keyword)
        
        print(f"\n収集されたキーワード（上位15件）:")
        for i, kw in enumerate(collected_keywords[:15], 1):
            print(f"  {i:2d}. {kw}")
        
        if len(collected_keywords) > 15:
            print(f"  ... 他 {len(collected_keywords) - 15}件")
        
        print(f"\n合計: {len(collected_keywords)}件")
        
        # 戦略的拡張ワードの確認
        strategic_words = hunter.get_strategic_expansion_words()
        print(f"\n戦略的拡張ワード: {', '.join(strategic_words)}")
        
        # レート制限回避
        await asyncio.sleep(2)
    
    # キャッシュクリーンアップ
    yahoo_collector.clear_cache()

if __name__ == "__main__":
    asyncio.run(test_yahoo_keyword_hunter())
