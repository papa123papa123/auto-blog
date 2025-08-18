# src/rss_feeder.py (修正・最終確定版)

import feedparser
from typing import List

class RssFeeder:
    """RSSフィードから「資産型」ブログのキーワードの種を取得するクラス"""

    def __init__(self):
        # 資産型アフィリエイトブログ向きの情報源（URLを最新版に更新・修正）
        self.feed_urls = {
            # 新製品・新サービス
            "pr_times_all": "https://prtimes.jp/index.rdf",  # より広範囲なRDF形式に変更
            
            # IT・ガジェットレビュー
            "ascii_top": "https://ascii.jp/rss.xml",
            # "kakaku_mag": "https://kakakumag.com/atom.xml", # → 2024年3月にサービス終了のためコメントアウト

            # ライフスタイル・趣味
            "go_out_web": "https://web.goout.jp/feed/",
            "roomie": "https://www.roomie.jp/feed",
            "all_about": "https://rss.allabout.co.jp/rss/aa/latest.rdf", # 全領域の新着記事フィードに変更

            # 車・バイク
            "car_watch": "https://car.watch.impress.co.jp/docs/news/index.rss",
            "bike_news": "https://bike-news.jp/feed",
            
            # 旅行・お出かけ
            "travel_watch": "https://travel.watch.impress.co.jp/docs/news/index.rss",
            "jalan_net": "https://www.jalan.net/news/feed/", # 最新のURLに変更
        }
        print("[OK] RssFeederの初期化に成功しました。（最新情報源に最適化）")

    def fetch_titles(self, max_per_feed: int = 10) -> List[str]:
        """登録されているすべてのRSSフィードから最新記事のタイトルを取得する"""
        all_titles = []
        print("[INFO] 資産型キーワードの種を取得中...")
        
        # ブラウザを装うためのヘッダー情報
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36'
        }

        for genre, url in self.feed_urls.items():
            try:
                feed = feedparser.parse(url, request_headers=headers)
                
                # --- ステータスチェックを強化 ---
                if feed.status == 200:
                    titles = [entry.title for entry in feed.entries[:max_per_feed]]
                    if titles:
                        print(f"  -> {genre} から {len(titles)}件取得")
                        all_titles.extend(titles)
                    else:
                        # 記事が0件だった場合も表示
                        print(f"  -> {genre} から 0件取得 (フィードは正常)")
                else:
                    # HTTPエラーの場合
                    print(f"[NG] {genre} でエラー発生 (HTTPステータス: {feed.status})")

            except Exception as e:
                print(f"[NG] {genre} のフィード処理中に予期せぬエラー: {e}")
        
        # 重複を削除して最終的な件数を表示
        unique_titles = list(set(all_titles))
        print(f"[OK] 合計{len(unique_titles)}件のユニークなタイトルを取得しました。")
        return unique_titles

# このファイルが直接実行された場合にテストするためのコード
if __name__ == '__main__':
    feeder = RssFeeder()
    latest_titles = feeder.fetch_titles()
    
    print("\n--- 取得したタイトル（最大30件まで表示） ---")
    if latest_titles:
        for i, title in enumerate(latest_titles[:30]):
            print(f"{i+1:2d}: {title}")
    else:
        print("タイトルを取得できませんでした。")