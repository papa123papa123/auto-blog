import asyncio
import os
import csv
import json
import base64
from datetime import datetime
from pprint import pprint
from urllib.parse import urlparse
import httpx
from dotenv import load_dotenv

# --- 設定項目 ---

# .envファイルから環境変数を読み込む
load_dotenv()
DATAFORSEO_LOGIN = os.getenv("DATAFORSEO_LOGIN")
DATAFORSEO_PASSWORD = os.getenv("DATAFORSEO_PASSWORD")

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

# --- DataForSEO API関数 ---

def get_auth_header():
    """DataForSEO API認証ヘッダーを生成"""
    if not DATAFORSEO_LOGIN or not DATAFORSEO_PASSWORD:
        raise ValueError("DataForSEO認証情報が設定されていません")
    
    credentials = f"{DATAFORSEO_LOGIN}:{DATAFORSEO_PASSWORD}"
    encoded_credentials = base64.b64encode(credentials.encode()).decode()
    return {"Authorization": f"Basic {encoded_credentials}"}

async def submit_batch_tasks(client: httpx.AsyncClient, keywords: list, pingback_url: str = None):
    """DataForSEOにバッチタスクを投入"""
    
    # バッチタスクを作成
    tasks = []
    
    for keyword in keywords:
        # 通常検索タスク
        tasks.append({
            "keyword": keyword,
            "location_code": 2392,  # Japan
            "language_code": "ja",
            "device": "desktop",
            "os": "windows"
        })
        
        # allintitle検索タスク  
        tasks.append({
            "keyword": f"allintitle:{keyword}",
            "location_code": 2392,  # Japan
            "language_code": "ja", 
            "device": "desktop",
            "os": "windows"
        })
    
    payload = tasks
    if pingback_url:
        for task in payload:
            task["pingback_url"] = pingback_url
    
    headers = get_auth_header()
    headers["Content-Type"] = "application/json"
    
    try:
        print(f"DataForSEOに {len(tasks)} 件のバッチタスクを投入...")
        response = await client.post(
            "https://api.dataforseo.com/v3/serp/google/organic/task_post",
            json=payload,
            headers=headers,
            timeout=30.0
        )
        response.raise_for_status()
        
        result = response.json()
        print(f"[OK] バッチタスク投入完了: {len(result.get('tasks', []))} 件")
        
        # タスクIDを収集
        task_ids = []
        for task_result in result.get('tasks', []):
            if task_result['status_code'] == 20000:
                task_ids.append(task_result['id'])
            else:
                print(f"[WARN] タスク投入失敗: {task_result.get('status_message', 'Unknown error')}")
        
        return task_ids
        
    except httpx.HTTPStatusError as e:
        print(f"DataForSEO APIエラー: {e.response.status_code}")
        print(f"レスポンス: {e.response.text}")
        return []
    except Exception as e:
        print(f"バッチタスク投入エラー: {e}")
        return []

async def get_batch_results(client: httpx.AsyncClient, task_ids: list):
    """DataForSEOからバッチ結果を取得"""
    
    headers = get_auth_header()
    headers["Content-Type"] = "application/json"
    
    payload = [{"id": task_id} for task_id in task_ids]
    
    try:
        print(f"DataForSEOから {len(task_ids)} 件の結果を取得...")
        response = await client.post(
            "https://api.dataforseo.com/v3/serp/google/organic/task_get/advanced",
            json=payload,
            headers=headers,
            timeout=60.0
        )
        response.raise_for_status()
        
        result = response.json()
        print(f"[OK] バッチ結果取得完了")
        
        return result.get('tasks', [])
        
    except httpx.HTTPStatusError as e:
        print(f"DataForSEO結果取得エラー: {e.response.status_code}")
        return []
    except Exception as e:
        print(f"結果取得エラー: {e}")
        return []

def analyze_dataforseo_results(api_results: list) -> dict:
    """DataForSEOの結果を分析"""
    organized_data = {}
    
    for task_result in api_results:
        if task_result['status_code'] != 20000:
            continue
            
        # タスクデータから検索クエリとキーワードを抽出
        task_data = task_result.get('data', [])
        if not task_data:
            continue
            
        for data in task_data:
            keyword_full = data.get('keyword', '')
            
            # allintitleかどうかを判定
            if keyword_full.startswith('allintitle:'):
                keyword = keyword_full.replace('allintitle:', '')
                search_type = 'allintitle'
            else:
                keyword = keyword_full
                search_type = 'regular'
            
            # キーワードデータを初期化
            if keyword not in organized_data:
                organized_data[keyword] = {
                    "allintitle_count": "Error",
                    "intitle_count": "Error", 
                    "weak_competitors_in_top10": [],
                    "weak_competitors_count": 0,
                    "aim_judgement": "Error",
                    "judgement_reason": "データ不足"
                }
            
            # 結果件数を取得
            total_count = data.get('total_count', 0)
            
            if search_type == 'allintitle':
                organized_data[keyword]['allintitle_count'] = total_count
            else:
                # 通常検索の場合はintitle近似とランキング分析
                organized_data[keyword]['intitle_count'] = total_count
                
                # 上位10位の競合分析
                items = data.get('items', [])
                found_competitors = []
                
                for item in items:
                    position = item.get('rank_group', 0)
                    if position > 10:
                        break
                        
                    url = item.get('url', '')
                    if not url:
                        continue
                        
                    try:
                        domain = urlparse(url).netloc
                        if domain.startswith("www."):
                            domain = domain[4:]
                            
                        if domain in WEAK_DOMAINS_SET:
                            category = DOMAIN_TO_CATEGORY[domain]
                            found_competitors.append({
                                "position": position,
                                "domain": domain,
                                "category": category,
                                "url": url
                            })
                    except Exception:
                        continue
                
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
    if not DATAFORSEO_LOGIN or not DATAFORSEO_PASSWORD:
        print("エラー: DataForSEOの認証情報が設定されていません。")
        print(".envファイルを作成し、'DATAFORSEO_LOGIN=ログイン名'と'DATAFORSEO_PASSWORD=パスワード'を記述してください。")
        return

    print(f"--- DataForSEO バッチ競合リサーチを開始します ---")
    
    # CSVファイルからキーワードを読み込む（テスト用に最初の10個のみ）
    all_keywords = load_keywords_from_csv()
    keywords = all_keywords[:10]  # テスト用
    print(f"対象キーワード数: {len(keywords)}件（全{len(all_keywords)}件中）")

    async with httpx.AsyncClient() as client:
        # バッチタスクを投入
        task_ids = await submit_batch_tasks(client, keywords)
        
        if not task_ids:
            print("バッチタスクの投入に失敗しました。")
            return
        
        # 少し待機してから結果を取得（実際にはWebhookまたはポーリングを使用）
        print("タスク処理を待機中...")
        await asyncio.sleep(10)
        
        # バッチ結果を取得
        api_results = await get_batch_results(client, task_ids)

    print("--- 全ての結果を取得しました。データを分析します ---")
    final_results = analyze_dataforseo_results(api_results)

    print("\n--- 分析結果 ---")
    pprint(final_results)

    # CSVファイルに結果を保存
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"dataforseo_competitor_results_{timestamp}.csv"
    
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
