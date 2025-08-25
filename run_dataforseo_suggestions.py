# run_dataforseo_suggestions.py  --- 強化診断 & 安定版
# 使い方:
#   python run_dataforseo_suggestions.py "エアコン 掃除"
# 注意:
#   BASE は本番 https://api.dataforseo.com/v3 を使います（sandboxだと items が空になりやすい）

import os, sys, json, base64
from typing import List, Dict, Tuple, Optional
import httpx
from dotenv import load_dotenv

# ===== env =====
load_dotenv()
LOGIN  = os.getenv("DATAFORSEO_LOGIN")
PASSWD = os.getenv("DATAFORSEO_PASSWORD")

# 環境変数の値を確認
print("=== 環境変数の確認 ===")
print(f"DATAFORSEO_LOGIN: {LOGIN}")
print(f"DATAFORSEO_PASSWORD: {'*' * len(PASSWD) if PASSWD else 'None'}")
print(f"DATAFORSEO_BASE: {os.getenv('DATAFORSEO_BASE', 'Not set (using default)')}")
print("=" * 30)

if not LOGIN or not PASSWD:
    print("ERROR: .env に DATAFORSEO_LOGIN / DATAFORSEO_PASSWORD を設定してください")
    sys.exit(1)

# ===== const =====
BASE = os.getenv("DATAFORSEO_BASE", "https://api.dataforseo.com/v3")  # 必要なら env で一時上書き
# GOOGLE_URL   = f"{BASE}/serp/google/autocomplete/live"           # サジェスト（存在しないため削除）
GOOGLE_ADV   = f"{BASE}/serp/google/autocomplete/live/advanced"  # Advanced版のみ使用
RELATED_URL  = f"{BASE}/dataforseo_labs/google/related_keywords/live"
# YAHOO_URL    = f"{BASE}/serp/yahoo/autocomplete/live"            # 存在しないため削除
YAHOO_REGULAR_URL = f"{BASE}/serp/yahoo/live/regular"            # 構造化データ
YAHOO_HTML_URL    = f"{BASE}/serp/yahoo/live/html"               # HTMLデータ
LANG = "ja"
LOC  = int(os.getenv("DATAFORSEO_LOCATION_CODE", "2380"))  # Japan

AUTH = "Basic " + base64.b64encode(f"{LOGIN}:{PASSWD}".encode()).decode()
HEADERS = {"Authorization": AUTH, "Content-Type": "application/json"}

def http_post(url: str, payload: list) -> Tuple[int, Dict]:
    try:
        with httpx.Client(timeout=120.0) as c:
            r = c.post(url, headers=HEADERS, json=payload)
            code = r.status_code
            try:
                j = r.json()
            except Exception:
                j = {"raw": r.text}
            return code, j
    except Exception as e:
        return -1, {"exception": str(e)}

def extract_items(j: Dict) -> List[Dict]:
    try:
        return j["tasks"][0]["result"][0]["items"]
    except Exception:
        return []

def to_text_list(items: List[Dict]) -> List[str]:
    out = []
    for it in items:
        out.append(it.get("suggestion") or it.get("keyword") or it.get("text") or it.get("title"))
    return [t for t in out if t]

def diagnose_account():
    # アカウント/残高/権限チェック
    print("=== アカウント情報の詳細確認 ===")
    
    # 正しいエンドポイント: /v3/appendix/user_data
    url = f"{BASE}/appendix/user_data"
    with httpx.Client(timeout=30.0) as c:
        r = c.get(url, headers=HEADERS)
    print(f"[check] GET /appendix/user_data -> {r.status_code}")
    try:
        response_data = r.json()
        print(f"Status Code: {response_data.get('status_code')}")
        print(f"Status Message: {response_data.get('status_message')}")
        print(json.dumps(response_data, ensure_ascii=False, indent=2)[:2000])
    except Exception:
        print(r.text[:1000])
    
    # 認証ヘッダーの確認
    print(f"\n--- 認証情報の確認 ---")
    print(f"Authorization: {HEADERS['Authorization'][:20]}...")
    print(f"Content-Type: {HEADERS['Content-Type']}")

def fetch(keyword: str) -> Dict:
    payload = [{
        "keyword": keyword, 
        "language_code": LANG, 
        "location_code": LOC,
        "client": "chrome-omni",
        "cursor_pointer": 0,
        "limit": 10
    }]
    res = {"google": [], "google_adv": [], "yahoo": [], "related": []}
    dbg  = {}

    # Google (Advanced版のみ使用)
    code2, j2 = http_post(GOOGLE_ADV, payload)
    dbg["google_adv"] = {"status": code2, "message": j2.get("status_message"), "cost": j2.get("cost")}
    res["google_adv"] = to_text_list(extract_items(j2))

    # Yahoo SERP（関連検索を抽出）
    yahoo_payload = [{
        "keyword": keyword, 
        "language_code": LANG, 
        "location_code": LOC, 
        "device": "desktop"
    }]
    
    # 1. 構造化データを試行
    code3, j3 = http_post(YAHOO_REGULAR_URL, yahoo_payload)
    dbg["yahoo_regular"] = {"status": code3, "message": j3.get("status_message"), "cost": j3.get("cost")}
    
    # 2. 関連検索を抽出
    yahoo_suggestions = []
    if code3 == 200:
        try:
            # 構造化データから関連検索を抽出
            if "tasks" in j3 and j3["tasks"]:
                task = j3["tasks"][0]
                if "result" in task and task["result"]:
                    result = task["result"][0]
                    if "items" in result:
                        for item in result["items"]:
                            if "related_searches" in item:
                                yahoo_suggestions.extend(item["related_searches"])
        except Exception as e:
            print(f"Yahoo関連検索抽出エラー: {e}")
    
    # 3. 構造化データにない場合はHTMLを試行
    if not yahoo_suggestions:
        code3_html, j3_html = http_post(YAHOO_HTML_URL, yahoo_payload)
        dbg["yahoo_html"] = {"status": code3_html, "message": j3_html.get("status_message"), "cost": j3_html.get("cost")}
        
        if code3_html == 200:
            # HTMLから関連検索を抽出（簡易実装）
            try:
                html_content = j3_html.get("raw", "")
                # 関連検索のパターンを検索（簡易実装）
                # 実際の実装ではより詳細なパースが必要
                pass
            except Exception as e:
                print(f"Yahoo HTML抽出エラー: {e}")
    
    dbg["yahoo"] = {"status": code3, "message": j3.get("status_message"), "cost": j3.get("cost")}
    res["yahoo"] = yahoo_suggestions

    # Related keywords（Labs）
    code4, j4 = http_post(RELATED_URL, payload)
    dbg["related"] = {"status": code4, "message": j4.get("status_message"), "cost": j4.get("cost")}
    res["related"] = to_text_list(extract_items(j4))

    # マージ & 重複排除
    merged = []
    seen = set()
    for t in (res["google"] or []) + (res["google_adv"] or []) + (res["yahoo"] or []) + (res["related"] or []):
        key = " ".join(t.strip().lower().split())
        if key and key not in seen:
            seen.add(key)
            merged.append(t.strip())

    return {
        "debug": dbg,
        "counts": {
            "google_adv": len(res["google_adv"]),
            "yahoo": len(res["yahoo"]),
            "related": len(res["related"]),
            "merged": len(merged)
        },
        "suggestions": merged[:400],
    }

def main():
    if len(sys.argv) < 2:
        print("Usage: python run_dataforseo_suggestions.py <keyword>")
        sys.exit(1)

    keyword = " ".join(sys.argv[1:])
    print(f"BASE = {BASE}")
    print("=== ACCOUNT CHECK ===")
    diagnose_account()

    print(f"\n=== RUN: '{keyword}' ===")
    data = fetch(keyword)

    print("\n--- DEBUG (status/message/cost) ---")
    print(json.dumps(data["debug"], ensure_ascii=False, indent=2))

    print("\n=== COUNTS ===")
    print(json.dumps(data["counts"], ensure_ascii=False, indent=2))

    print("\n=== TOP 50 ===")
    for t in data["suggestions"][:50]:
        print(t)

if __name__ == "__main__":
    main()
