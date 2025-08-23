# test_h3_generation.py
# H2とH3のタグセット生成テスト

import asyncio
import json
from pathlib import Path

# テスト用のモッククラス（実際のGemini APIを使わずにテスト）
class MockGeminiGenerator:
    def generate(self, prompts, model_type="flash", timeout=180):
        # テスト用の固定レスポンス
        return '''```json
{
  "title": "プログラミング学習 おすすめの完全ガイド",
  "meta_description": "初心者から上級者まで、プログラミング学習の選び方と効果的な方法を徹底解説",
  "tags": "プログラミング,学習方法,おすすめ,初心者,スキルアップ",
  "outline": [
    {
      "h2": "「プログラミング学習 おすすめ」の基本情報",
      "h3": [
        "学習の基本と効果的なアプローチ",
        "人気の理由と他との違い",
        "レベル別の学習方法と特徴",
        "学習時の注意点とよくある失敗",
        "初心者向けの解説とよくある質問",
        "失敗しない学習方法の選び方"
      ]
    },
    {
      "h2": "「プログラミング学習 おすすめ」の具体的な活用法",
      "h3": [
        "学習環境の準備と必要なツール",
        "効果的な学習スケジュールの立て方",
        "継続的な学習のコツとモチベーション維持",
        "学習の壁とその乗り越え方",
        "実践的なプロジェクトの進め方",
        "プログラミング学習 おすすめの総まとめ"
      ]
    }
  ]
}
```'''

class MockPromptManager:
    def create_outline_prompt(self, main_keyword, sub_keywords):
        return f"テスト用プロンプト: {main_keyword}"

# テスト用のSubKeywordSelector
class TestSubKeywordSelector:
    def __init__(self):
        self.gemini_generator = MockGeminiGenerator()
        self.prompt_manager = MockPromptManager()
    
    def _extract_json_from_text(self, text: str):
        """JSONを抽出"""
        try:
            match = text.find('```json')
            if match != -1:
                start = match + 7
                end = text.find('```', start)
                if end != -1:
                    json_str = text[start:end].strip()
                    return json.loads(json_str)
            return None
        except Exception as e:
            print(f"JSON抽出エラー: {e}")
            return None
    
    def design_article_structure(self, main_keyword: str, suggest_list: list[str]):
        """記事構成案を生成"""
        print(f"  -> テスト用AIが「{main_keyword}」の記事構成案を生成中...")
        
        response = self.gemini_generator.generate([""])
        article_structure = self._extract_json_from_text(response)
        
        if article_structure:
            print("    [OK] テスト用記事構成案の生成が完了しました。")
            return article_structure
        else:
            print("    [NG] 記事構成案の生成に失敗しました。")
            return None

def test_h3_generation():
    """H3生成のテスト"""
    print("=== H2・H3タグセット生成テスト ===")
    
    # テスト用キーワード
    test_keywords = [
        "プログラミング学習 おすすめ",
        "料理 作り方",
        "健康管理 効果",
        "旅行 プランニング"
    ]
    
    selector = TestSubKeywordSelector()
    
    for main_keyword in test_keywords:
        print(f"\n{'='*60}")
        print(f"テストキーワード: {main_keyword}")
        print(f"{'='*60}")
        
        # 汎用的なサブキーワード候補
        suggest_list = [
            "基本知識", "選び方", "使用方法", "注意点",
            "効果", "メリット", "デメリット", "コツ"
        ]
        
        # 記事構成案を生成
        result = selector.design_article_structure(main_keyword, suggest_list)
        
        if result:
            print("\n=== 生成されたH2・H3構造 ===")
            print(f"タイトル: {result.get('title', 'N/A')}")
            print(f"メタ説明: {result.get('meta_description', 'N/A')}")
            print(f"タグ: {result.get('tags', 'N/A')}")
            
            print("\n=== H2・H3見出しの詳細 ===")
            h3_count = 0
            for i, section in enumerate(result.get("outline", []), 1):
                print(f"\n【H2-{i}】{section.get('h2', 'N/A')}")
                for j, h3 in enumerate(section.get("h3", []), 1):
                    h3_count += 1
                    print(f"  H3-{h3_count}: {h3}")
            
            print(f"\n📊 統計情報:")
            print(f"  - 総H3見出し数: {h3_count}")
            print(f"  - H2セクション数: {len(result.get('outline', []))}")
            
            # 禁止ワードチェック（メインキーワードの単語がH3-1〜H3-11に含まれていないか）
            main_words = main_keyword.split()
            forbidden_violations = []
            
            for i, section in enumerate(result.get("outline", [])):
                for j, h3 in enumerate(section.get("h3", [])):
                    h3_num = i * 6 + j + 1
                    if h3_num <= 11:  # H3-1〜H3-11
                        for word in main_words:
                            if word in h3:
                                forbidden_violations.append(f"H3-{h3_num}: {h3} (禁止ワード: {word})")
            
            if forbidden_violations:
                print(f"\n⚠️  禁止ワードルール違反:")
                for violation in forbidden_violations:
                    print(f"    {violation}")
            else:
                print(f"\n✅ 禁止ワードルールを完全に遵守しています！")
            
        else:
            print("❌ 生成に失敗しました。")
        
        print("\n" + "-"*50)

if __name__ == "__main__":
    test_h3_generation()
