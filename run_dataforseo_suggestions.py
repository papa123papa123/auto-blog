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
if not LOGIN or not PASSWD:
    print("ERROR: .env に DATAFORSEO_LOGIN / DATAFORSEO_PASSWORD を設定してください")
    sys.exit(1)

# ===== const =====
BASE = os.getenv("DATAFORSEO_BASE", "https://api.dataforseo.com/v3")  # 必要なら env で一時上書き
GOOGLE_URL   = f"{BASE}/serp/google/autocomplete/live"           # サジェスト
GOOGLE_ADV   = f"{BASE}/serp/google/autocomplete/live/advanced"  # こっちでもOK
RELATED_URL  = f"{BASE}/dataforseo_labs/google/related_keywords/live"
YAHOO_URL    = f"{BASE}/serp/yahoo/autocomplete/live"            # 404 になることがあるので optional
LANG = "ja"
LOC  = 2380  # Japan

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
    url = f"{BASE}/user"
    with httpx.Client(timeout=30.0) as c:
        r = c.get(url, headers=HEADERS)
    print(f"[check] GET /user -> {r.status_code}")
    try:
        print(json.dumps(r.json(), ensure_ascii=False, indent=2)[:2000])
    except Exception:
        print(r.text[:1000])

def fetch(keyword: str) -> Dict:
    payload = [{"keyword": keyword, "language_code": LANG, "location_code": LOC}]
    res = {"google": [], "google_adv": [], "yahoo": [], "related": []}
    dbg  = {}

    # Google (通常)
    code, j = http_post(GOOGLE_URL, payload)
    dbg["google"] = {"status": code, "message": j.get("status_message"), "cost": j.get("cost")}
    res["google"] = to_text_list(extract_items(j))

    # Google (advanced) 片方が0なら補完に使う
    code2, j2 = http_post(GOOGLE_ADV, payload)
    dbg["google_adv"] = {"status": code2, "message": j2.get("status_message"), "cost": j2.get("cost")}
    res["google_adv"] = to_text_list(extract_items(j2))

    # Yahoo（404でも止めない）
    code3, j3 = http_post(YAHOO_URL, payload)
    dbg["yahoo"] = {"status": code3, "message": j3.get("status_message"), "cost": j3.get("cost")}
    res["yahoo"] = to_text_list(extract_items(j3)) if code3 == 200 else []

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
            "google": len(res["google"]),
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
