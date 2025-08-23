# src/sub_keyword_selector.py

import json
import re
from src.gemini_generator import GeminiGenerator
from src.prompt_manager import PromptManager
from typing import List, Dict, Any

class SubKeywordSelector:
    def __init__(self, gemini_generator: GeminiGenerator, prompt_manager: PromptManager):
        self.gemini_generator = gemini_generator
        self.prompt_manager = prompt_manager

    def _extract_json_from_text(self, text: str, is_list: bool = False):
        """マークダウンのコードブロックやテキストからJSONオブジェクトまたはリストを抽出する。"""
        try:
            match = re.search(r'```json\s*([\s\S]*?)\s*```', text, re.DOTALL)
            if match:
                json_str = match.group(1)
            else:
                pattern = r'(\[[\s\S]*\])' if is_list else r'(\{[\s\S]*\})'
                match = re.search(pattern, text, re.DOTALL)
                if match:
                    json_str = match.group(0)
                else:
                    raise json.JSONDecodeError("応答からJSONデータが見つかりませんでした。", text, 0)
            return json.loads(json_str)
        except json.JSONDecodeError as e:
            print(f"    [ERROR] JSONのパースに失敗しました。エラー: {e}")
            print(f"    [DEBUG] 受け取ったテキスト(先頭300文字): {text[:300]}...")
            return None

    def _quick_validate_structure(self, article_structure: Dict[str, Any]) -> bool:
        """
        生成された構成案の基本的な構造を素早く検証（軽量チェック）
        """
        try:
            # 基本的な構造チェック
            if not article_structure.get("outline") or len(article_structure["outline"]) != 2:
                return False
            
            # H3見出しの数チェック
            h3_count = 0
            for section in article_structure["outline"]:
                if not section.get("h3") or not isinstance(section["h3"], list):
                    return False
                h3_count += len(section["h3"])
            
            # 合計12個のH3見出しがあるかチェック
            if h3_count != 12:
                return False
            
            return True
            
        except Exception as e:
            print(f"    [WARN] 構造検証中にエラーが発生: {e}")
            return False

    def design_article_structure(self, main_keyword: str, suggest_list: list[str]) -> Dict[str, Any]:
        """
        最適化されたプロンプトで1ターンで高品質な記事構成案を生成
        """
        print(f"  -> AIが「{main_keyword}」の記事構成案を1ターンで生成中...")
        
        # 最適化されたプロンプトを使用
        prompt = self.prompt_manager.create_outline_prompt(main_keyword, suggest_list)
        response = self.gemini_generator.generate([prompt], model_type="flash", timeout=180)
        
        if not response or response.startswith("エラー:"):
            print(f"    [NG] Geminiからの応答エラー: {response}")
            return None

        # JSON抽出
        article_structure = self._extract_json_from_text(response)
        if not article_structure:
            print("    [NG] 応答のJSON解析に失敗しました。")
            return None
        
        # 軽量な構造検証
        if not self._quick_validate_structure(article_structure):
            print("    [NG] 記事構造の基本形式が不正です。")
            return None
        
        print("    [OK] 1ターンで高品質な記事構成案の生成が完了しました。")
        return article_structure

    def select_sub_keywords(self, main_keyword: str, suggest_list: list[str]) -> List[str]:
        """
        後方互換性のためのメソッド（既存コードとの互換性を保つ）
        """
        article_structure = self.design_article_structure(main_keyword, suggest_list)
        if not article_structure:
            return []
        
        # H3見出しをフラットなリストとして抽出
        sub_keywords = []
        for section in article_structure.get("outline", []):
            sub_keywords.extend(section.get("h3", []))
        
        return sub_keywords

# テスト用コード
if __name__ == "__main__":
    async def test_selector():
        from src.gemini_generator import GeminiGenerator
        from src.prompt_manager import PromptManager
        
        # テスト用の初期化
        gemini_gen = GeminiGenerator()
        prompt_mgr = PromptManager()
        selector = SubKeywordSelector(gemini_gen, prompt_mgr)
        
        # 汎用的なテスト用キーワード（様々なカテゴリをテスト）
        test_keywords = [
            "プログラミング学習 おすすめ",  # 商品・サービス系
            "料理 作り方",                  # 方法・やり方系
            "健康管理 効果",                # 知識・情報系
            "旅行 プランニング"             # 汎用的
        ]
        
        for main_keyword in test_keywords:
            print(f"\n{'='*50}")
            print(f"テストキーワード: {main_keyword}")
            print(f"{'='*50}")
            
            # 汎用的なサブキーワード候補
            suggest_list = [
                "基本知識", "選び方", "使用方法", "注意点",
                "効果", "メリット", "デメリット", "コツ"
            ]
            
            print("1ターン生成テストを開始...")
            result = selector.design_article_structure(main_keyword, suggest_list)
            
            if result:
                print("\n=== 生成結果 ===")
                print(f"タイトル: {result.get('title', 'N/A')}")
                print(f"メタ説明: {result.get('meta_description', 'N/A')}")
                print(f"タグ: {result.get('tags', 'N/A')}")
                
                print("\n=== H3見出し ===")
                h3_count = 0
                for i, section in enumerate(result.get("outline", []), 1):
                    print(f"\nH2-{i}: {section.get('h2', 'N/A')}")
                    for j, h3 in enumerate(section.get("h3", []), 1):
                        h3_count += 1
                        print(f"  H3-{h3_count}: {h3}")
                
                print(f"\n合計H3見出し数: {h3_count}")
            else:
                print("生成に失敗しました。")
            
            print("\n" + "-"*30)
    
    # 非同期テストの実行
    import asyncio
    asyncio.run(test_selector())