# src/haru_system.py

import os
from typing import Dict, List
from pathlib import Path
import datetime
import json
import re
from dotenv import load_dotenv

from src.gemini_generator import GeminiGenerator
from src.serp_analyzer import SerpAnalyzer
from src.content_extractor import ContentExtractor
from src.prompt_manager import PromptManager
from src.wordpress_connector import WordPressConnector
from src.image_processor import ImageProcessor
from src.site_manager import SiteManager
from src.keyword_suggester import KeywordSuggester
from src.keyword_hunter import KeywordHunter
from src.sub_keyword_selector import SubKeywordSelector
from src.keyword_analyzer import KeywordAnalyzer
from src.spec_extractor import SpecExtractor
from src.flows.full_article_generation_flow import FullArticleGenerationFlow
from src.flows.database_construction_flow import DatabaseConstructionFlow
from src.flows.strategic_keyword_flow import StrategicKeywordFlow
from src.flows.manual_content_flow import ManualContentFlow

class HaruOrchestrator:
    def __init__(self):
        gemini_api_key = os.getenv("GEMINI_API_KEY")
        serp_api_key = os.getenv("SERPAPI_API_KEY")
        gcp_project_id = os.getenv("GOOGLE_CLOUD_PROJECT_ID")

        if not all([gemini_api_key, serp_api_key, gcp_project_id]):
            raise ValueError(".envファイルにGEMINI_API_KEY, SERPAPI_API_KEY, GOOGLE_CLOUD_PROJECT_IDのいずれかが設定されていません。")

        print("司令塔が全ての専門家を準備中...")
        
        self.gemini_generator = GeminiGenerator()
        self.image_processor = ImageProcessor()
        self.serp_analyzer = SerpAnalyzer(api_key=serp_api_key)
        self.keyword_suggester = KeywordSuggester()
        self.content_extractor = ContentExtractor()
        self.prompt_manager = PromptManager()
        self.wordpress_connector = WordPressConnector()
        self.site_manager = SiteManager()
        self.keyword_analyzer = KeywordAnalyzer(serp_analyzer=self.serp_analyzer)
        self.spec_extractor = SpecExtractor(gemini_generator=self.gemini_generator)
        
        self.keyword_hunter = KeywordHunter(
            serp_analyzer=self.serp_analyzer,
            keyword_suggester=self.keyword_suggester
        )
        self.sub_keyword_selector = SubKeywordSelector(
            gemini_generator=self.gemini_generator,
            prompt_manager=self.prompt_manager
        )
        
        self.database_construction_flow = DatabaseConstructionFlow(
            serp_analyzer=self.serp_analyzer,
            gemini_generator=self.gemini_generator,
            prompt_manager=self.prompt_manager,
            content_extractor=self.content_extractor
        )
        self.full_article_generation_flow = FullArticleGenerationFlow(
            gemini_generator=self.gemini_generator,
            prompt_manager=self.prompt_manager,
            image_processor=self.image_processor
        )
        self.strategic_keyword_flow = StrategicKeywordFlow(
            keyword_hunter=self.keyword_hunter,
            sub_keyword_selector=self.sub_keyword_selector
        )
        self.manual_content_flow = ManualContentFlow(
            spec_extractor=self.spec_extractor,
            sub_keyword_selector=self.sub_keyword_selector,
            gemini_generator=self.gemini_generator
        )
        print("[OK] 全ての専門家とフローの準備が完了しました。")

    def run_manual_content_flow(self):
        return self.manual_content_flow.run()

    def run_strategic_keyword_flow(self, auto_yes: bool = False):
        """
        【改修後】戦略的キーワードフローを実行し、メインKWと構成案JSONを返す。
        """
        # strategic_keyword_flow.run()が、キーワード収集から構成案作成まで全て実行し、
        # main_keywordとarticle_structureを返すようになった。
        main_keyword, article_structure = self.strategic_keyword_flow.run(auto_yes)
        return main_keyword, article_structure

    def run_keyword_research_flow(self):
        print("\n--- [超高速] キーワード発見・分析フロー ---")
        self.keyword_analyzer.run_analysis()

    def run_full_article_creation_flow(self, site_info: Dict, credentials: Dict):
        """
        【最終版】キーワード選定から記事生成、投稿までを一気通貫で実行するフロー。
        """
        # 1. 【改修】戦略的キーワード選定＆構成案作成
        main_keyword, article_structure = self.run_strategic_keyword_flow()
        if not (main_keyword and article_structure):
            print("\n構成案の作成が正常に完了しなかったため、フローを中止します。")
            return

        # 2. 【新規追加】collect_google_suggestions.py + extract_seo_content.pyを使用してサジェスト多数取得
        print("\n--- ステップ2: Googleサジェスト収集 → SEO用コンテンツ抽出 ---")
        try:
            # 1. サジェスト収集
            print("📊 Google SERP API サジェスト収集中...")
            import subprocess
            import sys
            
            result1 = subprocess.run([sys.executable, "collect_google_suggestions.py"], 
                                   capture_output=True, text=True, encoding='utf-8')
            
            if result1.returncode == 0:
                print("✅ サジェスト収集が完了しました")
                if result1.stdout:
                    print(result1.stdout)
            else:
                print(f"❌ サジェスト収集が失敗しました: {result1.stderr}")
                print("既存のフローを継続します。")
                collected_suggestions = []
            
            # 2. SEO用コンテンツ抽出
            print("🔍 SEO用コンテンツ抽出中...")
            result2 = subprocess.run([sys.executable, "extract_seo_content.py"], 
                                   capture_output=True, text=True, encoding='utf-8')
            
            if result2.returncode == 0:
                print("✅ SEO用コンテンツ抽出が完了しました")
                if result2.stdout:
                    print(result2.stdout)
            else:
                print(f"❌ SEO用コンテンツ抽出が失敗しました: {result2.stderr}")
                print("既存のフローを継続します。")
                collected_suggestions = []
            
            # 3. 抽出されたコンテンツを読み込み
            import glob
            seo_files = glob.glob("seo_results/seo_content_*.txt")
            if seo_files:
                # 最新のファイルを取得
                latest_file = max(seo_files, key=os.path.getctime)
                with open(latest_file, 'r', encoding='utf-8') as f:
                    content_lines = f.readlines()
                
                # 番号を除去してコンテンツのみを抽出
                collected_suggestions = []
                for line in content_lines:
                    if line.strip() and '. ' in line:
                        content = line.split('. ', 1)[1].strip()
                        if content:
                            collected_suggestions.append(content)
                
                print(f"✅ SEO用コンテンツ読み込み完了: {len(collected_suggestions)}件")
                print(f"📁 読み込みファイル: {latest_file}")
            else:
                print("⚠️ SEO用コンテンツファイルが見つかりません。既存のフローを継続します。")
                collected_suggestions = []
                
        except Exception as e:
            print(f"⚠️ サジェスト収集でエラーが発生しました: {e}")
            print("既存のフローを継続します。")
            collected_suggestions = []

        # 3. 高品質JSONデータベース構築（キャッシュ対応）
        # 構成案からH3リストを抽出して渡す
        sub_keywords = [h3 for h2 in article_structure.get("outline", []) for h3 in h2.get("h3", [])]
        final_json_database = self.database_construction_flow.build_database_from_sub_keywords(main_keyword, sub_keywords)
        if not (final_json_database and final_json_database.strip()):
            print("[NG] データベースの構築に失敗、または収集されたデータが空です。フローを中止します。")
            return

        # 4. 記事と画像のローカル生成（完全並列）
        success = self.full_article_generation_flow.run(main_keyword, article_structure, final_json_database)
        if not success:
            print("[NG] 記事と画像のローカル生成に失敗しました。")
            return
            
        # 5. 自動投稿
        self._post_from_cache(site_info, credentials)

    def _post_from_cache(self, site_info: Dict, credentials: Dict):
        """ローカルキャッシュから記事と画像を投稿する内部メソッド。"""
        print("\n--- WordPressへの自動投稿ステップ ---")
        if not Path("article_cache.md").exists() or not Path("image_prompts.json").exists():
            print("[エラー] 投稿に必要なキャッシュファイルが見つかりません。")
            return
        
        result = self.wordpress_connector.post_from_cache(site_info, credentials)
        if result.get("success"):
            print(f"\n[成功] 投稿が完了しました！ URL: {result.get('link')}")
            self.site_manager.update_article_count(site_info['id'])
        else:
            print(f"\n[失敗] 投稿中にエラーが発生しました: {result.get('error')}")