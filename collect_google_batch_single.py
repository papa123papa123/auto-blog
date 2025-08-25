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

class BatchSingleGoogleCollector:
    def __init__(self):
        self.client = None
        self.all_keywords = set()
        
    async def __aenter__(self):
        self.client = httpx.AsyncClient(
            auth=(LOGIN, PASSWORD),
            headers={"Content-Type": "application/json"},
            timeout=60
        )
        return self
        
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.client:
            await self.client.aclose()
    
    async def check_connection(self):
        """接続テスト"""
        try:
            r = await self.client.get(f"{BASE}/appendix/user_data", timeout=30)
            j = r.json()
            if j.get("status_code") == 20000:
                print("✅ Data for SEO接続成功")
                return True
            else:
                print(f"❌ 接続失敗: {j.get('status_message')}")
                return False
        except Exception as e:
            print(f"❌ 接続エラー: {e}")
            return False
    
    async def get_batch_suggestions(self, keyword):
        """1回のAPI呼び出しでバッチ処理によりサジェスト取得"""
        print(f"🚀 メインキーワード「{keyword}」からバッチ処理でサジェスト取得中...")
        
        # バッチ処理用のタスク配列
        batch_tasks = []
        
        # 1. Autocompleteタスク（カーソル0-4）
        for cursor in range(5):
            autocomplete_task = {
                "language_code": LANG,
                "location_code": LOC,
                "keyword": keyword,
                "client": "chrome",
                "cursor_pointer": cursor
            }
            batch_tasks.append(autocomplete_task)
        
        # 2. Organic Searchタスク（Related Searches + PAA）
        organic_task = {
            "language_code": LANG,
            "location_code": LOC,
            "keyword": keyword,
            "depth": 2
        }
        batch_tasks.append(organic_task)
        
        print(f"   📍 バッチタスク数: {len(batch_tasks)}個")
        print(f"   📍 内訳: Autocomplete 5件 + Organic Search 1件")
        
        try:
            # バッチ処理で一括実行
            r = await self.client.post(
                f"{BASE}/serp/google/autocomplete/live/advanced",
                json=batch_tasks
            )
            j = r.json()
            
            # 結果の解析
            autocomplete_suggestions = []
            organic_suggestions = []
            
            for i, task_result in enumerate(j.get("tasks", [])):
                if i < 5:  # Autocompleteタスク
                    for res in task_result.get("result", []):
                        for item in res.get("items", []):
                            if item.get("type") == "autocomplete":
                                suggestion = item.get("suggestion") or item.get("text") or item.get("value")
                                if suggestion:
                                    autocomplete_suggestions.append(suggestion)
                else:  # Organic Searchタスク
                    for res in task_result.get("result", []):
                        # Related Searches
                        for item in res.get("items", []):
                            if item.get("type") == "related_searches":
                                for rel_item in item.get("items", []):
                                    suggestion = rel_item.get("text") or rel_item.get("suggestion")
                                    if suggestion:
                                        organic_suggestions.append(suggestion)
                        
                        # People Also Ask
                        for item in res.get("items", []):
                            if item.get("type") == "people_also_ask":
                                for paa_item in item.get("items", []):
                                    suggestion = paa_item.get("question")
                                    if suggestion:
                                        organic_suggestions.append(suggestion)
            
            # 重複除去
            all_suggestions = autocomplete_suggestions + organic_suggestions
            unique_suggestions = list(dict.fromkeys(all_suggestions))
            
            print(f"✅ バッチ処理完了:")
            print(f"   - Autocomplete: {len(autocomplete_suggestions)}件")
            print(f"   - Organic Search: {len(organic_suggestions)}件")
            print(f"   - 重複除去前: {len(all_suggestions)}件")
            print(f"   - 重複除去後: {len(unique_suggestions)}件")
            print(f"   - 重複率: {((len(all_suggestions) - len(unique_suggestions)) / len(all_suggestions) * 100):.1f}%")
            
            self.all_keywords.update(unique_suggestions)
            return unique_suggestions
            
        except Exception as e:
            print(f"    ⚠️ バッチ処理エラー: {e}")
            return []
    
    async def run_batch_single_collection(self, seed_keyword, target_count=100):
        """バッチ処理による1回のAPI呼び出しでサジェスト収集"""
        print(f"🚀 バッチ処理Googleサジェスト収集開始: 「{seed_keyword}」")
        print(f"🎯 目標: {target_count}件")
        print(f"💡 1回のAPI呼び出しでバッチ処理により効率的に収集")
        
        # 接続確認
        if not await self.check_connection():
            return None
        
        # バッチ処理でサジェスト取得（1回のAPI呼び出し）
        all_suggestions = await self.get_batch_suggestions(seed_keyword)
        
        # 最終結果
        final_keywords = list(self.all_keywords)[:target_count]
        
        # コスト計算
        total_api_calls = 1  # バッチ処理で1回のみ
        estimated_cost = total_api_calls * 0.02  # $0.02/リクエスト
        
        print(f"\n🎉 バッチ処理収集完了!")
        print(f"📊 最終結果: {len(final_keywords)}件")
        print(f"   - 総ユニーク数: {len(self.all_keywords)}件")
        print(f"💰 コスト分析:")
        print(f"   - API呼び出し回数: {total_api_calls}回")
        print(f"   - 推定コスト: ${estimated_cost:.2f} (約{estimated_cost*150:.0f}円)")
        print(f"   - 従来方式との比較: 約{(1 - total_api_calls/19)*100:.0f}%のコスト削減")
        
        return {
            "seed": seed_keyword,
            "total_collected": len(final_keywords),
            "keywords": final_keywords,
            "cost_analysis": {
                "total_api_calls": total_api_calls,
                "estimated_cost_usd": estimated_cost,
                "estimated_cost_jpy": estimated_cost * 150,
                "cost_reduction_percent": (1 - total_api_calls/19)*100
            },
            "breakdown": {
                "total_unique": len(self.all_keywords)
            }
        }

async def main():
    """メイン実行関数"""
    if not LOGIN or not PASSWORD:
        print("❌ 環境変数が設定されていません。.envファイルを確認してください。")
        return
    
    # コマンドライン引数からキーワード取得
    import sys
    seed_keyword = sys.argv[1] if len(sys.argv) > 1 else "テスト"
    target_count = int(sys.argv[2]) if len(sys.argv) > 2 else 100
    
    print(f"🌱 シードキーワード: {seed_keyword}")
    print(f"🎯 目標件数: {target_count}件")
    
    async with BatchSingleGoogleCollector() as collector:
        result = await collector.run_batch_single_collection(seed_keyword, target_count)
        
        if result:
            # 結果をファイルに保存
            output_file = f"batch_single_{seed_keyword}_{len(result['keywords'])}件.json"
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(result, f, ensure_ascii=False, indent=2)
            
            print(f"\n💾 結果を {output_file} に保存しました")
            
            # 上位30件を表示
            print(f"\n📋 上位30件:")
            for i, kw in enumerate(result['keywords'][:30], 1):
                print(f"  {i:2d}. {kw}")

if __name__ == "__main__":
    asyncio.run(main())
