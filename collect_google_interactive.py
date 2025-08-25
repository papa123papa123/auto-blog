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

class InteractiveGoogleCollector:
    def __init__(self):
        self.client = None
        self.all_keywords = set()
        self.current_step = 0
        self.step_results = {}
        
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
    
    def show_status(self):
        """現在の状況を表示"""
        print(f"\n📊 現在の状況:")
        print(f"   収集済みキーワード: {len(self.all_keywords)}件")
        print(f"   現在のステップ: {self.current_step}")
        
        if self.step_results:
            print(f"   各ステップの結果:")
            for step, result in self.step_results.items():
                if isinstance(result, dict):
                    print(f"     - ステップ{step}: {result.get('count', 0)}件")
                else:
                    print(f"     - ステップ{step}: {len(result) if hasattr(result, '__len__') else 'N/A'}件")
    
    async def step1_seed_suggestions(self, seed_keyword):
        """ステップ1: シードキーワードのサジェスト取得"""
        print(f"\n🔍 ステップ1実行中: シードキーワード「{seed_keyword}」のサジェスト取得...")
        
        all_suggestions = []
        cursors = [0, 1, 2]
        
        for i, cursor in enumerate(cursors):
            print(f"  📍 カーソル {cursor} 処理中... ({i+1}/{len(cursors)})")
            suggestions = await self.get_autocomplete(seed_keyword, cursor)
            all_suggestions.extend(suggestions)
            print(f"    → {len(suggestions)}件取得")
            await asyncio.sleep(0.1)
        
        # 重複除去
        unique_suggestions = list(dict.fromkeys(all_suggestions))
        self.all_keywords.update(unique_suggestions)
        self.step_results[1] = {"count": len(unique_suggestions), "keywords": unique_suggestions}
        
        print(f"✅ ステップ1完了: {len(unique_suggestions)}件のユニークサジェスト")
        return unique_suggestions
    
    async def step2_serp_data(self, seed_keyword):
        """ステップ2: SERP関連検索・PAA取得"""
        print(f"\n🔍 ステップ2実行中: SERP関連検索・PAA取得...")
        
        related, paa = await self.get_serp_data(seed_keyword)
        
        # 重複除去して追加
        new_keywords = []
        for kw in related + paa:
            if kw not in self.all_keywords:
                new_keywords.append(kw)
                self.all_keywords.add(kw)
        
        self.step_results[2] = {
            "related_count": len(related),
            "paa_count": len(paa),
            "new_count": len(new_keywords),
            "related": related,
            "paa": paa
        }
        
        print(f"✅ ステップ2完了: 関連検索 {len(related)}件, PAA {len(paa)}件")
        print(f"   新規追加: {len(new_keywords)}件")
        
        return related, paa
    
    async def step3_expanded_suggestions(self, keywords, max_per_keyword=3):
        """ステップ3: 拡張サジェスト取得"""
        print(f"\n🔍 ステップ3実行中: 拡張サジェスト取得... ({len(keywords)}件のキーワードから)")
        
        new_suggestions = []
        processed = 0
        
        for i, keyword in enumerate(keywords[:50]):
            if len(new_suggestions) >= 100:
                break
                
            print(f"  📍 処理中: {keyword} ({i+1}/{min(len(keywords), 50)})")
            
            suggestions = await self.get_autocomplete(keyword, 0)
            suggestions = suggestions[:max_per_keyword]
            
            for suggestion in suggestions:
                if suggestion not in self.all_keywords:
                    new_suggestions.append(suggestion)
                    self.all_keywords.add(suggestion)
                    
                    if len(new_suggestions) >= 100:
                        break
            
            processed += 1
            await asyncio.sleep(0.1)
        
        self.step_results[3] = {"count": len(new_suggestions), "keywords": new_suggestions}
        print(f"✅ ステップ3完了: {len(new_suggestions)}件の新規サジェスト")
        return new_suggestions
    
    async def interactive_collection(self, seed_keyword):
        """インタラクティブな収集処理"""
        print(f"🚀 インタラクティブGoogleサジェスト収集開始: 「{seed_keyword}」")
        print(f"💡 各ステップの実行後に状況を確認し、次のアクションを決定できます")
        
        # 接続確認
        if not await self.check_connection():
            return None
        
        while True:
            self.show_status()
            
            if self.current_step == 0:
                print(f"\n🎯 次のアクションを選択してください:")
                print(f"   1. ステップ1実行 (シードサジェスト取得)")
                print(f"   2. 現在の状況を詳細表示")
                print(f"   3. 収集終了")
                
                choice = input("選択してください (1-3): ").strip()
                
                if choice == "1":
                    await self.step1_seed_suggestions(seed_keyword)
                    self.current_step = 1
                elif choice == "2":
                    self.show_detailed_status()
                elif choice == "3":
                    break
                else:
                    print("❌ 無効な選択です。1-3の数字を入力してください。")
            
            elif self.current_step == 1:
                print(f"\n🎯 次のアクションを選択してください:")
                print(f"   1. ステップ2実行 (SERP関連検索・PAA取得)")
                print(f"   2. ステップ1の結果を確認")
                print(f"   3. 収集終了")
                
                choice = input("選択してください (1-3): ").strip()
                
                if choice == "1":
                    await self.step2_serp_data(seed_keyword)
                    self.current_step = 2
                elif choice == "2":
                    self.show_step_details(1)
                elif choice == "3":
                    break
                else:
                    print("❌ 無効な選択です。1-3の数字を入力してください。")
            
            elif self.current_step == 2:
                print(f"\n🎯 次のアクションを選択してください:")
                print(f"   1. ステップ3実行 (拡張サジェスト取得)")
                print(f"   2. ステップ2の結果を確認")
                print(f"   3. 収集終了")
                
                choice = input("選択してください (1-3): ").strip()
                
                if choice == "1":
                    base_keywords = self.step_results[1]["keywords"] + self.step_results[2]["related"] + self.step_results[2]["paa"]
                    await self.step3_expanded_suggestions(base_keywords)
                    self.current_step = 3
                elif choice == "2":
                    self.show_step_details(2)
                elif choice == "3":
                    break
                else:
                    print("❌ 無効な選択です。1-3の数字を入力してください。")
            
            elif self.current_step == 3:
                print(f"\n🎯 収集完了! 次のアクションを選択してください:")
                print(f"   1. 最終結果を表示")
                print(f"   2. 結果をファイルに保存")
                print(f"   3. 収集終了")
                
                choice = input("選択してください (1-3): ").strip()
                
                if choice == "1":
                    self.show_final_results()
                elif choice == "2":
                    self.save_results(seed_keyword)
                elif choice == "3":
                    break
                else:
                    print("❌ 無効な選択です。1-3の数字を入力してください。")
        
        print(f"\n👋 収集セッション終了")
    
    def show_detailed_status(self):
        """詳細な状況表示"""
        print(f"\n📋 詳細状況:")
        print(f"   総収集キーワード数: {len(self.all_keywords)}件")
        print(f"   実行済みステップ: {list(self.step_results.keys())}")
        
        if self.all_keywords:
            print(f"   収集済みキーワード (上位10件):")
            for i, kw in enumerate(list(self.all_keywords)[:10], 1):
                print(f"     {i:2d}. {kw}")
    
    def show_step_details(self, step_num):
        """特定ステップの詳細表示"""
        if step_num not in self.step_results:
            print(f"❌ ステップ{step_num}の結果がありません")
            return
        
        result = self.step_results[step_num]
        print(f"\n📋 ステップ{step_num}の詳細結果:")
        
        if step_num == 1:
            print(f"   取得件数: {result['count']}件")
            print(f"   キーワード (上位20件):")
            for i, kw in enumerate(result['keywords'][:20], 1):
                print(f"     {i:2d}. {kw}")
        
        elif step_num == 2:
            print(f"   関連検索: {result['related_count']}件")
            print(f"   PAA: {result['paa_count']}件")
            print(f"   新規追加: {result['new_count']}件")
            
            if result['related']:
                print(f"   関連検索 (上位10件):")
                for i, kw in enumerate(result['related'][:10], 1):
                    print(f"     {i:2d}. {kw}")
        
        elif step_num == 3:
            print(f"   取得件数: {result['count']}件")
            print(f"   キーワード (上位20件):")
            for i, kw in enumerate(result['keywords'][:20], 1):
                print(f"     {i:2d}. {kw}")
    
    def show_final_results(self):
        """最終結果表示"""
        print(f"\n🎉 最終収集結果:")
        print(f"   総収集件数: {len(self.all_keywords)}件")
        
        if self.all_keywords:
            print(f"   収集されたキーワード (上位50件):")
            for i, kw in enumerate(list(self.all_keywords)[:50], 1):
                print(f"     {i:2d}. {kw}")
    
    def save_results(self, seed_keyword):
        """結果をファイルに保存"""
        output_file = f"interactive_collected_{seed_keyword}_{len(self.all_keywords)}件.json"
        
        result_data = {
            "seed": seed_keyword,
            "total_collected": len(self.all_keywords),
            "keywords": list(self.all_keywords),
            "step_results": self.step_results,
            "collection_summary": {
                "step1_seed_suggestions": self.step_results.get(1, {}).get("count", 0),
                "step2_serp_related": self.step_results.get(2, {}).get("related_count", 0),
                "step2_serp_paa": self.step_results.get(2, {}).get("paa_count", 0),
                "step3_expanded": self.step_results.get(3, {}).get("count", 0)
            }
        }
        
        try:
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(result_data, f, ensure_ascii=False, indent=2)
            print(f"💾 結果を {output_file} に保存しました")
        except Exception as e:
            print(f"❌ 保存エラー: {e}")

async def main():
    """メイン実行関数"""
    if not LOGIN or not PASSWORD:
        print("❌ 環境変数が設定されていません。.envファイルを確認してください。")
        return
    
    # コマンドライン引数からキーワード取得
    import sys
    seed_keyword = sys.argv[1] if len(sys.argv) > 1 else "テスト"
    
    print(f"🌱 シードキーワード: {seed_keyword}")
    print(f"💡 インタラクティブモードで実行します")
    
    async with InteractiveGoogleCollector() as collector:
        await collector.interactive_collection(seed_keyword)

if __name__ == "__main__":
    asyncio.run(main())
