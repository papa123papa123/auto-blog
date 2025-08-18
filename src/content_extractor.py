# src/content_extractor.py

from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeoutError
import time
import requests
from bs4 import BeautifulSoup

class ContentExtractor:
    def __init__(self, timeout=20000):
        self.timeout = timeout
        print("[OK] ContentExtractorの初期化に成功しました。（Playwright + Requests fallbackモード）")

    def extract_text_with_playwright(self, url: str) -> (str, str):
        """
        Playwrightを使用してURLから本文テキストを抽出する。
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
                    body_text = page.locator('body').inner_text()
                    
                    if not body_text:
                        return "エラー", f"本文テキストの抽出に失敗しました (URL: {url})"
                        
                    return title, body_text

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