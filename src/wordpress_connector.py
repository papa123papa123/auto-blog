# src/wordpress_connector.py

import requests
from typing import Dict, List
import re
import markdown
import mimetypes
from pathlib import Path
import html
import uuid
import time
import json
import concurrent.futures

class WordPressConnector:
    def __init__(self):
        print("[OK] WordPressConnectorの初期化に成功しました。")

    def _get_auth(self, credentials: Dict):
        return (credentials.get("username"), credentials.get("password"))

    def _html_to_native_blocks(self, html_content: str) -> str:
        """
        HTML文字列を解析し、個別のネイティブなWordPressブロックの文字列に変換する。
        """
        if not html_content.strip():
            return ""

        # HTMLのトップレベル要素を分割するための正規表現
        # <p>, <ul>, <ol>, <table> などを個別にキャプチャする
        pattern = r'(<p>.*?</p>|<ul>.*?</ul>|<ol>.*?</ol>|<table>.*?</table>)'
        parts = re.split(pattern, html_content, flags=re.DOTALL)
        
        blocks = []
        for part in filter(None, [p.strip() for p in parts]):
            if part.startswith('<p>'):
                content = part[3:-4] # <p>と</p>を除去
                blocks.append(f'<!-- wp:paragraph --><p>{content}</p><!-- /wp:paragraph -->')
            elif part.startswith('<ul>'):
                items = "".join([f'<!-- wp:list-item -->{li}<!-- /wp:list-item -->' for li in re.findall(r'<li>.*?</li>', part, re.DOTALL)])
                blocks.append(f'<!-- wp:list --><ul>{items}</ul><!-- /wp:list -->')
            elif part.startswith('<ol>'):
                items = "".join([f'<!-- wp:list-item -->{li}<!-- /wp:list-item -->' for li in re.findall(r'<li>.*?</li>', part, re.DOTALL)])
                blocks.append(f'<!-- wp:list {{"ordered":true}} --><ol>{items}</ol><!-- /wp:list -->')
            elif part.startswith('<table'):
                blocks.append(f'<!-- wp:table --><figure class="wp-block-table">{part}</figure><!-- /wp:table -->')
            else:
                # 上記以外（主に分割で残った改行など）は無視するか、必要なら段落として扱う
                # ここでは無視して、意図しない空の段落が作られるのを防ぐ
                pass
        
        return "\n\n".join(blocks)

    def get_or_create_tag_ids(self, site_info: Dict, credentials: Dict, tag_names: List[str]) -> List[int]:
        tag_ids = []
        api_url = f"{site_info['domain'].rstrip('/')}/wp-json/wp/v2/tags"
        print("\n--- タグを処理中 ---")
        for name in tag_names:
            try:
                create_res = requests.post(api_url, json={'name': name}, auth=self._get_auth(credentials), timeout=15)
                if create_res.status_code == 201:
                    tag_ids.append(create_res.json()['id'])
                    print(f"  -> タグ '{name}' (ID: {create_res.json()['id']}) を新規作成しました。")
                elif create_res.status_code == 400 and create_res.json().get('code') == 'term_exists':
                    term_id = create_res.json().get('data', {}).get('term_id')
                    if term_id:
                        tag_ids.append(term_id)
                        print(f"  -> 既存タグ '{name}' (ID: {term_id}) を使用します。")
            except requests.exceptions.RequestException as e:
                print(f"[WARN] タグ '{name}' の処理に失敗: {e}")
        print("--- タグの処理完了 ---\n")
        return tag_ids

    def upload_image(self, site_info: Dict, credentials: Dict, image_path: Path, title: str) -> Dict:
        api_url = f"{site_info['domain'].rstrip('/')}/wp-json/wp/v2/media"
        safe_filename = f"upload_{uuid.uuid4()}{image_path.suffix}"
        mime_type, _ = mimetypes.guess_type(image_path.name)
        if not mime_type: mime_type = 'application/octet-stream'

        try:
            with open(image_path, "rb") as f: img_data = f.read()
            headers = {'Content-Disposition': f'attachment; filename="{safe_filename}"', 'Content-Type': mime_type}
            res = requests.post(api_url, data=img_data, headers=headers, auth=self._get_auth(credentials), timeout=45)
            res.raise_for_status()
            media_info = res.json()
            update_payload = {'title': title, 'alt_text': title, 'caption': title}
            requests.post(f"{api_url}/{media_info['id']}", json=update_payload, auth=self._get_auth(credentials), timeout=30).raise_for_status()
            print(f"  -> [OK] 画像 '{title}' をアップロード (ID: {media_info['id']})")
            return {"success": True, "media_id": media_info["id"], "image_url": media_info["source_url"]}
        except requests.exceptions.RequestException as e:
            print(f"  -> [NG] 画像 '{title}' のアップロード失敗: {e}")
            return {"success": False, "error": f"画像 '{title}' のアップロード失敗: {e}"}

    def create_post(self, site_info: Dict, credentials: Dict, post_data: Dict) -> Dict:
        api_url = f"{site_info['domain'].rstrip('/')}/wp-json/wp/v2/posts"
        try:
            response = requests.post(api_url, json=post_data, auth=self._get_auth(credentials), timeout=60)
            response.raise_for_status()
            return {"success": True, "id": response.json().get('id'), "link": response.json().get('link')}
        except requests.exceptions.RequestException as e:
            return {"success": False, "error": f"投稿エラー: {e.response.text if e.response else e}"}

    def post_from_cache(self, site_info: Dict, credentials: Dict) -> Dict:
        print("\n--- キャッシュからの記事投稿処理を開始します ---")
        try:
            article_text = Path("article_cache.md").read_text(encoding="utf-8")
            with open("image_prompts.json", "r", encoding="utf-8") as f:
                image_data = json.load(f)
            
            generated_images_dir = Path("generated_images")

            title = re.search(r"タイトル:\s*(.*)", article_text).group(1).strip()
            meta_desc = re.search(r"メタディスクリプション:\s*(.*)", article_text).group(1).strip()
            tag_names = [t.strip() for t in re.search(r"タグ:\s*(.*)", article_text).group(1).split(',') if t.strip()]
            body_md = re.sub(r"^(タイトル:.*|メタディスクリプション:.*|タグ:.*)\s*", "", article_text, flags=re.MULTILINE).strip()

            print("\n[ステップ 1/3] 全てのローカル画像を並列アップロード中...")
            featured_media_id = None
            image_block_map = {}
            
            with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
                future_to_placeholder = {}

                # アイキャッチ画像のアップロードタスク
                eyecatch_info = image_data.get("eyecatch", {})
                eyecatch_path = generated_images_dir / eyecatch_info.get("filename", "")
                if eyecatch_path.exists():
                    future = executor.submit(self.upload_image, site_info, credentials, eyecatch_path, title)
                    future_to_placeholder[future] = "eyecatch"

                # H3画像のアップロードタスク
                for h3_info in image_data.get("h3_images", []):
                    h3_path = generated_images_dir / h3_info.get("filename", "")
                    if h3_path.exists():
                        future = executor.submit(self.upload_image, site_info, credentials, h3_path, f"H3 Image for {title}")
                        future_to_placeholder[future] = h3_info["placeholder"]

                for future in concurrent.futures.as_completed(future_to_placeholder):
                    placeholder = future_to_placeholder[future]
                    try:
                        res = future.result()
                        if res.get("success"):
                            if placeholder == "eyecatch":
                                featured_media_id = res.get("media_id")
                            else:
                                image_attrs = {
                                    "id": res["media_id"],
                                    "sizeSlug": "large",
                                    "linkDestination": "none",
                                }
                                image_attrs_json = json.dumps(image_attrs)
                                block = f'<!-- wp:image {image_attrs_json} --><figure class="wp-block-image size-large"><img src="{res["image_url"]}" alt="{html.escape(title)}" class="wp-image-{res["media_id"]}"/></figure><!-- /wp:image -->'
                                image_block_map[placeholder] = block
                    except Exception as exc:
                        print(f"  -> [NG] {placeholder} のアップロード中に例外が発生: {exc}")

            print("\n[ステップ 2/3] 本文をWordPressブロックに変換中...")
            final_blocks = []
            sections = re.split(r'(^## .*$|^### .*$)', body_md, flags=re.MULTILINE)
            
            intro_md = sections[0].strip()
            if intro_md:
                intro_html = markdown.markdown(intro_md, extensions=['tables', 'fenced_code'])
                final_blocks.append(self._html_to_native_blocks(intro_html))

            for i in range(1, len(sections), 2):
                header = sections[i].strip()
                content_md = sections[i+1].strip()

                level = header.count('#')
                text = header.lstrip('# ').strip()
                final_blocks.append(f'<!-- wp:heading {{\"level\":{level}}} --><h{level}>{html.escape(text)}</h{level}><!-- /wp:heading -->')

                for placeholder, block in image_block_map.items():
                    if placeholder in content_md:
                        final_blocks.append(block)
                        content_md = content_md.replace(placeholder, "")

                if content_md.strip():
                    content_html = markdown.markdown(content_md, extensions=['tables', 'fenced_code'])
                    final_blocks.append(self._html_to_native_blocks(content_html))

            final_content_string = "\n\n".join(filter(None, final_blocks))

            print("\n[ステップ 3/3] WordPressへ投稿中...")
            tag_ids = self.get_or_create_tag_ids(site_info, credentials, tag_names)
            
            post_data = {'title': title, 'content': final_content_string, 'status': 'draft', 'tags': tag_ids, 'meta': {'_aioseo_description': meta_desc}}
            if featured_media_id: post_data['featured_media'] = featured_media_id

            return self.create_post(site_info, credentials, post_data)

        except FileNotFoundError as e:
            return {"success": False, "error": f"キャッシュファイルが見つかりません: {e.filename}"}
        except Exception as e:
            import traceback
            return {"success": False, "error": f"キャッシュからの投稿中にエラーが発生: {e}\n{traceback.format_exc()}"}

    def post_article_from_data(self, site_info: Dict, credentials: Dict, article_data: Dict, main_keyword: str) -> Dict:
        """
        受け取った記事データ（テキストと画像情報）を元にWordPressに投稿する。
        """
        print("\n--- 記事データからの投稿処理を開始します ---")
        try:
            article_text = article_data.get("article_text", "")
            image_data = article_data.get("image_data", {})
            
            if not article_text:
                return {"success": False, "error": "記事テキストが空です。"}

            generated_images_dir = Path("generated_images")

            title = re.search(r"タイトル:\s*(.*)", article_text).group(1).strip()
            meta_desc = re.search(r"メタディスクリプション:\s*(.*)", article_text).group(1).strip()
            tag_names = [t.strip() for t in re.search(r"タグ:\s*(.*)", article_text).group(1).split(',') if t.strip()]
            body_md = re.sub(r"^(タイトル:.*|メタディスクリプション:.*|タグ:.*)\s*", "", article_text, flags=re.MULTILINE).strip()

            print("\n[ステップ 1/3] 全てのローカル画像を並列アップロード中...")
            featured_media_id = None
            image_block_map = {}
            
            with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
                future_to_placeholder = {}

                # アイキャッチ画像のアップロードタスク
                eyecatch_info = image_data.get("eyecatch", {})
                eyecatch_path = generated_images_dir / eyecatch_info.get("filename", "")
                if eyecatch_path.exists():
                    future = executor.submit(self.upload_image, site_info, credentials, eyecatch_path, title)
                    future_to_placeholder[future] = "eyecatch"

                # H3画像のアップロードタスク
                for h3_info in image_data.get("h3_images", []):
                    h3_path = generated_images_dir / h3_info.get("filename", "")
                    if h3_path.exists():
                        future = executor.submit(self.upload_image, site_info, credentials, h3_path, f"H3 Image for {title}")
                        future_to_placeholder[future] = h3_info["placeholder"]

                for future in concurrent.futures.as_completed(future_to_placeholder):
                    placeholder = future_to_placeholder[future]
                    try:
                        res = future.result()
                        if res.get("success"):
                            if placeholder == "eyecatch":
                                featured_media_id = res.get("media_id")
                            else:
                                image_attrs = {
                                    "id": res["media_id"],
                                    "sizeSlug": "large",
                                    "linkDestination": "none",
                                }
                                image_attrs_json = json.dumps(image_attrs)
                                block = f'<!-- wp:image {image_attrs_json} --><figure class="wp-block-image size-large"><img src="{res["image_url"]}" alt="{html.escape(title)}" class="wp-image-{res["media_id"]}"/></figure><!-- /wp:image -->'
                                image_block_map[placeholder] = block
                    except Exception as exc:
                        print(f"  -> [NG] {placeholder} のアップロード中に例外が発生: {exc}")

            print("\n[ステップ 2/3] 本文をWordPressブロックに変換中...")
            final_blocks = []
            sections = re.split(r'(^## .*$|^### .*$)', body_md, flags=re.MULTILINE)
            
            intro_md = sections[0].strip()
            if intro_md:
                intro_html = markdown.markdown(intro_md, extensions=['tables', 'fenced_code'])
                final_blocks.append(self._html_to_native_blocks(intro_html))

            for i in range(1, len(sections), 2):
                header = sections[i].strip()
                content_md = sections[i+1].strip()

                level = header.count('#')
                text = header.lstrip('# ').strip()
                final_blocks.append(f'<!-- wp:heading {{\"level\":{level}}} --><h{level}>{html.escape(text)}</h{level}><!-- /wp:heading -->')

                for placeholder, block in image_block_map.items():
                    if placeholder in content_md:
                        final_blocks.append(block)
                        content_md = content_md.replace(placeholder, "")

                if content_md.strip():
                    content_html = markdown.markdown(content_md, extensions=['tables', 'fenced_code'])
                    final_blocks.append(self._html_to_native_blocks(content_html))

            final_content_string = "\n\n".join(filter(None, final_blocks))

            print("\n[ステップ 3/3] WordPressへ投稿中...")
            tag_ids = self.get_or_create_tag_ids(site_info, credentials, tag_names)
            
            post_data = {'title': title, 'content': final_content_string, 'status': 'draft', 'tags': tag_ids, 'meta': {'_aioseo_description': meta_desc}}
            if featured_media_id: post_data['featured_media'] = featured_media_id

            return self.create_post(site_info, credentials, post_data)

        except Exception as e:
            import traceback
            return {"success": False, "error": f"記事データからの投稿中にエラーが発生: {e}\n{traceback.format_exc()}"}