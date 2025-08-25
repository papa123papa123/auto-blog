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

class SimpleGoogleCollector:
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
    
    async def get_autocomplete(self, keyword, cursor=0):
        """Googleサジェスト取得"""
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
            print(f"⚠️ サジェスト取得エラー ({keyword}): {e}")
            return []
    
    async def get_serp_data(self, keyword):
        """SERP関連検索・PAA取得"""
        task = {
            "language_code": LANG,
            "location_code": LOC,
            "keyword": keyword,
            "device": "desktop"
        }
        
        try:
            r = await self.client.post(
                f"{BASE}/serp/google/organic/live/advanced",
                json=[task]
            )
            j = r.json()
            
            related = []
            paa = []
            
            for t in j.get("tasks", []):
                for res in t.get("result", []):
                    for item in res.get("items", []):
                        if item.get("type") == "related_searches":
                            for rel_item in item.get("items", []):
                                title = rel_item.get("title") or rel_item.get("keyword")
                                if title:
                                    related.append(title)
                        elif item.get("type") == "people_also_ask":
                            for paa_item in item.get("items", []):
                                question = paa_item.get("title") or paa_item.get("question")
                                if question:
                                    paa.append(question)
            
            return related, paa
            
        except Exception as e:
            print(f"⚠️ SERP取得エラー ({keyword}): {e}")
            return [], []
    
    async def collect_step1_seed_suggestions(self, seed_keyword):
        """ステップ1: シードキーワードのサジェスト取得"""
        print(f"\n🔍 ステップ1: シードキーワード「{seed_keyword}」のサジェスト取得中...")
        
        all_suggestions = []
        cursors = [0, 1, 2]  # 3つのカーソル位置
        
        for i, cursor in enumerate(cursors):
            print(f"  📍 カーソル {cursor} 処理中... ({i+1}/{len(cursors)})")
            suggestions = await self.get_autocomplete(seed_keyword, cursor)
            all_suggestions.extend(suggestions)
            print(f"    → {len(suggestions)}件取得")
            await asyncio.sleep(0.1)  # レート制限対策
        
        # 重複除去
        unique_suggestions = list(dict.fromkeys(all_suggestions))
        self.all_keywords.update(unique_suggestions)
        
        print(f"✅ ステップ1完了: {len(unique_suggestions)}件のユニークサジェスト")
        return unique_suggestions
    
    async def collect_step2_serp_data(self, seed_keyword):
        """ステップ2: SERP関連検索・PAA取得"""
        print(f"\n🔍 ステップ2: SERP関連検索・PAA取得中...")
        
        related, paa = await self.get_serp_data(seed_keyword)
        
        # 重複除去して追加
        new_keywords = []
        for kw in related + paa:
            if kw not in self.all_keywords:
                new_keywords.append(kw)
                self.all_keywords.add(kw)
        
        print(f"✅ ステップ2完了: 関連検索 {len(related)}件, PAA {len(paa)}件")
        print(f"   新規追加: {len(new_keywords)}件")
        
        return related, paa
    
    async def collect_step3_expanded_suggestions(self, keywords, max_per_keyword=3):
        """ステップ3: 拡張サジェスト取得"""
        print(f"\n🔍 ステップ3: 拡張サジェスト取得中... ({len(keywords)}件のキーワードから)")
        
        new_suggestions = []
        processed = 0
        
        for i, keyword in enumerate(keywords[:50]):  # 上位50件のみ処理
            if len(new_suggestions) >= 100:  # 100件で停止
                break
                
            print(f"  📍 処理中: {keyword} ({i+1}/{min(len(keywords), 50)})")
            
            # 各キーワードから最大3件のサジェスト取得
            suggestions = await self.get_autocomplete(keyword, 0)
            suggestions = suggestions[:max_per_keyword]
            
            # 新規キーワードのみ追加
            for suggestion in suggestions:
                if suggestion not in self.all_keywords:
                    new_suggestions.append(suggestion)
                    self.all_keywords.add(suggestion)
                    
                    if len(new_suggestions) >= 100:
                        break
            
            processed += 1
            await asyncio.sleep(0.1)  # レート制限対策
        
        print(f"✅ ステップ3完了: {len(new_suggestions)}件の新規サジェスト")
        return new_suggestions
    
    async def run_collection(self, seed_keyword, target_count=100):
        """メイン収集処理"""
        print(f"🚀 Googleサジェスト収集開始: 「{seed_keyword}」")
        print(f"🎯 目標: {target_count}件")
        
        # 接続確認
        if not await self.check_connection():
            return None
        
        # ステップ1: シードサジェスト
        seed_suggestions = await self.collect_step1_seed_suggestions(seed_keyword)
        
        # ステップ2: SERPデータ
        related, paa = await self.collect_step2_serp_data(seed_keyword)
        
        # ステップ3: 拡張サジェスト
        if len(self.all_keywords) < target_count:
            # シードサジェスト + 関連検索 + PAA から拡張
            base_keywords = seed_suggestions + related + paa
            expanded = await self.collect_step3_expanded_suggestions(base_keywords)
        else:
            expanded = []
        
        # 最終結果
        final_keywords = list(self.all_keywords)[:target_count]
        
        print(f"\n🎉 収集完了!")
        print(f"📊 最終結果: {len(final_keywords)}件")
        print(f"   - シードサジェスト: {len(seed_suggestions)}件")
        print(f"   - SERP関連: {len(related) + len(paa)}件")
        print(f"   - 拡張サジェスト: {len(expanded)}件")
        
        return {
            "seed": seed_keyword,
            "total_collected": len(final_keywords),
            "keywords": final_keywords,
            "breakdown": {
                "seed_suggestions": len(seed_suggestions),
                "serp_related": len(related),
                "serp_paa": len(paa),
                "expanded": len(expanded)
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
    
    async with SimpleGoogleCollector() as collector:
        result = await collector.run_collection(seed_keyword, target_count)
        
        if result:
            # 結果をファイルに保存
            output_file = f"collected_keywords_{seed_keyword}_{len(result['keywords'])}件.json"
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(result, f, ensure_ascii=False, indent=2)
            
            print(f"\n💾 結果を {output_file} に保存しました")
            
            # 上位20件を表示
            print(f"\n📋 上位20件:")
            for i, kw in enumerate(result['keywords'][:20], 1):
                print(f"  {i:2d}. {kw}")

if __name__ == "__main__":
    asyncio.run(main())
