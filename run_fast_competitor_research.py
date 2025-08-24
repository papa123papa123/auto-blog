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

# CSVファイルからキーワードを動的に読み込む
def load_keywords_from_csv(csv_path: str = "KWラッコエクセル/rakkokeyword_2025822234915.csv") -> list:
    """ラッコキーワードCSVからキーワードを読み込む"""
    keywords = []
    
    # エンコーディングを自動判定
    encodings = ['utf-16', 'utf-16le', 'utf-8', 'shift_jis', 'cp932', 'utf-8-sig']
    
    for encoding in encodings:
        try:
            with open(csv_path, 'r', encoding=encoding) as f:
                # タブ区切りで読み込み
                reader = csv.DictReader(f, delimiter='\t')
                
                for row in reader:
                    # カラム名を正確に取得（ダブルクォートを除去）
                    keyword = row.get('キーワード', '').strip().strip('"')
                    if keyword and keyword != 'キーワード':  # ヘッダー行を除外
                        keywords.append(keyword)
                
                print(f"[OK] CSVから {len(keywords)} 個のキーワードを読み込みました（エンコーディング: {encoding}）")
                return keywords
                
        except UnicodeDecodeError:
            print(f"[DEBUG] エンコーディング '{encoding}' で失敗")
            continue
        except Exception as e:
            print(f"[エラー] エンコーディング '{encoding}' で読み込みに失敗: {e}")
            continue
    
    print(f"[エラー] 全てのエンコーディングで失敗しました")
    return []

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

async def fetch_optimized_serp_results(client: httpx.AsyncClient, keywords: list):
    """最適化されたSerpAPI呼び出し：重要なキーワードのみを効率的に処理"""
    
    # 上位10個のキーワードを処理（厳密基準クリアのため）
    top_keywords = keywords[:10]
    print(f"厳密基準クリアのため上位 {len(top_keywords)} 個のキーワードを分析します")
    
    tasks = []
    for keyword in top_keywords:
        # 各キーワードに対して3種類の検索タスクを作成
        tasks.append(fetch_serp_results(client, f'allintitle:{keyword}', keyword, "allintitle"))
        tasks.append(fetch_serp_results(client, f'intitle:{keyword}', keyword, "intitle"))
        tasks.append(fetch_serp_results(client, keyword, keyword, "regular"))
    
    print(f"合計 {len(tasks)} 件のAPIリクエストを実行...")
    
    # 並列処理数を制限して安定性を向上
    semaphore = asyncio.Semaphore(5)  # 最大5件まで並列実行
    
    async def limited_fetch(task):
        async with semaphore:
            return await task
    
    # 並列処理数を制限して実行
    api_results = await asyncio.gather(*[limited_fetch(task) for task in tasks])
    return api_results

# 旧関数は互換性のため残しておく
async def fetch_serp_results(client: httpx.AsyncClient, query: str, keyword: str, search_type: str):
    """SerpAPIに非同期でリクエストを送信し、結果を返す（旧版・互換性用）"""
    params = {
        "api_key": SERPAPI_API_KEY,
        "q": query,
        "engine": "google",
        "gl": "jp",
        "hl": "ja",
        "num": 10  # 上位10件のみ取得
    }
    try:
        response = await client.get("https://serpapi.com/search", params=params, timeout=10.0)
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
    """APIから返ってきた結果のリストをキーワードごとに整理・分析する（厳密な判定基準付き）"""
    organized_data = {}

    for res in api_results:
        keyword = res["keyword"]
        if keyword not in organized_data:
            organized_data[keyword] = {
                "allintitle_count": "Error",
                "intitle_count": "Error",
                "weak_competitors_in_top10": [],
                "weak_competitors_count": 0,
                "aim_judgement": "Error",
                "judgement_reason": "データ不足"
            }

        if res.get("error") or "data" not in res:
            print(f"[警告] キーワード '{keyword}' ({res.get('search_type', '不明')}) でエラー: {res.get('error', 'データなし')}")
            continue

        search_type = res["search_type"]
        data = res["data"]
        search_info = data.get("search_information", {})

        if search_type == "allintitle" or search_type == "intitle":
            count = search_info.get("total_results", 0)
            organized_data[keyword][f"{search_type}_count"] = count
            
            # 厳密な判定基準の適用
            if search_type == "allintitle":
                organized_data[keyword]["allintitle_count"] = count
            elif search_type == "intitle":
                organized_data[keyword]["intitle_count"] = count
                
            # 両方のデータが揃ったら判定を実行
            if (isinstance(organized_data[keyword]["allintitle_count"], int) and 
                isinstance(organized_data[keyword]["intitle_count"], int)):
                
                aim_judgement, reason = _judge_keyword_strict(
                    organized_data[keyword]["allintitle_count"],
                    organized_data[keyword]["intitle_count"]
                )
                organized_data[keyword]["aim_judgement"] = aim_judgement
                organized_data[keyword]["judgement_reason"] = reason
        
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

def _judge_keyword_strict(allintitle: int, intitle: int) -> tuple[str, str]:
    """
    厳密な判定基準でキーワードのポテンシャルを判定する
    
    Args:
        allintitle (int): allintitleの検索結果件数
        intitle (int): intitleの検索結果件数
        
    Returns:
        tuple[str, str]: 判定結果と根拠
    """
    # 厳密な基準：allintitle 10件以下 AND intitle 30,000件以下
    if allintitle <= 10 and intitle <= 30000:
        return "★★★ お宝キーワード", f"allintitle: {allintitle}件, intitle: {intitle}件 (厳密基準クリア)"
    
    # allintitleのみクリア
    elif allintitle <= 10:
        return "★★☆ 参入価値あり", f"allintitle: {allintitle}件 (intitle: {intitle}件で基準超過)"
    
    # intitleのみクリア  
    elif intitle <= 30000:
        return "★☆☆ 要検討", f"intitle: {intitle}件 (allintitle: {allintitle}件で基準超過)"
    
    # 両方とも基準超過
    else:
        return "☆☆☆ 競合多し", f"allintitle: {allintitle}件, intitle: {intitle}件 (両方とも基準超過)"

async def main():
    """メインの非同期処理"""
    if not SERPAPI_API_KEY:
        print("エラー: SerpAPIのAPIキーが設定されていません。")
        print(".envファイルを作成し、'SERPAPI_API_KEY=あなたのキー'と記述してください。")
        return

    print(f"--- 高速競合リサーチを開始します ---")
    # CSVファイルからキーワードを読み込む（コスト削減のため最初の10個のみ）
    all_keywords = load_keywords_from_csv()
    keywords = all_keywords[:10]  # 最初の10個のみ
    print(f"対象キーワード数: {len(keywords)}件（全{len(all_keywords)}件中）")

    async with httpx.AsyncClient() as client:
        # 最適化されたSerpAPI呼び出し（コスト削減版）
        api_results = await fetch_optimized_serp_results(client, keywords)

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
            "弱い競合の件数(10位以内)", "弱い競合の詳細", "AIM判定", "判定根拠"
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
                competitors_str,
                data.get("aim_judgement", "Error"),
                data.get("judgement_reason", "データ不足")
            ])

    print(f"\n結果を '{filename}' に保存しました。")


if __name__ == "__main__":
    asyncio.run(main())
