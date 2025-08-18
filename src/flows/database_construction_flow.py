# src/flows/database_construction_flow.py

import json
import time
import concurrent.futures
from typing import List, Dict, Any, Set
import datetime
from pathlib import Path
import re

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
        self.cache_dir.mkdir(exist_ok=True)
        print("[OK] DatabaseConstructionFlowの初期化に成功しました。（ルールベース権威性担保型・キャッシュ対応）")

    def _get_cache_filepath(self, main_keyword: str) -> Path:
        """キーワードに基づいたキャッシュファイルのパスを生成する。"""
        safe_filename = "".join(c for c in main_keyword if c.isalnum() or c in (' ', '_', '-')).rstrip()
        return self.cache_dir / f"{safe_filename}.json"

    def _load_from_cache(self, cache_path: Path) -> str:
        """キャッシュファイルが存在し、有効期限内であれば読み込む。"""
        if cache_path.exists():
            file_mod_time = datetime.datetime.fromtimestamp(cache_path.stat().st_mtime)
            if datetime.datetime.now() - file_mod_time < datetime.timedelta(hours=24):
                print(f"[CACHE] 24時間以内に生成された有効なキャッシュが見つかりました: {cache_path}")
                return cache_path.read_text(encoding="utf-8")
        return None

    def _save_to_cache(self, cache_path: Path, data: str):
        """生成したデータベースをキャッシュファイルに保存する。"""
        try:
            cache_path.write_text(data, encoding="utf-8")
            print(f"[CACHE] 生成したデータベースをキャッシュに保存しました: {cache_path}")
        except Exception as e:
            print(f"[ERROR] キャッシュの保存中にエラーが発生しました: {e}")

    def _get_priority_urls(self, main_keyword: str) -> Set[str]:
        """メインキーワードで検索し、最優先ドメインリストに合致するURLを収集する。"""
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
        """サブキーワードで検索し、上位2サイトのURLを並列で収集する。"""
        sub_keyword_urls = set()
        print(f"  -> {len(sub_keywords)}個のサブキーワードから関連URLを並列収集中...")
        with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
            future_to_keyword = {executor.submit(self.serp_analyzer.get_strong_competitor_urls, keyword, 2): keyword for keyword in sub_keywords}
            for future in concurrent.futures.as_completed(future_to_keyword):
                keyword = future_to_keyword[future]
                try:
                    urls = future.result()
                    if urls:
                        sub_keyword_urls.update(urls)
                except Exception as exc:
                    print(f"    [ERROR] サブキーワード「{keyword}」の検索中にエラーが発生しました: {exc}")
        print(f"    [OK] サブキーワードから{len(sub_keyword_urls)}件のユニークURLを収集しました。")
        return sub_keyword_urls

    def _process_url_worker(self, url: str) -> Dict[str, Any]:
        """
        単一のURLを処理するワーカー関数（テキスト抽出 -> AI要約）。
        抽出失敗時にRequestsでフォールバックし、JSONエラー時にはデバッグログを保存する。
        """
        print(f"  -> URLを処理中: {url}")
        raw_response_text = ""
        try:
            # 1. Playwrightで試行
            title, clean_text = self.content_extractor.extract_text_with_playwright(url)
            
            # 2. Playwrightが失敗したらRequestsでフォールバック
            if title == "エラー":
                print(f"    -> Playwrightでの抽出失敗。Requestsで再試行します...")
                title, clean_text = self.content_extractor.extract_text_with_requests(url)
                if title == "エラー":
                    raise Exception(clean_text) # Requestsも失敗したら例外を発生させる

            summarization_prompt = self.prompt_manager.create_summarization_prompt("抽出テキスト", clean_text)
            raw_response_text = self.gemini_generator.generate([summarization_prompt], model_type="pro", timeout=300)
            
            json_str = None
            match = re.search(r'```json\s*([\s\S]*?)\s*```', raw_response_text, re.DOTALL)
            if match:
                json_str = match.group(1)
            else:
                match = re.search(r'(\{[\s\S]*\}|[[\][\s\S]*\])', raw_response_text, re.DOTALL)
                if match:
                    json_str = match.group(0)

            if not json_str:
                raise json.JSONDecodeError("応答からJSONオブジェクトが見つかりませんでした。", raw_response_text, 0)

            data = json.loads(json_str)
            
            if isinstance(data, list):
                for item in data:
                    item['source_url'] = url
            else:
                data['source_url'] = url

            print(f"    [OK] URLの要約が完了しました: {url}")
            return data
        
        except json.JSONDecodeError:
            error_msg = f"JSONの解析に失敗しました (URL: {url})"
            print(f"    [ERROR] {error_msg}")
            
            # デバッグログを保存
            debug_dir = Path("debug_json_failures")
            debug_dir.mkdir(exist_ok=True)
            timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            failure_path = debug_dir / f"{timestamp}_{url.replace('/', '_')[:50]}.txt"
            failure_path.write_text(f"URL: {url}\n\n--- Gemini Raw Response ---\n{raw_response_text}", encoding="utf-8")
            print(f"    -> [DEBUG] 解析失敗時の応答を {failure_path} に保存しました。")
            
            return {"error": error_msg, "response": "Response saved to debug file."}
        
        except Exception as e:
            error_msg = f"URL処理中にエラーが発生しました (URL: {url}): {e}" 
            print(f"    [ERROR] {error_msg}")
            return {"error": error_msg}

    def build_database_from_sub_keywords(self, main_keyword: str, sub_keywords: list[str]) -> str:
        """
        【最終バージョン】ルールベースで権威サイトと関連サイトを収集し、
        ヘッドレスブラウザとAIで高品質なJSONデータベースを並列構築する。
        キャッシュ機能と堅牢な並列処理監視機能を搭載。
        """
        cache_path = self._get_cache_filepath(main_keyword)
        cached_data = self._load_from_cache(cache_path)
        if cached_data:
            return cached_data

        print("\n[STEP 1/3] 権威サイトと関連サイトのURLを収集中...")
        
        priority_urls = self._get_priority_urls(main_keyword)
        sub_keyword_urls = self._get_sub_keyword_urls(sub_keywords)
        
        final_urls = list(priority_urls.union(sub_keyword_urls))

        if not final_urls:
            print("[NG] 分析対象のURLが1件も見つかりませんでした。処理を中断します。")
            return ""

        print(f"\n[STEP 2/3] 合計 {len(final_urls)}件のユニークURLからデータベースを並列構築中...")
        
        all_data = []
        processed_count = 0
        total_urls = len(final_urls)

        with concurrent.futures.ThreadPoolExecutor(max_workers=20) as executor:
            future_to_url = {executor.submit(self._process_url_worker, url): url for url in final_urls}
            
            for future in concurrent.futures.as_completed(future_to_url):
                processed_count += 1
                url = future_to_url[future]
                print(f"  [進捗: {processed_count}/{total_urls}] URLの結果を待機中: {url}")
                try:
                    # future.result()にタイムアウトを設定 (Geminiのタイムアウト300秒 + 予備10秒)
                    result = future.result(timeout=310)
                    
                    if result and "error" not in result:
                        if isinstance(result, list):
                            all_data.extend(result)
                        else:
                            all_data.append(result)
                        print(f"    [OK] URLの処理結果を正常に格納しました: {url}")
                    else:
                        print(f"    [WARN] URLの処理結果にエラーが含まれていたため、スキップします: {url}")

                except concurrent.futures.TimeoutError:
                    print(f"  [CRITICAL ERROR] URLの処理がタイムアウトしました（310秒）: {url}")
                except Exception as exc:
                    print(f"  [CRITICAL ERROR] URL「{url}」の処理中に予期せぬ例外が発生しました: {exc}")

        if not all_data:
            print("[NG] データベースの構築に失敗しました。どのURLからもデータを抽出できませんでした。")
            return ""

        print("\n[STEP 3/3] 全てのデータを統合し、最終的なJSONデータベースを生成中...")
        final_database_json = json.dumps(all_data, indent=2, ensure_ascii=False)
        
        self._save_to_cache(cache_path, final_database_json)
        
        print("[OK] 高品質なJSONデータベースの構築が完了しました。")
        return final_database_json
