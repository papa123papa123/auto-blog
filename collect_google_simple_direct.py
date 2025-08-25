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

class DirectGoogleCollector:
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
    
    async def get_autocomplete_batch(self, keyword, cursors=None):
        """Googleサジェストを一括取得"""
        if cursors is None:
            # より多くのカーソル位置でサジェスト取得
            cursors = list(range(10))  # 0-9の10個のカーソル
        
        all_suggestions = []
        
        print(f"🔍 メインキーワード「{keyword}」から{len(cursors)}個のカーソル位置でサジェスト取得中...")
        
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
                
                # 短い間隔で処理（レート制限対策）
                await asyncio.sleep(0.05)
                
            except Exception as e:
                print(f"    ⚠️ カーソル {cursor} でエラー: {e}")
                continue
        
        # 重複除去
        unique_suggestions = list(dict.fromkeys(all_suggestions))
        self.all_keywords.update(unique_suggestions)
        
        print(f"✅ サジェスト取得完了: {len(unique_suggestions)}件のユニークキーワード")
        return unique_suggestions
    
    async def run_direct_collection(self, seed_keyword, target_count=100):
        """直接サジェスト収集（シンプル版）"""
        print(f"🚀 直接Googleサジェスト収集開始: 「{seed_keyword}」")
        print(f"🎯 目標: {target_count}件")
        print(f"💡 メインキーワードから直接大量取得します")
        
        # 接続確認
        if not await self.check_connection():
            return None
        
        # メインキーワードから直接サジェスト取得
        suggestions = await self.get_autocomplete_batch(seed_keyword)
        
        # 目標件数に達していない場合は、より多くのカーソルで再取得
        if len(suggestions) < target_count:
            print(f"\n📈 目標件数に達していません。追加取得を試行...")
            additional_cursors = list(range(10, 20))  # 10-19の追加カーソル
            additional_suggestions = await self.get_autocomplete_batch(seed_keyword, additional_cursors)
            suggestions = list(self.all_keywords)
        
        # 最終結果
        final_keywords = list(self.all_keywords)[:target_count]
        
        print(f"\n🎉 収集完了!")
        print(f"📊 最終結果: {len(final_keywords)}件")
        print(f"   - 直接サジェスト取得: {len(suggestions)}件")
        
        return {
            "seed": seed_keyword,
            "total_collected": len(final_keywords),
            "keywords": final_keywords,
            "raw_data": {
                "direct_suggestions": suggestions
            },
            "breakdown": {
                "direct_suggestions": len(suggestions)
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
    
    async with DirectGoogleCollector() as collector:
        result = await collector.run_direct_collection(seed_keyword, target_count)
        
        if result:
            # 結果をファイルに保存
            output_file = f"direct_collected_{seed_keyword}_{len(result['keywords'])}件.json"
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(result, f, ensure_ascii=False, indent=2)
            
            print(f"\n💾 結果を {output_file} に保存しました")
            
            # 上位30件を表示
            print(f"\n📋 上位30件:")
            for i, kw in enumerate(result['keywords'][:30], 1):
                print(f"  {i:2d}. {kw}")

if __name__ == "__main__":
    asyncio.run(main())
