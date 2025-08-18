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
        print("[OK] FullArticleGenerationFlowの初期化に成功しました。（品質優先・逐次生成モード v3）")

    def _extract_json_from_text(self, text: str) -> Dict[str, Any]:
        """マークダウンのコードブロックや、テキストに埋め込まれたJSONを抽出する。"""
        try:
            match = re.search(r'```json\s*([\s\S]*?)\s*```', text, re.DOTALL)
            if match:
                json_str = match.group(1)
            else:
                match = re.search(r'(\{[\s\S]*\})', text, re.DOTALL)
                if match:
                    json_str = match.group(0)
                else:
                    raise json.JSONDecodeError("応答からJSONオブジェクトが見つかりませんでした。", text, 0)
            return json.loads(json_str)
        except json.JSONDecodeError as e:
            print(f"ERROR: JSONのパースに失敗しました。エラー: {e}, テキスト(先頭300文字): {text[:300]}")
            return None

    def _generate_text_with_retry(self, task_id: str, prompt: str, max_retries: int = 2) -> str:
        """
        テキスト生成を試行し、失敗した場合はリトライする。
        空の応答や無意味な応答を失敗とみなす。
        """
        for attempt in range(max_retries + 1):
            print(f"  -> [実行中] テキスト生成タスク: {task_id} (試行 {attempt + 1}/{max_retries + 1})")
            response_text = self.gemini_generator.generate([prompt], model_type="pro", timeout=600)
            
            # 検証: 応答が有効か（空でない、短すぎない、無意味な定型句でない）
            if response_text and len(response_text.strip()) > 50 and "インプットしました" not in response_text and "承知しました" not in response_text:
                print(f"    [成功] タスク: {task_id}")
                return response_text
            
            print(f"    [WARN] タスク '{task_id}' で無効な応答を受信しました。応答: '{response_text[:100]}...'")
            if attempt < max_retries:
                print("    -> 5秒待機して再試行します...")
                time.sleep(5)
        
        print(f"  -> [失敗] タスク '{task_id}' はリトライ上限に達しました。")
        return "" # 最終的に失敗した場合は空文字を返す

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

    def run(self, main_keyword: str, article_structure: Dict, summarized_text: str) -> bool:
        print("\n--- 記事＆画像 生成・ローカル保存フローを開始します (品質優先・逐次生成モード v3) ---")
        start_time = time.time()
        
        current_year = datetime.datetime.now().year
        title = article_structure.get("title", "（タイトル取得失敗）")
        structured_outline = article_structure.get("outline", [])
        results = {}

        # --- 1. 全てのテキストコンテンツを逐次生成（品質優先） ---
        print("\n[ステップ 1/3] 全てのテキストコンテンツを逐次生成中...")
        
        h3_headings = [h3 for h2_section in structured_outline for h3 in h2_section.get('h3', [])]
        
        # 導入文
        intro_prompt = self.prompt_manager.create_intro_prompt(main_keyword, h3_headings, title, summarized_text)
        results["intro"] = self._generate_text_with_retry("intro", intro_prompt)

        # H2, H3の本文
        flat_headings = []
        for h2_section in structured_outline:
            h2_title = f"## {h2_section.get('h2', '')}"
            flat_headings.append(h2_title)
            for h3_title_text in h2_section.get('h3', []):
                flat_headings.append(f"### {h3_title_text}")

        for i, heading in enumerate(flat_headings):
            task_id = f"heading_{i}"
            if heading.startswith('## '):
                prompt = self.prompt_manager.create_h2_intro_prompt(heading, flat_headings, i, summarized_text)
            else: # H3
                prompt = self.prompt_manager.create_content_prompt_for_section(
                    main_keyword, structured_outline, heading.replace('### ', ''), current_year, summarized_text)
            results[task_id] = self._generate_text_with_retry(task_id, prompt)

        # --- 2. 全ての画像を並列生成 ---
        print("\n[ステップ 2/3] 全ての画像を並列生成中...")
        print("  -> 全ての画像プロンプトを一括生成中 (Flashモデル使用)...")
        all_image_prompts = self._generate_all_image_prompts(title, structured_outline)
        
        generated_images_dir = Path("generated_images")
        generated_images_dir.mkdir(exist_ok=True)
        for item in generated_images_dir.iterdir(): item.unlink()

        image_tasks = []
        if all_image_prompts:
            if eyecatch_prompt_data := all_image_prompts.get("eyecatch"):
                output_path = str(generated_images_dir / "eyecatch.png")
                image_tasks.append(("eyecatch", eyecatch_prompt_data, output_path))

            for i, h3_prompt_data in enumerate(all_image_prompts.get("h3_images", [])):
                task_id = f"h3_image_{i}"
                output_path = str(generated_images_dir / f"{task_id}.png")
                image_tasks.append((task_id, h3_prompt_data, output_path))
        else:
            print("[WARN] 画像プロンプトの一括生成に失敗したため、画像生成をスキップします。" )

        if image_tasks:
            with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
                future_to_task_id = {executor.submit(self._generate_image_worker, *task): task[0] for task in image_tasks}
                for future in concurrent.futures.as_completed(future_to_task_id):
                    task_id = future_to_task_id[future]
                    try:
                        _, result_data = future.result()
                        results[task_id] = result_data
                        print(f"  -> [完了] 画像タスク: {task_id}")
                    except Exception as exc:
                        print(f"  -> [エラー] 画像タスク {task_id} で例外発生: {exc}")

        # --- 3. 結果を組み立ててキャッシュファイルに保存 ---
        print("\n[ステップ 3/3] 全ての生成結果を組み立てています...")
        
        article_body_parts = [results.get("intro", "")]
        h3_counter = 0
        for i, heading in enumerate(flat_headings):
            heading_id = f"heading_{i}"
            content = results.get(heading_id, "")
            if not content:
                print(f"[WARN] 見出し「{heading}」の本文が空のため、スキップします。")

            if heading.startswith('## '):
                article_body_parts.append(f"\n{heading}\n\n{content}")
            else: # H3
                image_placeholder = f"\n[h3_image_{h3_counter}]\n"
                article_body_parts.append(f"\n{heading}{image_placeholder}\n\n{content}")
                h3_counter += 1

        image_prompts_data = {"eyecatch": results.get("eyecatch", {}), "h3_images": []}
        for i in range(len(h3_headings)):
            image_id = f"h3_image_{i}"
            if image_id in results and isinstance(results[image_id], dict):
                img_data = results[image_id]
                img_data["placeholder"] = f"[{image_id}]"
                image_prompts_data["h3_images"].append(img_data)

        final_article_body = "".join(article_body_parts)
        final_article_text = f"タイトル: {title}\nメタディスクリプション: {article_structure.get('meta_description', '')}\nタグ: {article_structure.get('tags', '')}\n\n{final_article_body}"
        
        Path("article_cache.md").write_text(final_article_text, encoding="utf-8")
        print("  -> article_cache.md を保存しました。")
        
        with open("image_prompts.json", "w", encoding="utf-8") as f:
            json.dump(image_prompts_data, f, ensure_ascii=False, indent=2)
        print("  -> image_prompts.json を保存しました。")

        end_time = time.time()
        print(f"\n--- [成功] 記事と画像のローカル生成が完了しました。(所要時間: {end_time - start_time:.2f}秒) ---")
        return True
