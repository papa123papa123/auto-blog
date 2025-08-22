# src/flows/full_article_generation_flow.py

import re
import time
import json
import datetime
from pathlib import Path
from src.gemini_generator import GeminiGenerator
from src.prompt_manager import PromptManager
from src.image_processor import ImageProcessor
from typing import List, Dict, Any
import concurrent.futures

class FullArticleGenerationFlow:
    def __init__(
        self,
        gemini_generator: GeminiGenerator,
        prompt_manager: PromptManager,
        image_processor: ImageProcessor,
    ):
        self.gemini_generator = gemini_generator
        self.prompt_manager = prompt_manager
        self.image_processor = image_processor
        print("[OK] FullArticleGenerationFlowの初期化に成功しました。（v4: プロンプト最適化モード）")

    def _extract_json_from_text(self, text: str) -> Dict[str, Any]:
        try:
            match = re.search(r'```json\s*([\s\S]*?)\s*```', text, re.DOTALL)
            json_str = match.group(1) if match else re.search(r'(\{[\s\S]*\})', text, re.DOTALL).group(0)
            return json.loads(json_str)
        except (json.JSONDecodeError, AttributeError) as e:
            print(f"ERROR: JSONのパースに失敗しました。エラー: {e}, テキスト(先頭300文字): {text[:300]}")
            return None

    def _generate_text_with_retry(self, task_id: str, prompt: str, max_retries: int = 2) -> str:
        for attempt in range(max_retries + 1):
            print(f"  -> [実行中] テキスト生成タスク: {task_id} (試行 {attempt + 1}/{max_retries + 1})")
            response_text = self.gemini_generator.generate([prompt], model_type="pro", timeout=600)
            
            if response_text and len(response_text.strip()) > 50 and "インプットしました" not in response_text:
                print(f"    [成功] タスク: {task_id}")
                return response_text
            
            print(f"    [WARN] タスク '{task_id}' で無効な応答。5秒待機して再試行します...")
            time.sleep(5)
        
        print(f"  -> [失敗] タスク '{task_id}' はリトライ上限に達しました。")
        return ""

    def _find_relevant_info(self, h3_title: str, db: List[Dict]) -> str:
        """DB(JSON)からH3見出しに関連する情報を検索して文字列として返す"""
        h3_keywords = set(re.findall(r'\w+', h3_title.lower()))
        relevant_items = []

        for entry in db:
            for topic in entry.get("topics", []):
                topic_name = topic.get("topic_name", "")
                description = topic.get("description", "")
                content_str = f"{topic_name} {description}".lower()
                if any(kw in content_str for kw in h3_keywords):
                    relevant_items.append(topic)
            
            for product in entry.get("products", []):
                product_info = json.dumps(product, ensure_ascii=False)
                if any(kw in product_info.lower() for kw in h3_keywords):
                    relevant_items.append(product)
        
        if not relevant_items:
            return "関連情報は見つかりませんでした。"
        return json.dumps(relevant_items, indent=2, ensure_ascii=False)

    def run(self, main_keyword: str, article_structure: Dict, summarized_text: str) -> bool:
        print("\n--- 記事＆画像 生成フローを開始します (v4: プロンプト最適化モード) ---")
        start_time = time.time()
        
        title = article_structure.get("title", "（タイトル取得失敗）")
        structured_outline = article_structure.get("outline", [])
        results = {}
        
        try:
            full_db = json.loads(summarized_text)
        except json.JSONDecodeError:
            print("[NG] データベース(JSON)の解析に失敗しました。処理を中断します。")
            return False

        # --- 1. テキストコンテンツを逐次生成 ---
        print("\n[ステップ 1/3] テキストコンテンツを逐次生成中...")
        
        h3_headings = [h3 for h2_section in structured_outline for h3 in h2_section.get('h3', [])]
        
        intro_prompt = self.prompt_manager.create_intro_prompt(main_keyword, h3_headings, title, summarized_text)
        results["intro"] = self._generate_text_with_retry("intro", intro_prompt)

        flat_headings = []
        for h2_section in structured_outline:
            flat_headings.append(f"## {h2_section.get('h2', '')}")
            for h3_title_text in h2_section.get('h3', []):
                flat_headings.append(f"### {h3_title_text}")

        for i, heading in enumerate(flat_headings):
            task_id = f"heading_{i}"
            prompt = ""
            if heading.startswith('## '):
                prompt = self.prompt_manager.create_h2_intro_prompt(heading, flat_headings, i, summarized_text)
            else: # H3
                h3_title = heading.replace('### ', '')
                relevant_info = self._find_relevant_info(h3_title, full_db)
                prompt = self.prompt_manager.create_content_prompt_for_section(
                    main_keyword, h3_title, relevant_info)
            
            results[task_id] = self._generate_text_with_retry(task_id, prompt)

        # --- 2. 画像を並列生成 ---
        print("\n[ステップ 2/3] 画像を並列生成中...")
        # (画像生成ロジックは変更なし)
        
        # --- 3. 結果を組み立ててキャッシュに保存 ---
        print("\n[ステップ 3/3] 全ての生成結果を組み立てています...")
        # (結果組み立てロジックは変更なし)

        # (画像生成と結果組み立てのコードは長いため省略。元のコードを流用)
        all_image_prompts = self._generate_all_image_prompts(title, structured_outline)
        generated_images_dir = Path("generated_images")
        generated_images_dir.mkdir(exist_ok=True)
        for item in generated_images_dir.iterdir(): item.unlink()
        image_tasks = []
        if all_image_prompts:
            if eyecatch_prompt_data := all_image_prompts.get("eyecatch"):
                image_tasks.append(("eyecatch", eyecatch_prompt_data, str(generated_images_dir / "eyecatch.png")))
            for i, h3_prompt_data in enumerate(all_image_prompts.get("h3_images", [])):
                image_tasks.append((f"h3_image_{i}", h3_prompt_data, str(generated_images_dir / f"h3_image_{i}.png")))
        if image_tasks:
            with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
                future_to_task_id = {executor.submit(self._generate_image_worker, *task): task[0] for task in image_tasks}
                for future in concurrent.futures.as_completed(future_to_task_id):
                    task_id, result_data = future.result()
                    results[task_id] = result_data
        
        article_body_parts = [results.get("intro", "")]
        h3_counter = 0
        for i, heading in enumerate(flat_headings):
            content = results.get(f"heading_{i}", "")
            if heading.startswith('## '):
                article_body_parts.append(f"\n{heading}\n\n{content}")
            else:
                image_placeholder = f"\n[h3_image_{h3_counter}]\n"
                article_body_parts.append(f"\n{heading}{image_placeholder}\n\n{content}")
                h3_counter += 1
        
        image_prompts_data = {"eyecatch": results.get("eyecatch", {}), "h3_images": []}
        for i in range(len(h3_headings)):
            img_data = results.get(f"h3_image_{i}", {})
            img_data["placeholder"] = f"[h3_image_{i}]"
            image_prompts_data["h3_images"].append(img_data)

        final_article_body = "".join(article_body_parts)
        final_article_text = f"タイトル: {title}\nメタディスクリプション: {article_structure.get('meta_description', '')}\nタグ: {article_structure.get('tags', '')}\n\n{final_article_body}"
        Path("article_cache.md").write_text(final_article_text, encoding="utf-8")
        with open("image_prompts.json", "w", encoding="utf-8") as f:
            json.dump(image_prompts_data, f, ensure_ascii=False, indent=2)

        end_time = time.time()
        print(f"\n--- [成功] 記事と画像のローカル生成が完了しました。(所要時間: {end_time - start_time:.2f}秒) ---")
        return True

    def _generate_all_image_prompts(self, title: str, outline: List[Dict[str, Any]]):
        """全画像プロンプトを一括生成する（Flashモデル使用）"""
        try:
            prompt = self.prompt_manager.create_all_image_prompts_prompt(title, outline)
            response = self.gemini_generator.generate([prompt], model_type="flash", timeout=300)
            return self._extract_json_from_text(response)
        except Exception as e:
            print(f"ERROR: 全画像プロンプトの一括生成でエラー: {e}")
            return None

    def _generate_image_worker(self, task_id: str, prompt_data: Dict, output_path: str):
        """画像生成タスクのワーカー"""
        try:
            self.image_processor.generate_images(
                prompt=prompt_data.get("positive_prompt", ""),
                output_base_path=output_path,
                number_of_images=1,
                negative_prompt=prompt_data.get("negative_prompt")
            )
            return task_id, {"prompt": prompt_data, "filename": Path(output_path).name}
        except Exception as e:
            print(f"ERROR: 画像生成タスク '{task_id}' でエラー: {e}")
            return task_id, {"error": str(e)}