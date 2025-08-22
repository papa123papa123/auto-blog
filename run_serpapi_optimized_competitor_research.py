import asyncio
import os
import csv
import json
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
            continue
        except Exception as e:
            print(f"[エラー] エンコーディング '{encoding}' で読み込みに失敗: {e}")
            continue
    
    print(f"[エラー] 全てのエンコーディングで失敗しました")
    return []

# 「弱い競合サイト」の定義（ドメインで指定）
WEAK_COMPETITORS = {
    "Q&Aサイト": ["chiebukuro.yahoo.co.jp", "okwave.jp", "oshiete.goo.ne.jp"],
    "大手ECモール": ["amazon.co.jp", "rakuten.co.jp", "shopping.yahoo.co.jp"],
    "無料ブログ/メディア": ["ameblo.jp", "note.com", "fc2.com", "hatenablog.com"],
}

# 高速なルックアップのために、全弱者ドメインのセットを作成
WEAK_DOMAINS_SET = {domain for sublist in WEAK_COMPETITORS.values() for domain in sublist}
# カテゴリ逆引き用の辞書も作成
DOMAIN_TO_CATEGORY = {domain: category for category, domains in WEAK_COMPETITORS.items() for domain in domains}

# --- SerpAPI最適化関数 ---

async def submit_async_search(client: httpx.AsyncClient, query: str, keyword: str, search_type: str):
    """SerpAPIに非同期検索を投入（async=true）"""
    params = {
        "api_key": SERPAPI_API_KEY,
        "q": query,
        "engine": "google",
        "gl": "jp",
        "hl": "ja",
        "num": 100,  # 100件取得でページング削減
        "async": "true"  # 非同期モード
    }
    
    try:
        response = await client.get("https://serpapi.com/search", params=params, timeout=10.0)
        response.raise_for_status()
        
        result = response.json()
        search_id = result.get("search_id")
        
        if search_id:
            return {
                "keyword": keyword,
                "search_type": search_type,
                "search_id": search_id,
                "status": "submitted"
            }
        else:
            return {
                "keyword": keyword, 
                "search_type": search_type,
                "error": "No search_id returned"
            }
            
    except httpx.HTTPStatusError as e:
        print(f"HTTPエラー: {e.response.status_code} - キーワード'{keyword}'({search_type})")
        return {"keyword": keyword, "search_type": search_type, "error": f"HTTP Error: {e.response.status_code}"}
    except Exception as e:
        print(f"エラー: {e} - キーワード'{keyword}'({search_type})")
        return {"keyword": keyword, "search_type": search_type, "error": str(e)}

async def get_search_results(client: httpx.AsyncClient, search_id: str, keyword: str, search_type: str):
    """Search Archive APIから結果を取得"""
    params = {
        "api_key": SERPAPI_API_KEY,
        "search_id": search_id
    }
    
    max_retries = 10
    retry_delay = 2
    
    for attempt in range(max_retries):
        try:
            response = await client.get("https://serpapi.com/searches/{}.json".format(search_id), params=params, timeout=10.0)
            response.raise_for_status()
            
            result = response.json()
            
            # 検索が完了しているかチェック
            search_status = result.get("search_status", "")
            
            if search_status == "Success":
                return {
                    "keyword": keyword,
                    "search_type": search_type,
                    "data": result
                }
            elif search_status in ["Processing", "Pending"]:
                # まだ処理中なので待機
                await asyncio.sleep(retry_delay)
                continue
            else:
                # エラーまたは失敗
                return {
                    "keyword": keyword,
                    "search_type": search_type, 
                    "error": f"Search failed: {search_status}"
                }
                
        except httpx.HTTPStatusError as e:
            if attempt == max_retries - 1:
                return {"keyword": keyword, "search_type": search_type, "error": f"HTTP Error: {e.response.status_code}"}
            await asyncio.sleep(retry_delay)
        except Exception as e:
            if attempt == max_retries - 1:
                return {"keyword": keyword, "search_type": search_type, "error": str(e)}
            await asyncio.sleep(retry_delay)
    
    return {"keyword": keyword, "search_type": search_type, "error": "Timeout after retries"}

async def optimized_serp_research(client: httpx.AsyncClient, keywords: list):
    """最適化されたSerpAPI競合分析（2クエリ/キーワード）"""
    
    print(f"最適化版SerpAPIで {len(keywords)} キーワードを分析します（2クエリ/キーワード）")
    
    # Phase 1: 非同期検索を一括投入
    submission_tasks = []
    for keyword in keywords:
        # 通常検索（競合順位 + タイトル解析によるintitle近似）
        submission_tasks.append(submit_async_search(client, keyword, keyword, "regular"))
        # allintitle検索（厳密な件数取得）
        submission_tasks.append(submit_async_search(client, f'allintitle:{keyword}', keyword, "allintitle"))
    
    print(f"Phase 1: {len(submission_tasks)} 件の非同期検索を投入...")
    submission_results = await asyncio.gather(*submission_tasks)
    
    # search_idを収集
    search_tasks = []
    for result in submission_results:
        if result.get("search_id"):
            search_tasks.append(get_search_results(
                client, 
                result["search_id"], 
                result["keyword"], 
                result["search_type"]
            ))
        else:
            print(f"[WARN] 投入失敗: {result.get('keyword')} ({result.get('search_type')}) - {result.get('error')}")
    
    print(f"Phase 2: {len(search_tasks)} 件の結果を取得中...")
    
    # 並列処理数を制限（50並列）
    semaphore = asyncio.Semaphore(50)
    
    async def limited_get_results(task):
        async with semaphore:
            return await task
    
    # 結果を取得
    final_results = await asyncio.gather(*[limited_get_results(task) for task in search_tasks])
    
    return final_results

def analyze_optimized_results(api_results: list) -> dict:
    """最適化版SerpAPIの結果を分析"""
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
            print(f"[WARN] キーワード '{keyword}' ({res.get('search_type', 'unknown')}) でエラー: {res.get('error', 'データなし')}")
            continue

        search_type = res["search_type"]
        data = res["data"]
        search_info = data.get("search_information", {})

        if search_type == "allintitle":
            # allintitle検索の厳密な件数
            count = search_info.get("total_results", 0)
            organized_data[keyword]["allintitle_count"] = count
            
        elif search_type == "regular":
            # 通常検索からintitle近似と競合分析
            total_results = search_info.get("total_results", 0)
            organized_data[keyword]["intitle_count"] = total_results
            
            # 上位競合分析
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
        
        # 両方のデータが揃ったら判定を実行
        if (isinstance(organized_data[keyword]["allintitle_count"], int) and 
            isinstance(organized_data[keyword]["intitle_count"], int)):
            
            aim_judgement, reason = _judge_keyword_strict(
                organized_data[keyword]["allintitle_count"],
                organized_data[keyword]["intitle_count"]
            )
            organized_data[keyword]["aim_judgement"] = aim_judgement
            organized_data[keyword]["judgement_reason"] = reason

    return organized_data

def _judge_keyword_strict(allintitle: int, intitle: int) -> tuple[str, str]:
    """厳密な判定基準でキーワードのポテンシャルを判定する"""
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

    print(f"--- SerpAPI最適化版 競合リサーチを開始します ---")
    
    # CSVファイルからキーワードを読み込む（テスト用に最初の10個のみ）
    all_keywords = load_keywords_from_csv()
    keywords = all_keywords[:10]  # テスト用
    print(f"対象キーワード数: {len(keywords)}件（全{len(all_keywords)}件中）")

    async with httpx.AsyncClient() as client:
        # 最適化されたSerpAPI分析を実行
        api_results = await optimized_serp_research(client, keywords)

    print("--- 全ての結果を取得しました。データを分析します ---")
    final_results = analyze_optimized_results(api_results)

    print("\n--- 分析結果 ---")
    pprint(final_results)

    # CSVファイルに結果を保存
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"serpapi_optimized_results_{timestamp}.csv"
    
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
