# file: collect_keywords_one_shot.py
import os, json, asyncio
from pathlib import Path
import httpx
from dotenv import load_dotenv

# ----- env 読み込みを"ファイルのある場所"に固定 -----
load_dotenv(dotenv_path=Path(__file__).parent / ".env")

BASE = os.getenv("DATAFORSEO_BASE", "https://api.dataforseo.com/v3").rstrip("/")
LOGIN = os.getenv("DATAFORSEO_LOGIN")
PASSWORD = os.getenv("DATAFORSEO_PASSWORD")
LANG = os.getenv("DATAFORSEO_LANGUAGE_CODE", "ja")
LOC  = int(os.getenv("DATAFORSEO_LOCATION_CODE", "2840"))  # 2840=Japan

def _auth_ok() -> bool:
    return bool(LOGIN and PASSWORD)

def _log(title, payload=None, resp=None):
    print(f"\n=== {title} ===")
    if payload is not None:
        print("payload:", json.dumps(payload, ensure_ascii=False)[:600])
    if resp is not None:
        try:
            j = resp.json()
        except Exception:
            j = {"raw": resp.text[:500]}
        print("status:", resp.status_code, "|", j.get("status_code"), j.get("status_message"), "| cost:", j.get("cost"))
        if "tasks_count" in j:
            print("tasks_count:", j.get("tasks_count"))

async def _post(client: httpx.AsyncClient, endpoint: str, tasks: list):
    url = f"{BASE}{endpoint}"
    resp = await client.post(url, json=tasks, timeout=60)
    return resp

async def check_user():
    async with httpx.AsyncClient(auth=(LOGIN, PASSWORD)) as c:
        r = await c.get(f"{BASE}/appendix/user_data", timeout=30)
        _log("ACCOUNT CHECK", resp=r)
        j = r.json()
        ok = j.get("status_code") == 20000
        return ok, j

# ---- Google: Autocomplete Advanced（サジェストの"核"） ----
def make_google_autocomplete_task(keyword: str):
    return {
        "language_code": LANG,
        "location_code": LOC,
        "keyword": keyword,
        "client": "chrome-omni",
        "cursor_pointer": 0
    }

# ---- Google: SERP Organic Advanced（関連検索/People also ask 抽出）----
def make_google_serp_task(keyword: str):
    return {
        "language_code": LANG,
        "location_code": LOC,
        "keyword": keyword,
        "device": "desktop"
    }

# ---- Yahoo: SERP Organic（関連検索抽出のみ。Autocompleteは無い） ----
def make_yahoo_serp_task(keyword: str):
    return {
        "language_code": LANG,
        "location_code": LOC,
        "keyword": keyword,
        "device": "desktop"
    }

def _uniq_keep_order(seq):
    seen = set()
    out = []
    for s in seq:
        if not s: 
            continue
        if s not in seen:
            out.append(s)
            seen.add(s)
    return out

def _extract_google_autocomplete_items(task_json):
    # /serp/google/autocomplete/live/advanced の items 抽出
    out = []
    for r in task_json.get("result", []) or []:
        for it in r.get("items", []) or []:
            val = it.get("value") or it.get("text")
            if val:
                out.append(val)
    return out

def _extract_related_from_serp(task_json):
    # Google/Yahoo 共通: SERPの related_searches を拾う
    out = []
    for r in task_json.get("result", []) or []:
        for block in r.get("items", []) or []:
            if block.get("type") == "related_searches":
                for it in block.get("items", []) or []:
                    v = it.get("title") or it.get("keyword") or it.get("text")
                    if v:
                        out.append(v)
    return out

async def collect(main_kw: str, yahoo_enable=True, fanout_limit=80):
    if not _auth_ok():
        raise RuntimeError("DATAFORSEO_LOGIN/PASSWORD が読み込めていません (.env を確認)")

    async with httpx.AsyncClient(auth=(LOGIN, PASSWORD), headers={"Content-Type": "application/json"}) as client:
        # 1) Google Autocomplete（外形1POST）
        g_auto_tasks = [make_google_autocomplete_task(main_kw)]
        r1 = await _post(client, "/serp/google/autocomplete/live/advanced", g_auto_tasks)
        _log("GOOGLE AUTOCOMPLETE ADVANCED", g_auto_tasks, r1)
        g_auto = r1.json()
        level1 = _uniq_keep_order(_extract_google_autocomplete_items(g_auto))

        # 2) Google SERP（関連検索）＋（任意）Yahoo SERP（関連検索）をバッチ
        serp_tasks = [
            {"postback": {"engine":"google"}, **make_google_serp_task(main_kw)}
        ]
        if yahoo_enable:
            serp_tasks.append({"postback": {"engine":"yahoo"}, **make_yahoo_serp_task(main_kw)})

        # Google: /serp/google/organic/live/advanced
        r2g = await _post(client, "/serp/google/organic/live/advanced", serp_tasks[:1])
        _log("GOOGLE SERP ORGANIC ADV", serp_tasks[:1], r2g)
        g_serp = r2g.json()
        related_google = _extract_related_from_serp(g_serp)

        related_yahoo = []
        if yahoo_enable:
            # Yahoo: /serp/yahoo/organic/live  （advanced が無いプランでもこちらは通る想定）
            r2y = await _post(client, "/serp/yahoo/organic/live", [serp_tasks[1]])
            _log("YAHOO SERP ORGANIC", [serp_tasks[1]], r2y)
            y_serp = r2y.json()
            related_yahoo = _extract_related_from_serp(y_serp)

        # 3) 1段深掘り：level1（Googleサジェスト）をまとめて"外形1POST"で再サジェスト
        #    → ここで20〜60件程度まで一気に増える想定。fanout_limit で上限管理
        second_kw = level1[:fanout_limit]
        if second_kw:
            tasks2 = [make_google_autocomplete_task(k) for k in second_kw]
            r3 = await _post(client, "/serp/google/autocomplete/live/advanced", tasks2)
            _log("GOOGLE AUTOCOMPLETE ADVANCED (2nd batch)", f"{len(tasks2)} tasks", r3)
            g_auto2 = r3.json()
            lvl2 = _uniq_keep_order(_extract_google_autocomplete_items(g_auto2))
        else:
            lvl2 = []

        # 統合 & 重複排除
        all_terms = _uniq_keep_order(level1 + related_google + related_yahoo + lvl2)

        return {
            "seed": main_kw,
            "counts": {
                "level1_google_auto": len(level1),
                "google_related": len(related_google),
                "yahoo_related": len(related_yahoo),
                "level2_google_auto": len(lvl2),
                "total_unique": len(all_terms),
            },
            "suggestions": all_terms
        }

if __name__ == "__main__":
    import sys
    main_kw = sys.argv[1] if len(sys.argv) > 1 else "テスト"
    ok, info = asyncio.run(check_user())
    if not ok:
        raise SystemExit("認証に失敗しました。/appendix/user_data が 20000 になることを確認してください。")
    result = asyncio.run(collect(main_kw, yahoo_enable=True, fanout_limit=80))
    print("\n=== SUMMARY ===")
    print(json.dumps(result["counts"], ensure_ascii=False, indent=2))
    print("\nTOP 50:")
    for t in result["suggestions"][:50]:
        print("-", t)
