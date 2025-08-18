import asyncio
import os
import csv
from datetime import datetime
from pprint import pprint
from urllib.parse import urlparse

import httpx
from dotenv import load_dotenv

# --- 設定項目 ---

# .envファイルから環境変数を読み込む
load_dotenv()
SERPAPI_API_KEY = os.getenv("SERPAPI_API_KEY")


# 調査したいキーワードのリスト
KEYWORDS = [
    "扇風機 おすすめ",
    "サーキュレーター 静か",
    "エアコン 選び方",
    "除湿機 衣類乾燥",
    "空気清浄機 ペット"
]

# 「弱い競合サイト」の定義（ドメインで指定）
# カテゴリ分けしておくことで、結果の分析がしやすくなります。
WEAK_COMPETITORS = {
    "Q&Aサイト": ["chiebukuro.yahoo.co.jp", "okwave.jp", "oshiete.goo.ne.jp"],
    "大手ECモール": ["amazon.co.jp", "rakuten.co.jp", "shopping.yahoo.co.jp"],
    "無料ブログ/メディア": ["ameblo.jp", "note.com", "fc2.com", "hatenablog.com"],
}

# 高速なルックアップのために、全弱者ドメインのセットを作成
WEAK_DOMAINS_SET = {domain for sublist in WEAK_COMPETITORS.values() for domain in sublist}
# カテゴリ逆引き用の辞書も作成
DOMAIN_TO_CATEGORY = {domain: category for category, domains in WEAK_COMPETITORS.items() for domain in domains}

# --- スクリプト本体 ---

async def fetch_serp_results(client: httpx.AsyncClient, query: str, keyword: str, search_type: str):
    """SerpAPIに非同期でリクエストを送信し、結果を返す"""
    params = {
        "api_key": SERPAPI_API_KEY,
        "q": query,
        "engine": "google",
        "gl": "jp",
        "hl": "ja",
        "num": 10  # 上位10件のみ取得
    }
    try:
        response = await client.get("https://serpapi.com/search", params=params, timeout=20.0)
        response.raise_for_status()  # HTTPエラーがあれば例外を発生
        return {
            "keyword": keyword,
            "search_type": search_type,
            "data": response.json()
        }
    except httpx.HTTPStatusError as e:
        print(f"HTTPエラー: {e.response.status_code} - キーワード'{keyword}'({search_type})")
        return {"keyword": keyword, "search_type": search_type, "error": f"HTTP Error: {e.response.status_code}"}
    except Exception as e:
        print(f"エラー: {e} - キーワード'{keyword}'({search_type})")
        return {"keyword": keyword, "search_type": search_type, "error": str(e)}

def analyze_results(api_results: list) -> dict:
    """APIから返ってきた結果のリストをキーワードごとに整理・分析する"""
    organized_data = {}

    for res in api_results:
        keyword = res["keyword"]
        if keyword not in organized_data:
            organized_data[keyword] = {
                "allintitle_count": "Error",
                "intitle_count": "Error",
                "weak_competitors_in_top10": [],
                "weak_competitors_count": 0
            }

        if res.get("error"):
            continue

        search_type = res["search_type"]
        data = res["data"]
        search_info = data.get("search_information", {})

        if search_type == "allintitle" or search_type == "intitle":
            count = search_info.get("total_results", 0)
            organized_data[keyword][f"{search_type}_count"] = count
        
        elif search_type == "regular":
            organic_results = data.get("organic_results", [])
            found_competitors = []
            for result in organic_results:
                position = result.get("position")
                link = result.get("link")
                if not link or position > 10:
                    continue

                try:
                    domain = urlparse(link).netloc
                    # www. は削除して判定
                    if domain.startswith("www."):
                        domain = domain[4:]

                    if domain in WEAK_DOMAINS_SET:
                        category = DOMAIN_TO_CATEGORY[domain]
                        found_competitors.append({
                            "position": position,
                            "domain": domain,
                            "category": category,
                            "url": link
                        })
                except Exception:
                    continue # URLパースエラーは無視
            
            organized_data[keyword]["weak_competitors_in_top10"] = sorted(found_competitors, key=lambda x: x['position'])
            organized_data[keyword]["weak_competitors_count"] = len(found_competitors)

    return organized_data

async def main():
    """メインの非同期処理"""
    if not SERPAPI_API_KEY:
        print("エラー: SerpAPIのAPIキーが設定されていません。")
        print(".envファイルを作成し、'SERPAPI_API_KEY=あなたのキー'と記述してください。")
        return

    print(f"--- 高速競合リサーチを開始します ---")
    print(f"対象キーワード数: {len(KEYWORDS)}件")

    tasks = []
    async with httpx.AsyncClient() as client:
        for keyword in KEYWORDS:
            # 3種類の検索タスクを作成
            tasks.append(fetch_serp_results(client, f'allintitle:"{keyword}"', keyword, "allintitle"))
            tasks.append(fetch_serp_results(client, f'intitle:"{keyword}"', keyword, "intitle"))
            tasks.append(fetch_serp_results(client, keyword, keyword, "regular"))
        
        print(f"合計 {len(tasks)} 件のAPIリクエストを並列で実行します...")
        api_results = await asyncio.gather(*tasks)

    print("--- 全ての結果を取得しました。データを分析します ---")
    final_results = analyze_results(api_results)

    print("\n--- 分析結果 ---")
    pprint(final_results)

    # CSVファイルに結果を保存
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"competitor_research_results_{timestamp}.csv"
    
    with open(filename, "w", newline="", encoding="utf-8-sig") as f:
        writer = csv.writer(f)
        # ヘッダー
        writer.writerow([
            "キーワード", "allintitle件数", "intitle件数", 
            "弱い競合の件数(10位以内)", "弱い競合の詳細"
        ])
        # データ
        for keyword, data in final_results.items():
            competitors_str = "; ".join(
                [f"{c['position']}位:{c['category']}({c['domain']})" for c in data['weak_competitors_in_top10']]
            )
            writer.writerow([
                keyword,
                data["allintitle_count"],
                data["intitle_count"],
                data["weak_competitors_count"],
                competitors_str
            ])

    print(f"\n結果を '{filename}' に保存しました。")


if __name__ == "__main__":
    asyncio.run(main())
