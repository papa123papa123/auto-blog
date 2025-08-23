# src/agent_article_system.py
# Cursorエージェント完結型記事作成システム

import json
import asyncio
from pathlib import Path
from typing import List, Dict, Any, Optional
from datetime import datetime
import time

class AgentArticleSystem:
    """Cursorエージェント完結型記事作成システム"""
    
    def __init__(self, output_dir: str = "agent_articles"):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(exist_ok=True)
        
        # 記事作成用のディレクトリ構造
        self.articles_dir = self.output_dir / "articles"
        self.keywords_dir = self.output_dir / "keywords"
        self.prompts_dir = self.output_dir / "prompts"
        self.images_dir = self.output_dir / "images"
        
        for dir_path in [self.articles_dir, self.keywords_dir, self.prompts_dir, self.images_dir]:
            dir_path.mkdir(exist_ok=True)
        
        print("[OK] AgentArticleSystemの初期化に成功しました。（エージェント完結型）")
    
    def create_article_request(self, main_keyword: str, target_audience: str = "一般", 
                              article_type: str = "情報提供", word_count: int = 2500) -> str:
        """エージェントへの記事作成リクエストを生成"""
        
        # 記事作成リクエストファイル
        request_file = self.prompts_dir / f"article_request_{main_keyword}_{int(time.time())}.json"
        
        request_data = {
            "task": "記事作成",
            "timestamp": datetime.now().isoformat(),
            "main_keyword": main_keyword,
            "target_audience": target_audience,
            "article_type": article_type,
            "word_count": word_count,
            "requirements": [
                "SEO最適化された見出し構造",
                "読者に価値のある実用的な内容",
                "自然で読みやすい日本語",
                "適切な段落分けとリスト化",
                "メタディスクリプションの生成"
            ],
            "output_format": "markdown",
            "output_file": f"articles/{main_keyword}_article.md",
            "next_steps": [
                "1. キーワードリサーチと見出し構造の設計",
                "2. 記事本文の作成",
                "3. 画像プロンプトの生成",
                "4. メタデータの最適化"
            ]
        }
        
        with open(request_file, 'w', encoding='utf-8') as f:
            json.dump(request_data, f, ensure_ascii=False, indent=2)
        
        print(f"✅ 記事作成リクエストファイルを作成しました: {request_file}")
        return str(request_file)
    
    def create_keyword_research_request(self, main_keyword: str, 
                                      collection_method: str = "yahoo_google_hybrid") -> str:
        """エージェントへのキーワードリサーチリクエストを生成"""
        
        request_file = self.prompts_dir / f"keyword_research_{main_keyword}_{int(time.time())}.json"
        
        request_data = {
            "task": "キーワードリサーチ",
            "timestamp": datetime.now().isoformat(),
            "main_keyword": main_keyword,
            "collection_method": collection_method,
            "target_count": 100,
            "requirements": [
                "関連性の高いキーワード100個以上",
                "検索ボリュームの高いキーワード",
                "長尾キーワードのバランス",
                "競合分析の結果"
            ],
            "tools_available": [
                "hybrid_keyword_collector.py - Yahoo + Googleハイブリッド収集",
                "yahoo_keyword_collector_simple.py - Yahoo専用収集",
                "手動での検索エンジン調査"
            ],
            "output_file": f"keywords/{main_keyword}_keywords.json",
            "next_steps": [
                "1. キーワード収集の実行",
                "2. キーワードの分類・優先度付け",
                "3. 見出し構造の設計",
                "4. 記事構成の決定"
            ]
        }
        
        with open(request_file, 'w', encoding='utf-8') as f:
            json.dump(request_data, f, ensure_ascii=False, indent=2)
        
        print(f"✅ キーワードリサーチリクエストファイルを作成しました: {request_file}")
        return str(request_file)
    
    def create_headings_request(self, main_keyword: str, collected_keywords: List[str],
                              article_type: str = "情報提供") -> str:
        """エージェントへの見出し生成リクエストを生成"""
        
        request_file = self.prompts_dir / f"headings_{main_keyword}_{int(time.time())}.json"
        
        request_data = {
            "task": "見出し生成",
            "timestamp": datetime.now().isoformat(),
            "main_keyword": main_keyword,
            "collected_keywords": collected_keywords[:50],  # 上位50個
            "article_type": article_type,
            "requirements": [
                "H2見出し: 5-8個（記事の主要セクション）",
                "H3見出し: 各H2に3-5個（詳細セクション）",
                "SEO最適化（メインキーワードの適切な配置）",
                "読者の興味を引く魅力的な見出し",
                "論理的な流れと構造"
            ],
            "constraints": [
                "H3-1からH3-11にはメインキーワードを含まない",
                "H3-12（まとめ）にはメインキーワードを含める",
                "見出しは具体的で分かりやすく"
            ],
            "output_format": "json",
            "output_file": f"keywords/{main_keyword}_headings.json",
            "next_steps": [
                "1. 見出し構造の設計",
                "2. 各見出しの内容概要",
                "3. 記事構成の決定",
                "4. 記事本文作成の準備"
            ]
        }
        
        with open(request_file, 'w', encoding='utf-8') as f:
            json.dump(request_data, f, ensure_ascii=False, indent=2)
        
        print(f"✅ 見出し生成リクエストファイルを作成しました: {request_file}")
        return str(request_file)
    
    def create_image_prompt_request(self, article_content: str, main_keyword: str,
                                  section: str = "全体") -> str:
        """エージェントへの画像プロンプト生成リクエストを生成"""
        
        request_file = self.prompts_dir / f"image_prompt_{main_keyword}_{int(time.time())}.json"
        
        request_data = {
            "task": "画像プロンプト生成",
            "timestamp": datetime.now().isoformat(),
            "main_keyword": main_keyword,
            "section": section,
            "article_content_preview": article_content[:500] + "...",
            "requirements": [
                "高品質で魅力的な画像",
                "記事の内容と関連性が高い",
                "商用利用可能",
                "SEO最適化（alt属性用の説明文も含む）"
            ],
            "image_specifications": {
                "size": "1200x630px（SNS最適化）",
                "style": "プロフェッショナルで魅力的",
                "format": "PNG/JPG",
                "purpose": "記事のヘッダー画像"
            },
            "output_format": "json",
            "output_file": f"images/{main_keyword}_image_prompts.json",
            "next_steps": [
                "1. 画像プロンプトの生成",
                "2. alt属性の最適化",
                "3. 画像生成サービスの選択",
                "4. 画像の記事への挿入"
            ]
        }
        
        with open(request_file, 'w', encoding='utf-8') as f:
            json.dump(request_data, f, ensure_ascii=False, indent=2)
        
        print(f"✅ 画像プロンプト生成リクエストファイルを作成しました: {request_file}")
        return str(request_file)
    
    def create_complete_workflow_request(self, main_keyword: str, 
                                       target_audience: str = "一般") -> str:
        """エージェントへの完全ワークフローリクエストを生成"""
        
        request_file = self.prompts_dir / f"complete_workflow_{main_keyword}_{int(time.time())}.json"
        
        request_data = {
            "task": "完全記事作成ワークフロー",
            "timestamp": datetime.now().isoformat(),
            "main_keyword": main_keyword,
            "target_audience": target_audience,
            "workflow_steps": [
                {
                    "step": 1,
                    "task": "キーワードリサーチ",
                    "description": "関連キーワード100個以上を収集",
                    "tool": "hybrid_keyword_collector.py または手動調査",
                    "output": "keywords/{main_keyword}_keywords.json"
                },
                {
                    "step": 2,
                    "task": "見出し構造設計",
                    "description": "H2/H3見出しの設計と最適化",
                    "tool": "エージェントの分析能力",
                    "output": "keywords/{main_keyword}_headings.json"
                },
                {
                    "step": 3,
                    "task": "記事本文作成",
                    "description": "2500文字程度のSEO最適化記事",
                    "tool": "エージェントの文章作成能力",
                    "output": "articles/{main_keyword}_article.md"
                },
                {
                    "step": 4,
                    "task": "画像プロンプト生成",
                    "description": "記事用画像のプロンプト作成",
                    "tool": "エージェントの画像分析能力",
                    "output": "images/{main_keyword}_image_prompts.json"
                },
                {
                    "step": 5,
                    "task": "メタデータ最適化",
                    "description": "タイトル、メタディスクリプション、タグ",
                    "tool": "エージェントのSEO知識",
                    "output": "articles/{main_keyword}_metadata.json"
                }
            ],
            "requirements": [
                "高品質な記事内容",
                "SEO最適化",
                "読者に価値のある情報",
                "画像作成の準備完了"
            ],
            "estimated_time": "30-60分（エージェント処理時間）",
            "next_steps": [
                "1. 各ステップの順次実行",
                "2. 品質チェックと調整",
                "3. 最終ファイルの生成",
                "4. 画像生成サービスの利用"
            ]
        }
        
        with open(request_file, 'w', encoding='utf-8') as f:
            json.dump(request_data, f, ensure_ascii=False, indent=2)
        
        print(f"✅ 完全ワークフローリクエストファイルを作成しました: {request_file}")
        return str(request_file)
    
    def get_workflow_status(self) -> Dict[str, Any]:
        """現在のワークフロー状況を確認"""
        status = {
            "total_requests": len(list(self.prompts_dir.glob("*.json"))),
            "articles_created": len(list(self.articles_dir.glob("*.md"))),
            "keywords_collected": len(list(self.keywords_dir.glob("*.json"))),
            "image_prompts": len(list(self.images_dir.glob("*.json"))),
            "recent_files": []
        }
        
        # 最近作成されたファイル
        all_files = []
        for dir_path in [self.articles_dir, self.keywords_dir, self.prompts_dir, self.images_dir]:
            all_files.extend(dir_path.glob("*"))
        
        all_files.sort(key=lambda x: x.stat().st_mtime, reverse=True)
        status["recent_files"] = [str(f.name) for f in all_files[:10]]
        
        return status

# テスト用コード
def test_agent_system():
    """エージェント記事作成システムのテスト"""
    print("=== Cursorエージェント完結型記事作成システムテスト ===")
    
    system = AgentArticleSystem()
    
    # テスト用キーワード
    test_keyword = "プログラミング学習"
    
    print(f"\n1. キーワードリサーチリクエスト作成...")
    keyword_file = system.create_keyword_research_request(test_keyword)
    
    print(f"\n2. 見出し生成リクエスト作成...")
    headings_file = system.create_headings_request(test_keyword, ["Python", "JavaScript", "学習方法"])
    
    print(f"\n3. 記事作成リクエスト作成...")
    article_file = system.create_article_request(test_keyword)
    
    print(f"\n4. 画像プロンプトリクエスト作成...")
    image_file = system.create_image_prompt_request("プログラミング学習について...", test_keyword)
    
    print(f"\n5. 完全ワークフローリクエスト作成...")
    workflow_file = system.create_complete_workflow_request(test_keyword)
    
    print(f"\n6. ワークフロー状況確認...")
    status = system.get_workflow_status()
    print(f"   - 総リクエスト数: {status['total_requests']}")
    print(f"   - 作成済み記事: {status['articles_created']}")
    print(f"   - 収集済みキーワード: {status['keywords_collected']}")
    print(f"   - 画像プロンプト: {status['image_prompts']}")
    
    print(f"\n✅ テスト完了！ エージェントが使用できるリクエストファイルが作成されました。")
    print(f"Cursorエージェントにこれらのファイルを開いて記事作成を依頼してください。")

if __name__ == "__main__":
    test_agent_system()
