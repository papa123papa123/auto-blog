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

class AgentCollaborationGoogleCollector:
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
    
    async def get_main_keyword_data(self, keyword):
        """メインキーワードからRelated Searches + PAAを取得（1回目のAPI呼び出し）"""
        print(f"🚀 メインキーワード「{keyword}」からRelated Searches + PAA取得中...")
        
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
            all_suggestions = related_searches + paa_questions
            unique_suggestions = list(dict.fromkeys(all_suggestions))
            
            print(f"✅ メインキーワード取得完了:")
            print(f"   - Related Searches: {len(related_searches)}件")
            print(f"   - People Also Ask: {len(paa_questions)}件")
            print(f"   - 総ユニーク数: {len(unique_suggestions)}件")
            
            self.all_keywords.update(unique_suggestions)
            return unique_suggestions
            
        except Exception as e:
            print(f"    ⚠️ メインキーワード取得エラー: {e}")
            return []
    
    def create_agent_analysis_file(self, keywords, main_keyword):
        """エージェント分析用ファイルを作成"""
        filename = f"agent_analysis_{main_keyword.replace(' ', '_')}.txt"
        
        content = f"""=== エージェント分析依頼 ===

メインキーワード: {main_keyword}

以下のキーワードから、SEO上有用な上位5個を選定してください。

選定基準：
- メインキーワードと関連性がある
- 検索される可能性がある
- コンテンツ作成に使えそう
- 季節性・トレンド性が高い

キーワード一覧（{len(keywords)}件）：
{chr(10).join(f"{i+1:2d}. {kw}" for i, kw in enumerate(keywords))}

=== 分析結果 ===
選定された上位5個：
1. 
2. 
3. 
4. 
5. 

選定理由：
"""
        
        with open(filename, 'w', encoding='utf-8') as f:
            f.write(content)
        
        print(f"\n📋 エージェント分析用ファイルを作成しました: {filename}")
        print("🤖 エージェントにこのファイルを送信して分析してください")
        print("📝 分析結果を入力してEnterを押してください")
        
        return filename
    
    def get_agent_selection(self, filename):
        """エージェントの選定結果を取得"""
        print(f"\n📥 エージェントの選定結果を入力してください")
        print("📋 ファイル {filename} の分析結果を参考にしてください")
        
        selected_keywords = []
        for i in range(5):
            while True:
                try:
                    kw = input(f"選定キーワード {i+1}: ").strip()
                    if kw:
                        selected_keywords.append(kw)
                        break
                    else:
                        print("⚠️ キーワードを入力してください")
                except KeyboardInterrupt:
                    print("\n❌ 入力をキャンセルしました")
                    return []
        
        print(f"✅ エージェント選定完了: {len(selected_keywords)}件")
        for i, kw in enumerate(selected_keywords, 1):
            print(f"  {i}. {kw}")
        
        return selected_keywords
    
    async def get_selected_keywords_data(self, selected_keywords):
        """選定されたキーワードからRelated Searches + PAAを取得（2回目のAPI呼び出し）"""
        print(f"\n🔍 選定されたキーワード{len(selected_keywords)}件からRelated Searches + PAA取得中...")
        
        # バッチ処理用のタスク配列
        batch_tasks = []
        for keyword in selected_keywords:
            task = {
                "language_code": LANG,
                "location_code": LOC,
                "keyword": keyword,
                "depth": 2,
                "include_serp_info": True
            }
            batch_tasks.append(task)
        
        print(f"   📍 {len(selected_keywords)}個のキーワードをバッチ処理")
        
        try:
            r = await self.client.post(
                f"{BASE}/serp/google/organic/live/advanced",
                json=batch_tasks
            )
            j = r.json()
            
            all_new_suggestions = []
            keyword_results = {}
            
            for i, task_result in enumerate(j.get("tasks", [])):
                keyword = selected_keywords[i]
                related_searches = []
                paa_questions = []
                
                for res in task_result.get("result", []):
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
                
                keyword_results[keyword] = {
                    "related_searches": related_searches,
                    "paa_questions": paa_questions
                }
                
                all_new_suggestions.extend(related_searches + paa_questions)
                print(f"  📍 {keyword}: Related {len(related_searches)}件, PAA {len(paa_questions)}件")
            
            # 重複除去
            unique_new_suggestions = []
            for suggestion in all_new_suggestions:
                if suggestion not in self.all_keywords:
                    unique_new_suggestions.append(suggestion)
                    self.all_keywords.add(suggestion)
            
            print(f"✅ 選定キーワード取得完了: {len(unique_new_suggestions)}件の新規サジェスト")
            return unique_new_suggestions, keyword_results
            
        except Exception as e:
            print(f"    ⚠️ 選定キーワード取得エラー: {e}")
            return [], {}
    
    async def run_agent_collaboration_collection(self, seed_keyword, target_count=100):
        """エージェント連携によるサジェスト収集（2回のAPI呼び出し）"""
        print(f"🚀 エージェント連携Googleサジェスト収集開始: 「{seed_keyword}」")
        print(f"🎯 目標: {target_count}件")
        print(f"💡 エージェントと連携して効率的に収集")
        
        # 接続確認
        if not await self.check_connection():
            return None
        
        # ステップ1: メインキーワードからRelated Searches + PAA取得（1回目のAPI呼び出し）
        main_suggestions = await self.get_main_keyword_data(seed_keyword)
        
        if len(main_suggestions) == 0:
            print("❌ メインキーワードからサジェストが取得できませんでした")
            return None
        
        print(f"\n📊 ステップ1結果: {len(main_suggestions)}件のサジェスト")
        
        # ステップ2: エージェント分析用ファイル作成
        analysis_file = self.create_agent_analysis_file(main_suggestions, seed_keyword)
        
        # ステップ3: エージェントの選定結果を取得
        selected_keywords = self.get_agent_selection(analysis_file)
        
        if len(selected_keywords) == 0:
            print("❌ エージェントの選定が完了しませんでした")
            return None
        
        # ステップ4: 選定されたキーワードから追加取得（2回目のAPI呼び出し）
        expanded_suggestions, keyword_results = await self.get_selected_keywords_data(selected_keywords)
        
        # 最終結果
        final_keywords = list(self.all_keywords)[:target_count]
        
        # コスト計算
        total_api_calls = 2  # 1回目 + 2回目
        estimated_cost = total_api_calls * 0.02  # $0.02/リクエスト
        
        print(f"\n🎉 エージェント連携収集完了!")
        print(f"📊 最終結果: {len(final_keywords)}件")
        print(f"   - メインサジェスト: {len(main_suggestions)}件")
        print(f"   - エージェント選定: {len(selected_keywords)}件")
        print(f"   - 拡張サジェスト: {len(expanded_suggestions)}件")
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
                "main_suggestions": main_suggestions,
                "selected_keywords": selected_keywords,
                "expanded_suggestions": expanded_suggestions,
                "keyword_results": keyword_results
            },
            "cost_analysis": {
                "total_api_calls": total_api_calls,
                "estimated_cost_usd": estimated_cost,
                "estimated_cost_jpy": estimated_cost * 150,
                "cost_reduction_percent": (1 - total_api_calls/19)*100
            },
            "breakdown": {
                "main_suggestions": len(main_suggestions),
                "selected_keywords": len(selected_keywords),
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
    seed_keyword = sys.argv[1] if len(sys.argv) > 1 else "夏 おすすめ お酒"
    target_count = int(sys.argv[2]) if len(sys.argv) > 2 else 100
    
    print(f"🌱 シードキーワード: {seed_keyword}")
    print(f"🎯 目標件数: {target_count}件")
    
    async with AgentCollaborationGoogleCollector() as collector:
        result = await collector.run_agent_collaboration_collection(seed_keyword, target_count)
        
        if result:
            # 結果をファイルに保存
            output_file = f"agent_collaboration_{seed_keyword.replace(' ', '_')}_{len(result['keywords'])}件.json"
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(result, f, ensure_ascii=False, indent=2)
            
            print(f"\n💾 結果を {output_file} に保存しました")
            
            # 上位30件を表示
            print(f"\n📋 上位30件:")
            for i, kw in enumerate(result['keywords'][:30], 1):
                print(f"  {i:2d}. {kw}")

if __name__ == "__main__":
    asyncio.run(main())
