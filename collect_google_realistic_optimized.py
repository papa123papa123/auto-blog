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

class RealisticOptimizedGoogleCollector:
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
    
    async def get_autocomplete_batch(self, keyword):
        """Autocompleteをバッチ処理で取得（カーソル0-4）"""
        print(f"🚀 メインキーワード「{keyword}」からAutocomplete取得中...")
        
        # バッチ処理用のタスク配列
        batch_tasks = []
        for cursor in range(5):
            task = {
                "language_code": LANG,
                "location_code": LOC,
                "keyword": keyword,
                "client": "chrome",
                "cursor_pointer": cursor
            }
            batch_tasks.append(task)
        
        print(f"   📍 カーソル0-4の5個をバッチ処理")
        
        try:
            r = await self.client.post(
                f"{BASE}/serp/google/autocomplete/live/advanced",
                json=batch_tasks
            )
            j = r.json()
            
            all_suggestions = []
            cursor_results = {}
            
            for i, task_result in enumerate(j.get("tasks", [])):
                cursor = i
                suggestions = []
                for res in task_result.get("result", []):
                    for item in res.get("items", []):
                        if item.get("type") == "autocomplete":
                            suggestion = item.get("suggestion") or item.get("text") or item.get("value")
                            if suggestion:
                                suggestions.append(suggestion)
                
                cursor_results[cursor] = suggestions
                all_suggestions.extend(suggestions)
                print(f"  📍 カーソル {cursor}: {len(suggestions)}件取得")
            
            # 重複除去
            unique_suggestions = list(dict.fromkeys(all_suggestions))
            
            print(f"✅ Autocomplete完了:")
            print(f"   - 重複除去前: {len(all_suggestions)}件")
            print(f"   - 重複除去後: {len(unique_suggestions)}件")
            print(f"   - 重複率: {((len(all_suggestions) - len(unique_suggestions)) / len(all_suggestions) * 100):.1f}%")
            
            self.all_keywords.update(unique_suggestions)
            return unique_suggestions, cursor_results
            
        except Exception as e:
            print(f"    ⚠️ Autocomplete取得エラー: {e}")
            return [], {}
    
    async def get_organic_search_data(self, keyword):
        """Organic SearchからRelated Searches + PAAを取得"""
        print(f"🔍 Organic SearchからRelated Searches + PAA取得中...")
        
        task = {
            "language_code": LANG,
            "location_code": LOC,
            "keyword": keyword,
            "depth": 2,
            "include_serp_info": True
        }
        
        try:
            r = await self.client.post(
                f"{BASE}/serp/google/organic/live/advanced",
                json=[task]
            )
            j = r.json()
            
            related_searches = []
            paa_questions = []
            
            for t in j.get("tasks", []):
                for res in t.get("result", []):
                    # Related Searches
                    for item in res.get("items", []):
                        if item.get("type") == "related_searches":
                            for rel_item in item.get("items", []):
                                suggestion = rel_item.get("text") or rel_item.get("suggestion")
                                if suggestion:
                                    related_searches.append(suggestion)
                    
                    # People Also Ask
                    for item in res.get("items", []):
                        if item.get("type") == "people_also_ask":
                            for paa_item in item.get("items", []):
                                question = paa_item.get("question")
                                if question:
                                    paa_questions.append(question)
            
            # 重複除去
            unique_related = []
            unique_paa = []
            
            for suggestion in related_searches:
                if suggestion not in self.all_keywords:
                    unique_related.append(suggestion)
                    self.all_keywords.add(suggestion)
            
            for question in paa_questions:
                if question not in self.all_keywords:
                    unique_paa.append(question)
                    self.all_keywords.add(question)
            
            print(f"✅ Organic Search完了:")
            print(f"   - Related Searches: {len(unique_related)}件")
            print(f"   - People Also Ask: {len(unique_paa)}件")
            
            return unique_related, unique_paa
            
        except Exception as e:
            print(f"    ⚠️ Organic Search取得エラー: {e}")
            return [], []
    
    async def run_realistic_optimized_collection(self, seed_keyword, target_count=100):
        """現実的最適化によるサジェスト収集（1-2回のAPI呼び出し）"""
        print(f"🚀 現実的最適化Googleサジェスト収集開始: 「{seed_keyword}」")
        print(f"🎯 目標: {target_count}件")
        print(f"💡 実際のユーザー検索行動に基づく高品質キーワード収集")
        
        # 接続確認
        if not await self.check_connection():
            return None
        
        # ステップ1: Autocompleteをバッチ処理で取得（1回目のAPI呼び出し）
        autocomplete_suggestions, cursor_results = await self.get_autocomplete_batch(seed_keyword)
        
        print(f"\n📊 ステップ1結果: {len(autocomplete_suggestions)}件のAutocomplete")
        
        # ステップ2: Organic Searchで追加取得（2回目のAPI呼び出し）
        if len(autocomplete_suggestions) < target_count:
            print(f"   📈 目標件数に達していないため、Organic Searchで追加取得")
            related_suggestions, paa_questions = await self.get_organic_search_data(seed_keyword)
        else:
            related_suggestions, paa_questions = [], []
            print(f"   ✅ 目標件数に到達したため、追加取得は不要")
        
        # 最終結果
        final_keywords = list(self.all_keywords)[:target_count]
        
        # コスト計算
        total_api_calls = 1  # 基本は1回
        if len(related_suggestions) > 0 or len(paa_questions) > 0:
            total_api_calls = 2  # Organic Search使用時は2回
        
        estimated_cost = total_api_calls * 0.02  # $0.02/リクエスト
        
        print(f"\n🎉 現実的最適化収集完了!")
        print(f"📊 最終結果: {len(final_keywords)}件")
        print(f"   - Autocomplete: {len(autocomplete_suggestions)}件")
        print(f"   - Related Searches: {len(related_suggestions)}件")
        print(f"   - People Also Ask: {len(paa_questions)}件")
        print(f"   - 総ユニーク数: {len(self.all_keywords)}件")
        print(f"💰 コスト分析:")
        print(f"   - API呼び出し回数: {total_api_calls}回")
        print(f"   - 推定コスト: ${estimated_cost:.2f} (約{estimated_cost*150:.0f}円)")
        print(f"   - 従来方式との比較: 約{(1 - total_api_calls/19)*100:.0f}%のコスト削減")
        
        return {
            "seed": seed_keyword,
            "total_collected": len(final_keywords),
            "keywords": final_keywords,
            "raw_data": {
                "autocomplete_suggestions": autocomplete_suggestions,
                "cursor_results": cursor_results,
                "related_suggestions": related_suggestions,
                "paa_questions": paa_questions
            },
            "cost_analysis": {
                "total_api_calls": total_api_calls,
                "estimated_cost_usd": estimated_cost,
                "estimated_cost_jpy": estimated_cost * 150,
                "cost_reduction_percent": (1 - total_api_calls/19)*100
            },
            "breakdown": {
                "autocomplete": len(autocomplete_suggestions),
                "related_searches": len(related_suggestions),
                "people_also_ask": len(paa_questions),
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
    
    async with RealisticOptimizedGoogleCollector() as collector:
        result = await collector.run_realistic_optimized_collection(seed_keyword, target_count)
        
        if result:
            # 結果をファイルに保存
            output_file = f"realistic_optimized_{seed_keyword}_{len(result['keywords'])}件.json"
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(result, f, ensure_ascii=False, indent=2)
            
            print(f"\n💾 結果を {output_file} に保存しました")
            
            # 上位30件を表示
            print(f"\n📋 上位30件:")
            for i, kw in enumerate(result['keywords'][:30], 1):
                print(f"  {i:2d}. {kw}")

if __name__ == "__main__":
    asyncio.run(main())
