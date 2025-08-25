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

class ParallelGoogleCollector:
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
    
    async def get_autocomplete_single(self, keyword, cursor):
        """単一カーソルでサジェスト取得"""
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
            
            return suggestions
            
        except Exception as e:
            print(f"    ⚠️ カーソル {cursor} でエラー: {e}")
            return []
    
    async def get_autocomplete_parallel(self, keyword, cursors):
        """複数カーソルを並列処理でサジェスト取得"""
        print(f"🚀 メインキーワード「{keyword}」から{len(cursors)}個のカーソルを並列処理中...")
        
        # 並列処理で複数カーソルを同時実行
        tasks = [self.get_autocomplete_single(keyword, cursor) for cursor in cursors]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        all_suggestions = []
        for i, result in enumerate(results):
            if isinstance(result, list):
                all_suggestions.extend(result)
                print(f"  📍 カーソル {cursors[i]}: {len(result)}件取得")
            else:
                print(f"  ⚠️ カーソル {cursors[i]}: エラー")
        
        # 重複除去
        unique_suggestions = list(dict.fromkeys(all_suggestions))
        self.all_keywords.update(unique_suggestions)
        
        print(f"✅ 並列処理完了: {len(unique_suggestions)}件のユニークキーワード")
        return unique_suggestions
    
    async def expand_keywords_parallel(self, base_keywords, max_per_keyword=2):
        """ベースキーワードから並列で拡張サジェスト取得"""
        print(f"🔍 ベースキーワード{len(base_keywords)}件から並列で拡張取得中...")
        print(f"   ⚡ 各キーワードから最大{max_per_keyword}件ずつ取得")
        
        # 各ベースキーワードからサジェスト取得を並列実行
        async def expand_single_keyword(kw):
            suggestions = await self.get_autocomplete_single(kw, 0)
            return suggestions[:max_per_keyword]
        
        # 並列実行（同時実行数を制限）
        semaphore = asyncio.Semaphore(5)  # 同時実行数を5に制限
        
        async def limited_expand(kw):
            async with semaphore:
                return await expand_single_keyword(kw)
        
        tasks = [limited_expand(kw) for kw in base_keywords]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        new_suggestions = []
        for i, result in enumerate(results):
            if isinstance(result, list):
                for suggestion in result:
                    if suggestion not in self.all_keywords:
                        new_suggestions.append(suggestion)
                        self.all_keywords.add(suggestion)
                print(f"  📍 {base_keywords[i]}: {len(result)}件取得")
            else:
                print(f"  ⚠️ {base_keywords[i]}: エラー")
        
        print(f"✅ 拡張取得完了: {len(new_suggestions)}件の新規サジェスト")
        return new_suggestions
    
    async def run_parallel_collection(self, seed_keyword, target_count=100):
        """並列処理によるサジェスト収集"""
        print(f"🚀 並列処理Googleサジェスト収集開始: 「{seed_keyword}」")
        print(f"🎯 目標: {target_count}件")
        print(f"💡 並列処理で高速化し、効率的に拡張")
        
        # 接続確認
        if not await self.check_connection():
            return None
        
        # ステップ1: メインキーワードから並列でサジェスト取得
        # 効率的なカーソル位置のみ使用（0-3の4個）
        efficient_cursors = [0, 1, 2, 3]
        base_suggestions = await self.get_autocomplete_parallel(seed_keyword, efficient_cursors)
        
        print(f"\n📊 ステップ1結果: {len(base_suggestions)}件のベースキーワード")
        
        # ステップ2: ベースキーワードから並列で拡張
        if len(base_suggestions) > 0:
            expanded_suggestions = await self.expand_keywords_parallel(base_suggestions, max_per_keyword=3)
        else:
            expanded_suggestions = []
        
        # 最終結果
        final_keywords = list(self.all_keywords)[:target_count]
        
        print(f"\n🎉 並列処理収集完了!")
        print(f"📊 最終結果: {len(final_keywords)}件")
        print(f"   - ベースサジェスト: {len(base_suggestions)}件")
        print(f"   - 拡張サジェスト: {len(expanded_suggestions)}件")
        print(f"   - 総ユニーク数: {len(self.all_keywords)}件")
        
        return {
            "seed": seed_keyword,
            "total_collected": len(final_keywords),
            "keywords": final_keywords,
            "raw_data": {
                "base_suggestions": base_suggestions,
                "expanded_suggestions": expanded_suggestions
            },
            "breakdown": {
                "base_suggestions": len(base_suggestions),
                "expanded_suggestions": len(expanded_suggestions),
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
    
    async with ParallelGoogleCollector() as collector:
        result = await collector.run_parallel_collection(seed_keyword, target_count)
        
        if result:
            # 結果をファイルに保存
            output_file = f"parallel_collected_{seed_keyword}_{len(result['keywords'])}件.json"
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(result, f, ensure_ascii=False, indent=2)
            
            print(f"\n💾 結果を {output_file} に保存しました")
            
            # 上位30件を表示
            print(f"\n📋 上位30件:")
            for i, kw in enumerate(result['keywords'][:30], 1):
                print(f"  {i:2d}. {kw}")

if __name__ == "__main__":
    asyncio.run(main())
