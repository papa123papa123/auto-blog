# src/content_extractor.py

from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeoutError
import time
import requests
from bs4 import BeautifulSoup
from pathlib import Path

class ContentExtractor:
    def __init__(self, timeout=20000):
        self.timeout = timeout
        print("[OK] ContentExtractorの初期化に成功しました。（ローカルHTML処理モード対応）")

    def download_html_with_playwright(self, url: str) -> str:
        """Playwrightを使ってURLから完全なHTMLコンテンツをダウンロードする。"""
        try:
            with sync_playwright() as p:
                browser = p.chromium.launch(headless=True)
                page = browser.new_page()
                try:
                    page.goto(url, timeout=self.timeout, wait_until='domcontentloaded')
                    time.sleep(3) # 動的コンテンツの読み込みを待つ
                    html_content = page.content()
                    return html_content
                finally:
                    browser.close()
        except Exception as e:
            print(f"    [ERROR] PlaywrightでのHTMLダウンロード中にエラー (URL: {url}): {e}")
            return None

    def extract_text_from_local_html(self, html_path: Path) -> (str, str):
        """ローカルのHTMLファイルをPlaywrightで開き、本文テキストを抽出する。"""
        try:
            with sync_playwright() as p:
                browser = p.chromium.launch(headless=True)
                page = browser.new_page()
                try:
                    html_content = html_path.read_text(encoding="utf-8")
                    # ローカルHTMLをセット。waitUntilはネットワーク待機がないため不要
                    page.set_content(html_content)
                    
                    title = page.title()

                    main_content_selectors = [
                        'article', 'main', '[role="main"]', '#content', '#main-content',
                        '.main-content', '.post-content', '.entry-content'
                    ]
                    
                    body_text = ""
                    for selector in main_content_selectors:
                        element = page.query_selector(selector)
                        if element:
                            body_text = element.inner_text()
                            break
                    
                    if not body_text:
                        page.evaluate("""
                            () => {
                                const selectorsToRemove = ['header', 'footer', 'nav', 'aside', 'script', 'style', '.ad', '#ad', '[class*="advert"]'];
                                selectorsToRemove.forEach(selector => {
                                    document.querySelectorAll(selector).forEach(el => el.remove());
                                });
                            }
                        """)
                        body_element = page.query_selector('body')
                        if body_element:
                            body_text = body_element.inner_text()

                    if not body_text or not body_text.strip():
                        return "エラー", f"本文テキストの抽出に失敗しました (File: {html_path.name})"
                        
                    return title, body_text.strip()

                finally:
                    browser.close()
        except Exception as e:
            return "エラー", f"ローカルHTML処理中にエラー (File: {html_path.name}): {e}"

    # --- 既存のメソッドは後方互換性のために残す ---

    def extract_text_with_playwright(self, url: str) -> (str, str):
        """
        Playwrightを使用してURLから本文テキストを抽出する。
        本文領域を特定し、ノイズを除去するよう改良。
        成功した場合は(タイトル, 本文)、失敗した場合は("エラー", エラーメッセージ)を返す。
        """
        try:
            with sync_playwright() as p:
                browser = p.chromium.launch(headless=True)
                page = browser.new_page()
                
                try:
                    page.goto(url, timeout=self.timeout, wait_until='domcontentloaded')
                    time.sleep(2) 
                    title = page.title()

                    # 本文抽出ロジックの改良
                    main_content_selectors = [
                        'article',
                        'main',
                        '[role="main"]',
                        '#content',
                        '#main-content',
                        '.main-content',
                        '.post-content',
                        '.entry-content'
                    ]
                    
                    body_text = ""
                    for selector in main_content_selectors:
                        element = page.query_selector(selector)
                        if element:
                            print(f"    -> 本文領域を発見しました (セレクタ: {selector})")
                            body_text = element.inner_text()
                            break
                    
                    # 上記セレクタで見つからない場合のフォールバック
                    if not body_text:
                        print("    -> [WARN] 主要な本文セレクタが見つかりませんでした。body全体から抽出を試みます。")
                        body_element = page.query_selector('body')
                        if body_element:
                            # 不要な要素をJavaScriptで削除
                            page.evaluate("""
                                () => {
                                    const selectorsToRemove = ['header', 'footer', 'nav', 'aside', 'script', 'style', '.ad', '#ad', '[class*="advert"]'];
                                    selectorsToRemove.forEach(selector => {
                                        document.querySelectorAll(selector).forEach(el => el.remove());
                                    });
                                }
                            """)
                            body_text = body_element.inner_text()

                    if not body_text or not body_text.strip():
                        return "エラー", f"本文テキストの抽出に失敗しました (URL: {url})"
                        
                    return title, body_text.strip()

                except PlaywrightTimeoutError:
                    return "エラー", f"ページの読み込みがタイムアウトしました (Playwright) (URL: {url})"
                except Exception as e:
                    return "エラー", f"ページ処理中に予期せぬエラーが発生しました (Playwright) (URL: {url}): {e}"
                finally:
                    browser.close()

        except Exception as e:
            return "エラー", f"Playwrightの初期化または終了処理中にエラーが発生しました: {e}"

    def extract_text_with_requests(self, url: str) -> (str, str):
        """
        RequestsとBeautifulSoupを使用してURLから本文テキストを抽出するフォールバックメソッド。
        """
        try:
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
            }
            response = requests.get(url, headers=headers, timeout=15)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.content, 'html.parser')
            
            for element in soup(['script', 'style', 'header', 'footer', 'nav', 'aside']):
                element.decompose()
            
            title = soup.title.string if soup.title else "No Title"
            body_text = soup.body.get_text(separator='\n', strip=True) if soup.body else ""
            
            if not body_text:
                return "エラー", f"本文テキストの抽出に失敗しました (Requests) (URL: {url})"
            
            return title, body_text
        except requests.exceptions.RequestException as e:
            return "エラー", f"ページの読み込みに失敗しました (Requests) (URL: {url}): {e}"
        except Exception as e:
            return "エラー", f"テキスト抽出中に予期せぬエラーが発生しました (Requests) (URL: {url}): {e}"

    def extract_text_from_url(self, url: str) -> (str, str):
        """
        [互換性のためのラッパーメソッド]
        新しいPlaywrightベースの抽出メソッドを呼び出す。
        """
        return self.extract_text_with_playwright(url)
