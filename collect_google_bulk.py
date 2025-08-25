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

class BulkGoogleCollector:
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
    
    async def get_bulk_autocomplete(self, keyword, limit=100):
        """Googleサジェストを一括大量取得"""
        print(f"🔍 メインキーワード「{keyword}」から一括で{limit}件取得を試行...")
        
        # 一括取得を試行
        task = {
            "language_code": LANG,
            "location_code": LOC,
            "keyword": keyword,
            "client": "chrome",
            "cursor_pointer": 0,
            "limit": limit  # 一度に大量取得
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
            
            print(f"✅ 一括取得結果: {len(suggestions)}件")
            return suggestions
            
        except Exception as e:
            print(f"⚠️ 一括取得エラー: {e}")
            return []
    
    async def get_fallback_autocomplete(self, keyword, max_cursors=5):
        """フォールバック: 複数カーソルで取得"""
        print(f"🔄 フォールバック: 複数カーソルで取得中...")
        
        all_suggestions = []
        cursors = list(range(max_cursors))
        
        for i, cursor in enumerate(cursors):
            print(f"  📍 カーソル {cursor} 処理中... ({i+1}/{len(cursors)})")
            
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
                
                all_suggestions.extend(suggestions)
                print(f"    → {len(suggestions)}件取得")
                await asyncio.sleep(0.05)
                
            except Exception as e:
                print(f"    ⚠️ カーソル {cursor} でエラー: {e}")
                continue
        
        # 重複除去
        unique_suggestions = list(dict.fromkeys(all_suggestions))
        print(f"✅ フォールバック取得完了: {len(unique_suggestions)}件")
        return unique_suggestions
    
    async def run_bulk_collection(self, seed_keyword, target_count=100):
        """一括サジェスト収集"""
        print(f"🚀 一括Googleサジェスト収集開始: 「{seed_keyword}」")
        print(f"🎯 目標: {target_count}件")
        print(f"💡 一括取得を試行し、必要に応じてフォールバック")
        
        # 接続確認
        if not await self.check_connection():
            return None
        
        # まず一括取得を試行
        suggestions = await self.get_bulk_autocomplete(seed_keyword, limit=target_count)
        
        # 一括取得で十分でない場合は、フォールバック
        if len(suggestions) < target_count:
            print(f"\n📈 一括取得では不十分です。フォールバック処理を実行...")
            fallback_suggestions = await self.get_fallback_autocomplete(seed_keyword)
            
            # 両方の結果を統合
            all_suggestions = list(set(suggestions + fallback_suggestions))
        else:
            all_suggestions = suggestions
        
        # 最終結果
        final_keywords = all_suggestions[:target_count]
        self.all_keywords.update(final_keywords)
        
        print(f"\n🎉 収集完了!")
        print(f"📊 最終結果: {len(final_keywords)}件")
        print(f"   - 一括取得: {len(suggestions)}件")
        print(f"   - フォールバック: {len(all_suggestions) - len(suggestions)}件")
        
        return {
            "seed": seed_keyword,
            "total_collected": len(final_keywords),
            "keywords": final_keywords,
            "raw_data": {
                "bulk_suggestions": suggestions,
                "fallback_suggestions": all_suggestions[len(suggestions):] if len(suggestions) < len(all_suggestions) else []
            },
            "breakdown": {
                "bulk_suggestions": len(suggestions),
                "fallback_suggestions": len(all_suggestions) - len(suggestions),
                "total_unique": len(all_suggestions)
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
    
    async with BulkGoogleCollector() as collector:
        result = await collector.run_bulk_collection(seed_keyword, target_count)
        
        if result:
            # 結果をファイルに保存
            output_file = f"bulk_collected_{seed_keyword}_{len(result['keywords'])}件.json"
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(result, f, ensure_ascii=False, indent=2)
            
            print(f"\n💾 結果を {output_file} に保存しました")
            
            # 上位30件を表示
            print(f"\n📋 上位30件:")
            for i, kw in enumerate(result['keywords'][:30], 1):
                print(f"  {i:2d}. {kw}")

if __name__ == "__main__":
    asyncio.run(main())
