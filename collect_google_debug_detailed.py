import os
import json
import asyncio
from pathlib import Path
import httpx
from dotenv import load_dotenv

# 環境変数読み込み
load_dotenv(dotenv_path=Path(__file__).parent / ".env")

# Data for SEO設定
BASE = os.getenv("DATAFORSEO_BASE", "https://api.dataforseo.com/v3").rstrip("/")
LOGIN = os.getenv("DATAFORSEO_LOGIN")
PASSWORD = os.getenv("DATAFORSEO_PASSWORD")
LANG = os.getenv("DATAFORSEO_LANGUAGE_CODE", "ja")
LOC = int(os.getenv("DATAFORSEO_LOCATION_CODE", "2392"))  # Japan

async def debug_detailed_api_response():
    """詳細なAPIレスポンスの構造をデバッグ"""
    print("🔍 詳細なAPIレスポンスの構造をデバッグ中...")
    
    async with httpx.AsyncClient(
        auth=(LOGIN, PASSWORD),
        headers={"Content-Type": "application/json"},
        timeout=60
    ) as client:
        
        # テスト用のタスク
        task = {
            "language_code": LANG,
            "location_code": LOC,
            "keyword": "夏 おすすめ お酒",
            "depth": 2,
            "include_serp_info": True
        }
        
        try:
            print(f"📡 API呼び出し中: {BASE}/serp/google/organic/live/advanced")
            print(f"📋 タスク: {json.dumps(task, ensure_ascii=False, indent=2)}")
            
            r = await client.post(
                f"{BASE}/serp/google/organic/live/advanced",
                json=[task]
            )
            
            print(f"✅ レスポンス受信: ステータス {r.status_code}")
            
            # レスポンスの詳細を確認
            j = r.json()
            
            print(f"\n📊 レスポンス構造:")
            print(f"   - 型: {type(j)}")
            print(f"   - キー: {list(j.keys()) if isinstance(j, dict) else 'N/A'}")
            
            if isinstance(j, dict):
                print(f"   - status_code: {j.get('status_code', 'N/A')}")
                print(f"   - status_message: {j.get('status_message', 'N/A')}")
                print(f"   - tasks_count: {j.get('tasks_count', 'N/A')}")
                print(f"   - tasks_error: {j.get('tasks_error', 'N/A')}")
                
                if 'tasks' in j:
                    print(f"   - tasks数: {len(j['tasks'])}")
                    
                    for i, task_result in enumerate(j['tasks']):
                        print(f"\n   📋 タスク {i}:")
                        print(f"      - 型: {type(task_result)}")
                        print(f"      - キー: {list(task_result.keys()) if isinstance(task_result, dict) else 'N/A'}")
                        print(f"      - status_code: {task_result.get('status_code', 'N/A')}")
                        print(f"      - status_message: {task_result.get('status_message', 'N/A')}")
                        
                        if isinstance(task_result, dict) and 'result' in task_result:
                            print(f"      - result数: {len(task_result['result'])}")
                            
                            for j, res in enumerate(task_result['result']):
                                print(f"\n      📍 結果 {j}:")
                                print(f"         - 型: {type(res)}")
                                print(f"         - キー: {list(res.keys()) if isinstance(res, dict) else 'N/A'}")
                                print(f"         - keyword: {res.get('keyword', 'N/A')}")
                                print(f"         - items_count: {res.get('items_count', 'N/A')}")
                                
                                if isinstance(res, dict) and 'items' in res:
                                    print(f"         - items数: {len(res['items'])}")
                                    
                                    for k, item in enumerate(res['items']):
                                        print(f"\n         🔍 アイテム {k}:")
                                        print(f"            - 型: {type(item)}")
                                        print(f"            - キー: {list(item.keys()) if isinstance(item, dict) else 'N/A'}")
                                        if isinstance(item, dict):
                                            print(f"            - type: {item.get('type', 'N/A')}")
                                            print(f"            - text: {item.get('text', 'N/A')}")
                                            print(f"            - suggestion: {item.get('suggestion', 'N/A')}")
                                            
                                            # Related Searchesの場合の詳細
                                            if item.get('type') == 'related_searches':
                                                print(f"            - itemsキーの存在: {'items' in item}")
                                                if 'items' in item:
                                                    print(f"            - itemsの型: {type(item['items'])}")
                                                    print(f"            - itemsの内容: {item['items']}")
                                            
                                            # People Also Askの場合の詳細
                                            elif item.get('type') == 'people_also_ask':
                                                print(f"            - itemsキーの存在: {'items' in item}")
                                                if 'items' in item:
                                                    print(f"            - itemsの型: {type(item['items'])}")
                                                    print(f"            - itemsの内容: {item['items']}")
                                else:
                                    print(f"         - items: {res}")
                        else:
                            print(f"      - result: {task_result}")
                else:
                    print(f"   - tasks: {j.get('tasks', 'N/A')}")
            
            # レスポンス全体をファイルに保存
            debug_file = "api_response_debug_detailed.json"
            with open(debug_file, 'w', encoding='utf-8') as f:
                json.dump(j, f, ensure_ascii=False, indent=2)
            
            print(f"\n💾 詳細デバッグ情報を {debug_file} に保存しました")
            
        except Exception as e:
            print(f"❌ デバッグエラー: {e}")
            import traceback
            traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(debug_detailed_api_response())
