# test_h3_local_fixed.py
# 修正されたローカルH3生成テスト（API不要）

import json
import re

class FixedLocalH3Generator:
    """修正されたローカルH3見出し生成クラス"""
    
    def __init__(self):
        # キーワードカテゴリの定義（より正確に）
        self.categories = {
            "product_service": {
                "indicators": ["おすすめ", "比較", "ランキング", "選び方", "購入", "レビュー"],
                "h3_templates": {
                    "h2_1": "基本情報",
                    "h3_1": [
                        "基本的な仕組みと効果",
                        "人気の理由と特徴", 
                        "種類と選び方のポイント",
                        "購入時の注意点",
                        "よくある質問と回答",
                        "失敗しない選び方"
                    ],
                    "h2_2": "具体的な活用法",
                    "h3_2": [
                        "購入場所と価格の相場",
                        "効果的な使用方法",
                        "お手入れと保管方法",
                        "トラブル対処法",
                        "カスタマイズのアイデア",
                        "総まとめ"
                    ]
                }
            },
            "how_to": {
                "indicators": ["やり方", "作り方", "方法", "手順", "コツ", "テクニック"],
                "h3_templates": {
                    "h2_1": "基本知識",
                    "h3_1": [
                        "基本的な手順と流れ",
                        "準備と必要なもの",
                        "効果的なアプローチ",
                        "よくある失敗と対策",
                        "成功のポイント",
                        "初心者向けの解説"
                    ],
                    "h2_2": "実践と応用",
                    "h3_2": [
                        "応用と発展方法",
                        "カスタマイズのコツ",
                        "トラブル対処法",
                        "実践のアイデア",
                        "組み合わせの提案",
                        "総まとめ"
                    ]
                }
            },
            "knowledge": {
                "indicators": ["効果", "メリット", "デメリット", "とは", "意味", "仕組み"],
                "h3_templates": {
                    "h2_1": "基本概念",
                    "h3_1": [
                        "基本的な定義と仕組み",
                        "メカニズムと働き",
                        "種類と特徴",
                        "メリットとデメリット",
                        "使用シーンと活用法",
                        "選び方のポイント"
                    ],
                    "h2_2": "実践と活用",
                    "h3_2": [
                        "よくある疑問と回答",
                        "実践での活用方法",
                        "応用と発展",
                        "カスタマイズのアイデア",
                        "組み合わせの提案",
                        "総まとめ"
                    ]
                }
            },
            "planning": {
                "indicators": ["プランニング", "計画", "戦略", "管理", "設計"],
                "h3_templates": {
                    "h2_1": "基本情報",
                    "h3_1": [
                        "基本的な考え方と目的",
                        "計画の重要性と効果",
                        "種類とアプローチの違い",
                        "計画時の注意点",
                        "よくある失敗と対策",
                        "成功のポイント"
                    ],
                    "h2_2": "具体的な実践方法",
                    "h3_2": [
                        "計画の立て方と手順",
                        "効果的な実行方法",
                        "進捗管理と調整",
                        "トラブル対処法",
                        "改善と最適化",
                        "総まとめ"
                    ]
                }
            }
        }
    
    def categorize_keyword(self, keyword: str) -> str:
        """キーワードのカテゴリを正確に判定"""
        keyword_lower = keyword.lower()
        
        # より詳細な判定ロジック
        for category, data in self.categories.items():
            if any(indicator in keyword_lower for indicator in data["indicators"]):
                return category
        
        # デフォルトカテゴリの判定
        if any(word in keyword_lower for word in ["学習", "勉強", "教育"]):
            return "how_to"
        elif any(word in keyword_lower for word in ["健康", "美容", "運動"]):
            return "knowledge"
        else:
            return "planning"  # 汎用的な計画系
    
    def generate_h3_structure(self, main_keyword: str) -> dict:
        """キーワードに応じたH3構造を生成"""
        # カテゴリを判定
        category = self.categorize_keyword(main_keyword)
        templates = self.categories[category]["h3_templates"]
        
        # メインキーワードを構成単語に分割
        main_words = re.split(r'[\s　]+', main_keyword.strip())
        
        # 禁止ワードチェック用の単語リスト
        forbidden_words = [word for word in main_words if word]
        
        # H3見出しを生成（禁止ワードを使用しない）
        h3_1 = self._generate_safe_h3s(templates["h3_1"], forbidden_words, main_keyword)
        h3_2 = self._generate_safe_h3s(templates["h3_2"], forbidden_words, main_keyword)
        
        # 最後のH3（まとめ）にはメインキーワードを含める
        h3_2[-1] = f"{main_keyword}の総まとめ"
        
        # 構造を構築
        structure = {
            "title": f"{main_keyword}の完全ガイド",
            "meta_description": f"{main_keyword}について、基本から実践まで詳しく解説します",
            "tags": f"{main_keyword.replace(' ', ',')},ガイド,解説,実践",
            "outline": [
                {
                    "h2": f"「{main_keyword}」の{templates['h2_1']}",
                    "h3": h3_1
                },
                {
                    "h2": f"「{main_keyword}」の{templates['h2_2']}",
                    "h3": h3_2
                }
            ]
        }
        
        return structure
    
    def _generate_safe_h3s(self, template_h3s: list, forbidden_words: list, main_keyword: str) -> list:
        """禁止ワードを使用しないH3見出しを生成"""
        safe_h3s = []
        
        for template in template_h3s:
            # テンプレートから禁止ワードを除去
            safe_h3 = template
            for word in forbidden_words:
                if word in safe_h3:
                    # 禁止ワードを同義語に置換
                    safe_h3 = safe_h3.replace(word, self._get_synonym(word))
            
            safe_h3s.append(safe_h3)
        
        return safe_h3s
    
    def _get_synonym(self, word: str) -> str:
        """禁止ワードの同義語を取得"""
        synonyms = {
            "おすすめ": "推奨",
            "比較": "対比",
            "ランキング": "順位",
            "選び方": "選択方法",
            "購入": "買い方",
            "やり方": "方法",
            "作り方": "作成方法",
            "方法": "アプローチ",
            "手順": "ステップ",
            "コツ": "ポイント",
            "効果": "効能",
            "メリット": "利点",
            "デメリット": "欠点",
            "とは": "について",
            "意味": "定義",
            "プランニング": "計画",
            "計画": "設計",
            "戦略": "方針",
            "管理": "運営",
            "学習": "習得",
            "勉強": "学習",
            "教育": "指導",
            "健康": "体調",
            "美容": "美しさ",
            "運動": "活動"
        }
        return synonyms.get(word, word)

def test_fixed_h3_generation():
    """修正されたH3生成のテスト"""
    print("=== 修正されたローカルH3生成テスト（API不要） ===")
    
    # テスト用キーワード（様々なカテゴリをテスト）
    test_keywords = [
        "プログラミング学習 おすすめ",  # product_service
        "料理 作り方",                  # how_to
        "健康管理 効果",                # knowledge
        "旅行 プランニング",            # planning
        "英語 勉強方法",                # how_to
        "投資 戦略",                    # planning
        "ダイエット やり方"             # how_to
    ]
    
    generator = FixedLocalH3Generator()
    
    for main_keyword in test_keywords:
        print(f"\n{'='*70}")
        print(f"テストキーワード: {main_keyword}")
        print(f"{'='*70}")
        
        # H3構造を生成
        result = generator.generate_h3_structure(main_keyword)
        
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
            
            # 禁止ワードチェック
            main_words = re.split(r'[\s　]+', main_keyword.strip())
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
            
            # カテゴリ判定の表示
            category = generator.categorize_keyword(main_keyword)
            print(f"\n🏷️  キーワードカテゴリ: {category}")
            
            # キーワードと内容の一致確認
            title_keywords = result.get('title', '')
            if main_keyword in title_keywords:
                print(f"✅ タイトルにメインキーワードが正しく含まれています")
            else:
                print(f"❌ タイトルにメインキーワードが含まれていません")
            
        else:
            print("❌ 生成に失敗しました。")
        
        print("\n" + "-"*50)

if __name__ == "__main__":
    test_fixed_h3_generation()
