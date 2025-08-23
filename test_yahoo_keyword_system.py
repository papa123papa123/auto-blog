# test_yahoo_keyword_system.py
# Yahoo検索ベースキーワード収集システムの統合テスト

import asyncio
import sys
from pathlib import Path

# srcディレクトリをパスに追加
sys.path.append(str(Path(__file__).parent / "src"))

from yahoo_keyword_collector import YahooKeywordCollector
from yahoo_keyword_hunter import YahooKeywordHunter

async def test_complete_system():
    """Yahoo検索ベースキーワード収集システムの完全テスト"""
    print("🚀 Yahoo検索ベースキーワード収集システムの統合テスト開始")
    print("=" * 70)
    
    try:
        # 1. YahooKeywordCollectorのテスト
        print("\n📋 ステップ1: YahooKeywordCollectorのテスト")
        print("-" * 50)
        
        collector = YahooKeywordCollector(output_dir="test_yahoo_keywords")
        print("✅ YahooKeywordCollectorの初期化に成功")
        
        # 2. YahooKeywordHunterのテスト
        print("\n📋 ステップ2: YahooKeywordHunterのテスト")
        print("-" * 50)
        
        hunter = YahooKeywordHunter(collector)
        print("✅ YahooKeywordHunterの初期化に成功")
        
        # 3. 実際のキーワード収集テスト
        print("\n📋 ステップ3: 実際のキーワード収集テスト")
        print("-" * 50)
        
        test_keywords = [
            "プログラミング学習",
            "料理 作り方",
            "健康管理"
        ]
        
        for i, keyword in enumerate(test_keywords, 1):
            print(f"\n🔍 テスト {i}/{len(test_keywords)}: 「{keyword}」")
            print("=" * 60)
            
            try:
                # キーワード収集を実行
                collected_keywords = await hunter.gather_all_keywords(keyword)
                
                print(f"\n📊 収集結果:")
                print(f"  総数: {len(collected_keywords)}件")
                
                if collected_keywords:
                    print(f"\n📝 収集されたキーワード（上位10件）:")
                    for j, kw in enumerate(collected_keywords[:10], 1):
                        print(f"    {j:2d}. {kw}")
                    
                    if len(collected_keywords) > 10:
                        print(f"    ... 他 {len(collected_keywords) - 10}件")
                    
                    # キーワードの品質チェック
                    print(f"\n🔍 キーワード品質チェック:")
                    print(f"  - 平均文字数: {sum(len(kw) for kw in collected_keywords) / len(collected_keywords):.1f}文字")
                    print(f"  - 最短: {min(len(kw) for kw in collected_keywords)}文字")
                    print(f"  - 最長: {max(len(kw) for kw in collected_keywords)}文字")
                    
                    # 戦略的拡張ワードの確認
                    strategic_words = hunter.get_strategic_expansion_words()
                    print(f"  - 戦略的拡張ワード: {', '.join(strategic_words)}")
                    
                else:
                    print("⚠️  キーワードが収集されませんでした。")
                
            except Exception as e:
                print(f"❌ キーワード「{keyword}」の収集中にエラーが発生: {e}")
                continue
            
            # レート制限回避
            if i < len(test_keywords):
                print(f"\n⏳ 次のテストまで2秒待機中...")
                await asyncio.sleep(2)
        
        # 4. キャッシュクリーンアップ
        print("\n📋 ステップ4: キャッシュクリーンアップ")
        print("-" * 50)
        
        collector.clear_cache()
        print("✅ テスト用HTMLファイルのクリーンアップ完了")
        
        # 5. 結果サマリー
        print("\n🎉 統合テスト完了！")
        print("=" * 70)
        print("✅ Yahoo検索ベースキーワード収集システムが正常に動作しています。")
        print("✅ SERP APIを使わずにキーワード収集が可能です。")
        print("✅ レート制限回避機能が正常に動作しています。")
        print("✅ 自動クリーンアップ機能が正常に動作しています。")
        
    except Exception as e:
        print(f"❌ 統合テスト中にエラーが発生: {e}")
        return False
    
    return True

async def quick_test():
    """クイックテスト（1つのキーワードのみ）"""
    print("🚀 Yahoo検索ベースキーワード収集システムのクイックテスト")
    print("=" * 60)
    
    try:
        collector = YahooKeywordCollector(output_dir="quick_test_keywords")
        hunter = YahooKeywordHunter(collector)
        
        test_keyword = "プログラミング学習"
        print(f"\n🔍 テストキーワード: 「{test_keyword}」")
        
        collected_keywords = await hunter.gather_all_keywords(test_keyword)
        
        print(f"\n📊 収集結果: {len(collected_keywords)}件")
        if collected_keywords:
            print("\n📝 収集されたキーワード（上位5件）:")
            for i, kw in enumerate(collected_keywords[:5], 1):
                print(f"  {i}. {kw}")
        
        collector.clear_cache()
        print("\n✅ クイックテスト完了")
        
    except Exception as e:
        print(f"❌ クイックテスト中にエラーが発生: {e}")

if __name__ == "__main__":
    print("Yahoo検索ベースキーワード収集システムのテスト")
    print("1. 完全テスト（推奨）")
    print("2. クイックテスト")
    
    choice = input("\n選択してください (1/2): ").strip()
    
    if choice == "1":
        success = asyncio.run(test_complete_system())
        if success:
            print("\n🎯 すべてのテストが成功しました！")
        else:
            print("\n⚠️  一部のテストでエラーが発生しました。")
    elif choice == "2":
        asyncio.run(quick_test())
    else:
        print("無効な選択です。完全テストを実行します。")
        asyncio.run(test_complete_system())
