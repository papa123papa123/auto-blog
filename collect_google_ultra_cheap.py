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

class UltraCheapGoogleCollector:
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
    
    async def get_autocomplete_with_spread_cursors(self, keyword):
        """離れたカーソルで重複の少ないサジェスト取得"""
        print(f"🚀 メインキーワード「{keyword}」から離れたカーソルでサジェスト取得中...")
        
        # 重複を減らすため、離れたカーソル位置を使用
        spread_cursors = [0, 5, 10, 15, 20, 25]
        print(f"   📍 使用カーソル: {spread_cursors}")
        
        all_suggestions = []
        cursor_results = {}
        
        for cursor in spread_cursors:
            task = {
                "language_code": LANG,
                "location_code": LOC,
                "keyword": keyword,
                "client": "chrome",
                "cursor_pointer": cursor
            }
            
            try:
                r = await self.client.post(
                    f"{BASE}/serp/google/autocomplete/live/advanced",
                    json=[task]
                )
                j = r.json()
                
                suggestions = []
                for t in j.get("tasks", []):
                    for res in t.get("result", []):
                        for item in res.get("items", []):
                            if item.get("type") == "autocomplete":
                                suggestion = item.get("suggestion") or item.get("text") or item.get("value")
                                if suggestion:
                                    suggestions.append(suggestion)
                
                cursor_results[cursor] = suggestions
                all_suggestions.extend(suggestions)
                print(f"  📍 カーソル {cursor}: {len(suggestions)}件取得")
                
                # 短い待機時間
                await asyncio.sleep(0.1)
                
            except Exception as e:
                print(f"    ⚠️ カーソル {cursor} でエラー: {e}")
                cursor_results[cursor] = []
        
        # 重複除去前の統計
        total_before_dedup = len(all_suggestions)
        unique_suggestions = list(dict.fromkeys(all_suggestions))
        total_after_dedup = len(unique_suggestions)
        
        print(f"✅ 離れたカーソル処理完了:")
        print(f"   - 重複除去前: {total_before_dedup}件")
        print(f"   - 重複除去後: {total_after_dedup}件")
        print(f"   - 重複率: {((total_before_dedup - total_after_dedup) / total_before_dedup * 100):.1f}%")
        
        self.all_keywords.update(unique_suggestions)
        return unique_suggestions, cursor_results
    
    async def get_related_searches(self, keyword):
        """Google Related Searchesで追加サジェスト取得"""
        print(f"🔍 Google Related Searchesで追加サジェスト取得中...")
        
        task = {
            "language_code": LANG,
            "location_code": LOC,
            "keyword": keyword,
            "depth": 2
        }
        
        try:
            r = await self.client.post(
                f"{BASE}/serp/google/organic/live/advanced",
                json=[task]
            )
            j = r.json()
            
            related_searches = []
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
                                suggestion = paa_item.get("question")
                                if suggestion:
                                    related_searches.append(suggestion)
            
            # 重複除去
            unique_related = []
            for suggestion in related_searches:
                if suggestion not in self.all_keywords:
                    unique_related.append(suggestion)
                    self.all_keywords.add(suggestion)
            
            print(f"✅ Related Searches完了: {len(unique_related)}件の新規サジェスト")
            return unique_related
            
        except Exception as e:
            print(f"    ⚠️ Related Searches取得エラー: {e}")
            return []
    
    async def run_ultra_cheap_collection(self, seed_keyword, target_count=100):
        """超低コストによるサジェスト収集（1-2回のAPI呼び出し）"""
        print(f"🚀 超低コストGoogleサジェスト収集開始: 「{seed_keyword}」")
        print(f"🎯 目標: {target_count}件")
        print(f"💡 1-2回のAPI呼び出しで効率的に収集")
        
        # 接続確認
        if not await self.check_connection():
            return None
        
        # ステップ1: 離れたカーソルでサジェスト取得（1回目のAPI呼び出し）
        base_suggestions, cursor_results = await self.get_autocomplete_with_spread_cursors(seed_keyword)
        
        print(f"\n📊 ステップ1結果: {len(base_suggestions)}件のベースサジェスト")
        
        # ステップ2: Related Searchesで追加取得（2回目のAPI呼び出し）
        if len(base_suggestions) < target_count:
            print(f"   📈 目標件数に達していないため、Related Searchesで追加取得")
            related_suggestions = await self.get_related_searches(seed_keyword)
        else:
            related_suggestions = []
            print(f"   ✅ 目標件数に到達したため、追加取得は不要")
        
        # 最終結果
        final_keywords = list(self.all_keywords)[:target_count]
        
        # コスト計算
        total_api_calls = 1  # 基本は1回
        if len(related_suggestions) > 0:
            total_api_calls = 2  # Related Searches使用時は2回
        
        estimated_cost = total_api_calls * 0.02  # $0.02/リクエスト
        
        print(f"\n🎉 超低コスト収集完了!")
        print(f"📊 最終結果: {len(final_keywords)}件")
        print(f"   - ベースサジェスト: {len(base_suggestions)}件")
        print(f"   - Related Searches: {len(related_suggestions)}件")
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
                "base_suggestions": base_suggestions,
                "cursor_results": cursor_results,
                "related_suggestions": related_suggestions
            },
            "cost_analysis": {
                "total_api_calls": total_api_calls,
                "estimated_cost_usd": estimated_cost,
                "estimated_cost_jpy": estimated_cost * 150,
                "cost_reduction_percent": (1 - total_api_calls/19)*100
            },
            "breakdown": {
                "base_suggestions": len(base_suggestions),
                "related_suggestions": len(related_suggestions),
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
    
    async with UltraCheapGoogleCollector() as collector:
        result = await collector.run_ultra_cheap_collection(seed_keyword, target_count)
        
        if result:
            # 結果をファイルに保存
            output_file = f"ultra_cheap_{seed_keyword}_{len(result['keywords'])}件.json"
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(result, f, ensure_ascii=False, indent=2)
            
            print(f"\n💾 結果を {output_file} に保存しました")
            
            # 上位30件を表示
            print(f"\n📋 上位30件:")
            for i, kw in enumerate(result['keywords'][:30], 1):
                print(f"  {i:2d}. {kw}")

if __name__ == "__main__":
    asyncio.run(main())
