import os, json, asyncio
from pathlib import Path
import httpx
from dotenv import load_dotenv

# ---- env をこのファイルの隣の .env に固定 ----
load_dotenv(dotenv_path=Path(__file__).parent / ".env")

BASE = os.getenv("DATAFORSEO_BASE", "https://api.dataforseo.com/v3").rstrip("/")
LOGIN = os.getenv("DATAFORSEO_LOGIN")
PASSWORD = os.getenv("DATAFORSEO_PASSWORD")
LANG = os.getenv("DATAFORSEO_LANGUAGE_CODE", "ja")
LOC  = int(os.getenv("DATAFORSEO_LOCATION_CODE", "2392"))  # Japan

def _uniq_keep_order(seq):
    seen, out = set(), []
    for s in seq:
        if not s: continue
        if s not in seen:
            out.append(s); seen.add(s)
    return out

def _iter_results(j):
    if not isinstance(j, dict):
        print(f"DEBUG: _iter_results received non-dict: {type(j)} = {j}")
        return
    for t in (j or {}).get("tasks", []) or []:
        for res in t.get("result", []) or []:
            yield res

def extract_google_autocomplete(j):
    out = []
    for res in _iter_results(j):
        for it in res.get("items", []) or []:
            if it.get("type") == "autocomplete":
                s = it.get("suggestion") or it.get("text") or it.get("value")
                if s: out.append(s)
    return out

def extract_related_and_paa(j):
    rel, paa = [], []
    for res in _iter_results(j):
        for blk in res.get("items", []) or []:
            if not isinstance(blk, dict):
                print(f"DEBUG: blk is not dict: {type(blk)} = {blk}")
                continue
            t = blk.get("type")
            if t == "related_searches":
                for it in blk.get("items", []) or []:
                    if not isinstance(it, dict):
                        print(f"DEBUG: it is not dict: {type(it)} = {it}")
                        continue
                    v = it.get("title") or it.get("keyword") or it.get("text") or it.get("suggestion")
                    if v: rel.append(v)
            elif t == "people_also_ask":
                for it in blk.get("items", []) or []:
                    if not isinstance(it, dict):
                        print(f"DEBUG: it is not dict: {type(it)} = {it}")
                        continue
                    v = it.get("title") or it.get("question") or it.get("text")
                    if v: paa.append(v)
    return rel, paa

def extract_labs_keywords(j):
    out = []
    print(f"DEBUG: _iter_results count: {sum(1 for _ in _iter_results(j))}")
    for res in _iter_results(j):
        print(f"DEBUG: res keys: {list(res.keys())}")
        items = res.get("items", []) or []
        print(f"DEBUG: items count: {len(items)}")
        for i, it in enumerate(items):
            print(f"DEBUG: item[{i}] type: {it.get('type')}, keys: {list(it.keys())}")
            if it.get("type") == "keyword_data":
                kw_data = it.get("keyword_data", {})
                print(f"DEBUG: keyword_data keys: {list(kw_data.keys())}")
                kw = kw_data.get("keyword")
                if kw: 
                    out.append(kw)
                    print(f"DEBUG: Added keyword: {kw}")
    return out

async def _post(client, endpoint, tasks):
    r = await client.post(f"{BASE}{endpoint}", json=tasks, timeout=60)
    return r

async def check_user():
    async with httpx.AsyncClient(auth=(LOGIN, PASSWORD)) as c:
        r = await c.get(f"{BASE}/appendix/user_data", timeout=30)
        j = r.json()
        ok = j.get("status_code") == 20000
        print("ACCOUNT:", j.get("status_code"), j.get("status_message"))
        return ok

def google_auto_task(keyword, cursor=0):
    return {
        "language_code": LANG, "location_code": LOC,
        "keyword": keyword, "client": "chrome",
        "cursor_pointer": cursor  # cursor_pointer を活用
    }

def google_serp_task(keyword):
    return {
        "language_code": LANG, "location_code": LOC,
        "keyword": keyword, "device": "desktop"
    }

async def collect_google_recursive(seed_kw: str, max_depth=3, max_total=500, cursors=(0,1,2)):
    """再帰的にサジェストを収集（理論上無限）"""
    if not (LOGIN and PASSWORD):
        raise RuntimeError("LOGIN/PASSWORD が空です。.env を確認してください。")

    async with httpx.AsyncClient(auth=(LOGIN, PASSWORD),
                                 headers={"Content-Type":"application/json"}) as client:
        
        all_terms = set()  # 重複排除用
        processed = set()   # 処理済みキーワード
        to_process = [seed_kw]  # 処理待ちキュー
        depth = 0
        
        while to_process and depth < max_depth and len(all_terms) < max_total:
            current_batch = to_process[:10]  # 10件ずつ処理（軽量化）
            to_process = to_process[10:]
            
            print(f"=== DEPTH {depth + 1}: Processing {len(current_batch)} keywords ===")
            
            # 現在のバッチからサジェスト取得
            new_suggestions = []
            print(f"  サジェスト処理中... {len(current_batch)}件")
            for i, kw in enumerate(current_batch):
                if kw in processed:
                    continue
                    
                processed.add(kw)
                
                # シンプルな進捗表示
                print(f"  [{i+1:3d}/{len(current_batch):3d}] 処理中: {kw}")
                
                # 各cursorでサジェスト取得
                for c in cursors:
                    task = google_auto_task(kw, c)
                    r = await _post(client, "/serp/google/autocomplete/live/advanced", [task])
                    j = r.json()
                    suggestions = extract_google_autocomplete(j)
                    new_suggestions.extend(suggestions)
                    
                    # 結果も表示
                    if suggestions:
                        print(f"      → cursor {c}: {len(suggestions)}件取得")
                    
                    # コスト管理（0.1秒間隔）
                    await asyncio.sleep(0.05)
            
            # 新しいサジェストを追加
            new_unique = [s for s in new_suggestions if s not in all_terms]
            all_terms.update(new_unique)
            
            # 次の処理対象に追加
            to_process.extend(new_unique[:50])  # 上位50件のみ次段階に
            
            print(f"  Total unique: {len(all_terms)}, Next batch: {len(to_process)}")
            depth += 1
            
            # コスト管理（段階間隔）
            await asyncio.sleep(0.5)
        
        # 最終結果
        final_terms = list(all_terms)[:max_total]
        
        return {
            "seed": seed_kw,
            "depth_reached": depth,
            "total_unique": len(final_terms),
            "terms": final_terms
        }

async def collect_google(seed_kw: str, fanout=80, max_total=120, cursors=(0,1,2)):
    """従来の方法（比較用）"""
    if not (LOGIN and PASSWORD):
        raise RuntimeError("LOGIN/PASSWORD が空です。.env を確認してください。")

    async with httpx.AsyncClient(auth=(LOGIN, PASSWORD),
                                 headers={"Content-Type":"application/json"}) as client:
        # 1) seed のサジェスト（1件ずつPOST）
        print(f"  ステップ1: seedキーワードのサジェスト取得中... ({len(cursors)}件)")
        lvl1 = []
        for i, c in enumerate(cursors):
            print(f"    [{i+1:2d}/{len(cursors):2d}] cursor {c} 処理中...")
            task1 = google_auto_task(seed_kw, c)
            r1 = await _post(client, "/serp/google/autocomplete/live/advanced", [task1])
            j1 = r1.json()
            suggestions = extract_google_autocomplete(j1)
            lvl1.extend(suggestions)
            print(f"      → {len(suggestions)}件取得完了")
        lvl1 = _uniq_keep_order(lvl1)
        print(f"    ステップ1完了: {len(lvl1)}件のユニークサジェスト")

        # 2) seed の SERP（関連検索 + PAA）
        print(f"  ステップ2: SERP関連検索・PAA取得中...")
        r2 = await _post(client, "/serp/google/organic/live/advanced", [google_serp_task(seed_kw)])
        j2 = r2.json()
        related, paa = extract_related_and_paa(j2)
        print(f"    ステップ2完了: 関連検索 {len(related)}件, PAA {len(paa)}件")

        # 3) 再サジェスト（1件ずつPOST）
        base_pool = _uniq_keep_order(lvl1 + related + paa)
        to_fan = base_pool[:fanout]
        lvl2 = []
        if to_fan:
            print(f"  ステップ3: 再サジェスト処理中... {len(to_fan)}件")
            for i, k in enumerate(to_fan):
                # 進捗表示
                print(f"    [{i+1:3d}/{len(to_fan):3d}] 処理中: {k}")
                
                task2 = google_auto_task(k, 0)
                r3 = await _post(client, "/serp/google/autocomplete/live/advanced", [task2])
                j3 = r3.json()
                suggestions = extract_google_autocomplete(j3)
                lvl2.extend(suggestions)
                
                # 結果も表示
                print(f"      → {len(suggestions)}件のサジェスト取得完了")
            lvl2 = _uniq_keep_order(lvl2)
            print(f"    ステップ3完了: {len(lvl2)}件の再サジェスト")
        else:
            print(f"  ステップ3: 再サジェスト対象なし（base_pool: {len(base_pool)}件）")

        all_terms = _uniq_keep_order(base_pool + lvl2)[:max_total]
        
        # 4) Labs Related Keywords（薄い時用の保険）
        if len(all_terms) < 50:  # 50件未満なら追加
            print(f"  ステップ4: Labs Related Keywords取得中... (現在{len(all_terms)}件)")
            labs_task = {
                "keyword": seed_kw,
                "language_code": LANG,
                "location_name": "Japan",
                "depth": 2,
                "limit": 150,
                "include_seed_keyword": False
            }
            r4 = await _post(client, "/dataforseo_labs/google/related_keywords/live", [labs_task])
            j4 = r4.json()
            print(f"      → Labs API status: {j4.get('status_code')}")
            labs_keywords = extract_labs_keywords(j4)
            print(f"      → Labsから {len(labs_keywords)}件取得")
            if labs_keywords:
                print(f"      → サンプル: {labs_keywords[:3]}")
            all_terms = _uniq_keep_order(all_terms + labs_keywords)[:max_total]
            print(f"    ステップ4完了: 合計 {len(all_terms)}件")
        else:
            print(f"  ステップ4: Labs処理スキップ（現在{len(all_terms)}件で十分）")

        # 最終結果サマリー
        print(f"\n=== 収集完了サマリー ===")
        print(f"  ステップ1 (seedサジェスト): {len(lvl1)}件")
        print(f"  ステップ2 (SERP関連): {len(related) + len(paa)}件")
        print(f"  ステップ3 (再サジェスト): {len(lvl2)}件")
        print(f"  最終ユニーク数: {len(all_terms)}件")

        return {
            "seed": seed_kw,
            "counts": {
                "lvl1_auto": len(lvl1),
                "related": len(related),
                "paa": len(paa),
                "lvl2_auto": len(lvl2),
                "total": len(all_terms)
            },
            "terms": all_terms
        }

if __name__ == "__main__":
    import sys
    kw = sys.argv[1] if len(sys.argv) > 1 else "テスト"
    method = sys.argv[2] if len(sys.argv) > 2 else "recursive"  # recursive or normal
    
    if not asyncio.run(check_user()):
        raise SystemExit("認証に失敗。/appendix/user_data が 20000 になること。")
    
    if method == "recursive":
        print("=== 再帰的サジェスト収集（理論上無限） ===")
        res = asyncio.run(collect_google_recursive(kw, max_depth=2, max_total=150, cursors=(0,1,2)))  # 元の設定
        print("\n=== SUMMARY (Recursive) ===")
        print(f"Depth reached: {res['depth_reached']}")
        print(f"Total unique: {res['total_unique']}")
        print("\nTOP 100:")
        for t in res["terms"][:100]:
            print("-", t)
    else:
        print("=== 従来の方法 ===")
        res = asyncio.run(collect_google(kw, fanout=80, max_total=120, cursors=(0,1,2)))  # 元の設定
        print("\n=== SUMMARY (Normal) ===")
        print(json.dumps(res["counts"], ensure_ascii=False, indent=2))
        print("\nTOP 100:")
        for t in res["terms"][:100]:
            print("-", t)
