# src/flows/database_construction_flow.py

import json
import time
import concurrent.futures
from typing import List, Dict, Any, Set, Tuple
import datetime
from pathlib import Path
import re
import hashlib

from src.serp_analyzer import SerpAnalyzer
from src.gemini_generator import GeminiGenerator
from src.prompt_manager import PromptManager
from src.content_extractor import ContentExtractor

class DatabaseConstructionFlow:
    def __init__(self, serp_analyzer: SerpAnalyzer, gemini_generator: GeminiGenerator, prompt_manager: PromptManager, content_extractor: ContentExtractor):
        self.serp_analyzer = serp_analyzer
        self.gemini_generator = gemini_generator
        self.prompt_manager = prompt_manager
        self.content_extractor = content_extractor
        self.priority_domains = [
            "my-best.com", "kakaku.com", "amazon.co.jp", "rakuten.co.jp"
        ]
        self.cache_dir = Path("summarized_texts")
        self.html_cache_dir = Path("html_cache")
        self.cache_dir.mkdir(exist_ok=True)
        self.html_cache_dir.mkdir(exist_ok=True)
        print("[OK] DatabaseConstructionFlowの初期化に成功しました。（ローカルHTML処理モード）")

    def _get_cache_filepath(self, main_keyword: str) -> Path:
        safe_filename = "".join(c for c in main_keyword if c.isalnum() or c in (' ', '_', '-')).rstrip()
        return self.cache_dir / f"{safe_filename}.json"

    def _load_from_cache(self, cache_path: Path) -> str:
        if cache_path.exists():
            file_mod_time = datetime.datetime.fromtimestamp(cache_path.stat().st_mtime)
            if datetime.datetime.now() - file_mod_time < datetime.timedelta(hours=24):
                print(f"[CACHE] 24時間以内に生成された有効なキャッシュが見つかりました: {cache_path}")
                return cache_path.read_text(encoding="utf-8")
        return None

    def _save_to_cache(self, cache_path: Path, data: str):
        try:
            cache_path.write_text(data, encoding="utf-8")
            print(f"[CACHE] 生成したデータベースをキャッシュに保存しました: {cache_path}")
        except Exception as e:
            print(f"[ERROR] キャッシュの保存中にエラーが発生しました: {e}")

    def _get_priority_urls(self, main_keyword: str) -> Set[str]:
        print(f"  -> メインキーワード「{main_keyword}」で権威サイトを検索中...")
        priority_urls = set()
        try:
            competitors = self.serp_analyzer.get_strong_competitors_info(main_keyword, num_results=15)
            for competitor in competitors:
                if any(domain in competitor["url"] for domain in self.priority_domains):
                    priority_urls.add(competitor["url"])
            print(f"    [OK] {len(priority_urls)}件の権威サイトURLを確保しました。")
        except Exception as e:
            print(f"    [ERROR] 権威サイトの検索中にエラーが発生しました: {e}")
        return priority_urls

    def _get_sub_keyword_urls(self, sub_keywords: List[str]) -> Set[str]:
        sub_keyword_urls = set()
        print(f"  -> {len(sub_keywords)}個のサブキーワードから関連URLを並列収集中...")
        with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
            future_to_keyword = {executor.submit(self.serp_analyzer.get_strong_competitor_urls, keyword, 2): keyword for keyword in sub_keywords}
            for future in concurrent.futures.as_completed(future_to_keyword):
                try:
                    urls = future.result()
                    if urls:
                        sub_keyword_urls.update(urls)
                except Exception as exc:
                    print(f"    [ERROR] サブキーワード検索中にエラー: {exc}")
        print(f"    [OK] サブキーワードから{len(sub_keyword_urls)}件のユニークURLを収集しました。")
        return sub_keyword_urls

    def _url_to_filename(self, url: str) -> Path:
        """URLを安全なファイル名に変換する"""
        url_hash = hashlib.md5(url.encode()).hexdigest()
        safe_domain = "".join(c for c in url.split('/')[2] if c.isalnum() or c in ('-', '_')).rstrip()
        return self.html_cache_dir / f"{safe_domain}_{url_hash}.html"

    def _download_html_worker(self, url: str) -> Tuple[str, Path, bool]:
        """URLからHTMLをダウンロードしてローカルに保存するワーカー"""
        filepath = self._url_to_filename(url)
        if filepath.exists():
            print(f"  -> [SKIP] HTMLは既にキャッシュされています: {url}")
            return url, filepath, True
        
        print(f"  -> [DOWNLOAD] HTMLをダウンロード中: {url}")
        try:
            html_content = self.content_extractor.download_html_with_playwright(url)
            if html_content:
                filepath.write_text(html_content, encoding="utf-8")
                return url, filepath, True
            else:
                return url, filepath, False
        except Exception as e:
            print(f"    [ERROR] HTMLダウンロード中にエラー (URL: {url}): {e}")
            return url, filepath, False

    def _process_local_html_worker(self, url: str, html_path: Path) -> Dict[str, Any]:
        """ローカルHTMLファイルを処理して要約を生成するワーカー"""
        print(f"  -> ローカルHTMLを処理中: {html_path.name}")
        raw_response_text = ""
        try:
            title, clean_text = self.content_extractor.extract_text_from_local_html(html_path)
            if title == "エラー":
                raise Exception(clean_text)

            summarization_prompt = self.prompt_manager.create_summarization_prompt("抽出テキスト", clean_text)
            raw_response_text = self.gemini_generator.generate([summarization_prompt], model_type="pro", timeout=300)
            
            match = re.search(r'```json\s*([\s\S]*?)\s*```', raw_response_text, re.DOTALL)
            json_str = match.group(1) if match else re.search(r'(\{[\s\S]*\})', raw_response_text, re.DOTALL).group(0)
            
            if not json_str:
                raise json.JSONDecodeError("応答からJSONオブジェクトが見つかりませんでした。", raw_response_text, 0)

            data = json.loads(json_str)
            
            source_info = {'source_url': url, 'source_file': str(html_path)}
            if isinstance(data, list):
                for item in data: item.update(source_info)
            else:
                data.update(source_info)

            print(f"    [OK] ローカルHTMLの要約が完了しました: {html_path.name}")
            return data
        
        except Exception as e:
            error_msg = f"ローカルHTML処理中にエラー ({html_path.name}): {e}" 
            print(f"    [ERROR] {error_msg}")
            return {"error": error_msg}

    def build_database_from_sub_keywords(self, main_keyword: str, sub_keywords: list[str]) -> str:
        cache_path = self._get_cache_filepath(main_keyword)
        cached_data = self._load_from_cache(cache_path)
        if cached_data: return cached_data

        print("\n[STEP 1/4] 権威サイトと関連サイトのURLを収集中...")
        priority_urls = self._get_priority_urls(main_keyword)
        sub_keyword_urls = self._get_sub_keyword_urls(sub_keywords)
        final_urls = list(priority_urls.union(sub_keyword_urls))

        if not final_urls:
            print("[NG] 分析対象のURLが1件も見つかりませんでした。")
            return ""

        print(f"\n[STEP 2/4] 合計 {len(final_urls)}件のURLからHTMLを安全にダウンロード中 (並列数: 5)...")
        downloaded_files = {}
        with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
            future_to_url = {executor.submit(self._download_html_worker, url): url for url in final_urls}
            for future in concurrent.futures.as_completed(future_to_url):
                url, filepath, success = future.result()
                if success:
                    downloaded_files[url] = filepath
        
        if not downloaded_files:
            print("[NG] どのURLからもHTMLをダウンロードできませんでした。")
            return ""

        print(f"\n[STEP 3/4] {len(downloaded_files)}件のローカルHTMLからデータベースを並列構築中 (並列数: 20)...")
        all_data = []
        with concurrent.futures.ThreadPoolExecutor(max_workers=20) as executor:
            future_to_path = {executor.submit(self._process_local_html_worker, url, path): path for url, path in downloaded_files.items()}
            for future in concurrent.futures.as_completed(future_to_path):
                try:
                    result = future.result(timeout=310)
                    if result and "error" not in result:
                        if isinstance(result, list): all_data.extend(result)
                        else: all_data.append(result)
                except Exception as exc:
                    print(f"  [CRITICAL ERROR] ローカルHTML処理中に予期せぬ例外: {exc}")

        if not all_data:
            print("[NG] データベースの構築に失敗しました。どのHTMLからもデータを抽出できませんでした。")
            return ""

        print("\n[STEP 4/4] 全てのデータを統合し、最終的なJSONデータベースを生成中...")
        final_database_json = json.dumps(all_data, indent=2, ensure_ascii=False)
        self._save_to_cache(cache_path, final_database_json)
        
        print("[OK] 高品質なJSONデータベースの構築が完了しました。")
        return final_database_json
