# src/yahoo_html_collector.py

import aiohttp
import asyncio
from pathlib import Path
import time
import random
from urllib.parse import quote
import logging
import shutil

# ロガーの設定
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

class YahooHTMLCollector:
    def __init__(self, output_dir: str = "yahoo_htmls", auto_cleanup: bool = True, cleanup_after_hours: int = 1):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(exist_ok=True)
        
        # 自動クリーンアップ設定
        self.auto_cleanup = auto_cleanup
        self.cleanup_after_hours = cleanup_after_hours
        
        # Yahoo検索のベースURL
        self.base_url = "https://search.yahoo.co.jp/search"
        
        # 検索クエリの種類
        self.query_types = {
            'allintitle': 'allintitle:',
            'intitle': 'intitle:', 
            'standard': ''  # 標準検索
        }
        
        # ユーザーエージェント（ブラウザを装う）
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'ja,en-US;q=0.7,en;q=0.3',
            'Accept-Encoding': 'gzip, deflate',
            'DNT': '1',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
        }
        
        print(f"[OK] YahooHTMLCollectorの初期化に成功しました。出力先: {self.output_dir}")
        if self.auto_cleanup:
            print(f"[INFO] 自動クリーンアップが有効です（分析完了後{self.cleanup_after_hours}時間でHTML削除）")
    
    async def collect_keyword_htmls(self, keyword: str, max_results: int = 10):
        """単一キーワードの全クエリタイプのHTMLを収集"""
        tasks = []
        
        for query_type, prefix in self.query_types.items():
            if prefix:
                query = f'{prefix}"{keyword}"'
            else:
                query = keyword
            
            task = self._fetch_and_save_html(keyword, query, query_type, max_results)
            tasks.append(task)
        
        await asyncio.gather(*tasks)
    
    async def collect_all_keywords_htmls(self, keywords: list[str], max_results: int = 10):
        """複数キーワードのHTMLを並列収集"""
        print(f"\n--- {len(keywords)}件のキーワードのHTML収集を開始 ---")
        
        # 並列処理でHTML収集
        tasks = []
        for keyword in keywords:
            task = self.collect_keyword_htmls(keyword, max_results)
            tasks.append(task)
        
        await asyncio.gather(*tasks)
        print("--- HTML収集完了 ---")
    
    async def _fetch_and_save_html(self, keyword: str, query: str, query_type: str, max_results: int):
        """HTMLを取得して保存"""
        params = {
            'p': query,
            'n': max_results,
            'ei': 'UTF-8',
            'fr': 'top_ga1_sa'
        }
        
        # ファイル名の生成（安全なファイル名に変換）
        safe_keyword = self._make_safe_filename(keyword)
        filename = f"{safe_keyword}_{query_type}.html"
        filepath = self.output_dir / filename
        
        # 既存ファイルのチェック（24時間以内なら再利用）
        if filepath.exists() and filepath.stat().st_mtime > time.time() - 86400:
            print(f"  -> キャッシュ使用: {filename}")
            return
        
        try:
            async with aiohttp.ClientSession(headers=self.headers) as session:
                # ランダムな待機時間（レート制限対策）
                await asyncio.sleep(random.uniform(2, 4))
                
                print(f"  -> 取得中: {query_type} - {keyword}")
                
                async with session.get(self.base_url, params=params, timeout=30) as response:
                    if response.status == 200:
                        html_content = await response.text()
                        
                        # HTMLを保存
                        with open(filepath, 'w', encoding='utf-8') as f:
                            f.write(html_content)
                        
                        print(f"    [OK] 保存完了: {filename}")
                    else:
                        print(f"    [NG] エラー {response.status}: {filename}")
                        
        except asyncio.TimeoutError:
            print(f"    [NG] タイムアウト: {filename}")
        except Exception as e:
            print(f"    [NG] 取得失敗 {filename}: {e}")
    
    def _make_safe_filename(self, keyword: str) -> str:
        """キーワードを安全なファイル名に変換"""
        # 危険な文字を置換
        unsafe_chars = ['/', '\\', ':', '*', '?', '"', '<', '>', '|']
        safe_keyword = keyword
        for char in unsafe_chars:
            safe_keyword = safe_keyword.replace(char, '_')
        
        # 長すぎる場合は短縮
        if len(safe_keyword) > 50:
            safe_keyword = safe_keyword[:50]
        
        return safe_keyword
    
    def get_collected_files(self, keyword: str) -> dict:
        """収集されたHTMLファイルのパスを取得"""
        safe_keyword = self._make_safe_filename(keyword)
        
        files = {}
        for query_type in self.query_types.keys():
            filename = f"{safe_keyword}_{query_type}.html"
            filepath = self.output_dir / filename
            files[query_type] = filepath if filepath.exists() else None
        
        return files
    
    def clear_cache(self, older_than_hours: int = 24):
        """指定時間より古いキャッシュファイルを削除"""
        cutoff_time = time.time() - (older_than_hours * 3600)
        deleted_count = 0
        
        for filepath in self.output_dir.glob("*.html"):
            if filepath.stat().st_mtime < cutoff_time:
                try:
                    filepath.unlink()
                    deleted_count += 1
                except Exception as e:
                    print(f"[WARN] ファイル削除に失敗: {filepath} - {e}")
        
        if deleted_count > 0:
            print(f"[INFO] {deleted_count}件の古いキャッシュファイルを削除しました。")
        else:
            print("[INFO] 削除対象の古いキャッシュファイルはありませんでした。")
    
    def cleanup_after_analysis(self, keywords: list[str]):
        """分析完了後のHTMLファイルをクリーンアップ"""
        if not self.auto_cleanup:
            print("[INFO] 自動クリーンアップが無効です。手動でクリーンアップしてください。")
            return
        
        print(f"\n--- 分析完了後のクリーンアップを開始 ---")
        
        # 分析対象のキーワードに関連するHTMLファイルを削除
        deleted_count = 0
        for keyword in keywords:
            safe_keyword = self._make_safe_filename(keyword)
            for query_type in self.query_types.keys():
                filename = f"{safe_keyword}_{query_type}.html"
                filepath = self.output_dir / filename
                
                if filepath.exists():
                    try:
                        filepath.unlink()
                        deleted_count += 1
                        print(f"  -> 削除: {filename}")
                    except Exception as e:
                        print(f"  -> [WARN] 削除失敗: {filename} - {e}")
        
        if deleted_count > 0:
            print(f"[OK] クリーンアップ完了: {deleted_count}件のHTMLファイルを削除しました。")
        else:
            print("[INFO] 削除対象のHTMLファイルはありませんでした。")
        
        # 空になったディレクトリも削除
        try:
            if self.output_dir.exists() and not any(self.output_dir.iterdir()):
                self.output_dir.rmdir()
                print(f"[INFO] 空のディレクトリを削除しました: {self.output_dir}")
        except Exception as e:
            print(f"[WARN] ディレクトリ削除に失敗: {e}")
    
    def schedule_cleanup(self, keywords: list[str]):
        """指定時間後に自動クリーンアップをスケジュール"""
        if not self.auto_cleanup:
            return
        
        print(f"[INFO] {self.cleanup_after_hours}時間後に自動クリーンアップをスケジュールしました。")
        
        async def delayed_cleanup():
            await asyncio.sleep(self.cleanup_after_hours * 3600)
            self.cleanup_after_analysis(keywords)
        
        # バックグラウンドでクリーンアップを実行
        asyncio.create_task(delayed_cleanup())
    
    def get_storage_info(self) -> dict:
        """ストレージ使用状況を取得"""
        total_size = 0
        file_count = 0
        
        for filepath in self.output_dir.glob("*.html"):
            if filepath.exists():
                total_size += filepath.stat().st_size
                file_count += 1
        
        return {
            'file_count': file_count,
            'total_size_bytes': total_size,
            'total_size_mb': round(total_size / (1024 * 1024), 2),
            'directory': str(self.output_dir)
        }
    
    def force_cleanup_all(self):
        """全てのHTMLファイルを強制削除"""
        print(f"\n--- 全HTMLファイルの強制削除を開始 ---")
        
        deleted_count = 0
        for filepath in self.output_dir.glob("*.html"):
            try:
                filepath.unlink()
                deleted_count += 1
                print(f"  -> 削除: {filepath.name}")
            except Exception as e:
                print(f"  -> [WARN] 削除失敗: {filepath.name} - {e}")
        
        if deleted_count > 0:
            print(f"[OK] 強制クリーンアップ完了: {deleted_count}件のHTMLファイルを削除しました。")
        else:
            print("[INFO] 削除対象のHTMLファイルはありませんでした。")
        
        # ディレクトリも削除
        try:
            if self.output_dir.exists():
                shutil.rmtree(self.output_dir)
                print(f"[INFO] ディレクトリを削除しました: {self.output_dir}")
        except Exception as e:
            print(f"[WARN] ディレクトリ削除に失敗: {e}")

# テスト用コード
if __name__ == "__main__":
    async def test_collector():
        collector = YahooHTMLCollector(auto_cleanup=True, cleanup_after_hours=1)
        test_keywords = ["日傘 おすすめ", "プログラミングスクール"]
        
        # ストレージ情報を表示
        storage_info = collector.get_storage_info()
        print(f"現在のストレージ使用状況: {storage_info}")
        
        await collector.collect_all_keywords_htmls(test_keywords)
        
        # 収集されたファイルの確認
        for keyword in test_keywords:
            files = collector.get_collected_files(keyword)
            print(f"\n{keyword}の収集ファイル:")
            for query_type, filepath in files.items():
                status = "存在" if filepath else "未収集"
                print(f"  {query_type}: {status}")
        
        # 分析完了後のクリーンアップをスケジュール
        collector.schedule_cleanup(test_keywords)
        
        # 即座にクリーンアップをテスト（実際の使用では時間後に実行）
        print("\n--- 即座クリーンアップテスト ---")
        collector.cleanup_after_analysis(test_keywords)
        
        # 最終的なストレージ情報を表示
        final_storage_info = collector.get_storage_info()
        print(f"\nクリーンアップ後のストレージ使用状況: {final_storage_info}")
    
    asyncio.run(test_collector())
