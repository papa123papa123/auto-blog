# src/yahoo_competitor_analyzer.py

import asyncio
from pathlib import Path
from src.yahoo_html_collector import YahooHTMLCollector
from src.yahoo_html_analyzer import YahooHTMLAnalyzer
import pandas as pd
from datetime import datetime
import logging

# ロガーの設定
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

class YahooCompetitorAnalyzer:
    def __init__(self, auto_cleanup: bool = True, cleanup_after_hours: int = 1):
        self.html_collector = YahooHTMLCollector(
            auto_cleanup=auto_cleanup, 
            cleanup_after_hours=cleanup_after_hours
        )
        self.html_analyzer = YahooHTMLAnalyzer()
        self.auto_cleanup = auto_cleanup
        
        print("[OK] YahooCompetitorAnalyzerの初期化に成功しました。")
        if self.auto_cleanup:
            print(f"[INFO] HTML自動クリーンアップが有効です（分析完了後{cleanup_after_hours}時間で削除）")
    
    async def run_analysis(self, keywords: list[str]) -> pd.DataFrame:
        """Yahoo検索ベースの競合分析を実行"""
        print(f"\n--- Yahoo検索ベース競合分析を開始 ---")
        print(f"対象キーワード数: {len(keywords)}件")
        
        # 分析前のストレージ情報を表示
        storage_info = self.html_collector.get_storage_info()
        print(f"分析前のストレージ使用状況: {storage_info['file_count']}ファイル, {storage_info['total_size_mb']}MB")
        
        # ステップ1: HTML収集
        print("\n[ステップ 1/3] Yahoo検索からHTML収集中...")
        await self.html_collector.collect_all_keywords_htmls(keywords)
        
        # ステップ2: HTML解析
        print("\n[ステップ 2/3] HTML解析中...")
        results = []
        
        for i, keyword in enumerate(keywords, 1):
            print(f"  [{i}/{len(keywords)}] {keyword} を解析中...")
            keyword_results = self._analyze_keyword(keyword)
            results.append(keyword_results)
        
        # ステップ3: 結果の整理・出力
        print("\n[ステップ 3/3] 結果を整理中...")
        df = pd.DataFrame(results)
        
        # AIM判定によるソート
        df = self._sort_by_aim_judgement(df)
        
        print("--- 競合分析完了 ---")
        
        # 分析完了後のクリーンアップ処理
        if self.auto_cleanup:
            await self._handle_cleanup(keywords)
        
        return df
    
    async def _handle_cleanup(self, keywords: list[str]):
        """分析完了後のクリーンアップ処理"""
        print(f"\n--- HTMLファイルのクリーンアップ処理 ---")
        
        # 即座クリーンアップ（分析完了直後に削除）
        print("分析完了直後の即座クリーンアップを実行中...")
        self.html_collector.cleanup_after_analysis(keywords)
        
        # 遅延クリーンアップもスケジュール（念のため）
        if self.html_collector.cleanup_after_hours > 0:
            print(f"{self.html_collector.cleanup_after_hours}時間後の遅延クリーンアップをスケジュール中...")
            self.html_collector.schedule_cleanup(keywords)
        
        # クリーンアップ後のストレージ情報を表示
        final_storage_info = self.html_collector.get_storage_info()
        print(f"クリーンアップ後のストレージ使用状況: {final_storage_info['file_count']}ファイル, {final_storage_info['total_size_mb']}MB")
        
        if final_storage_info['file_count'] == 0:
            print("[OK] 全てのHTMLファイルが正常に削除されました。")
        else:
            print(f"[INFO] {final_storage_info['file_count']}件のHTMLファイルが残っています。")
    
    def _analyze_keyword(self, keyword: str) -> Dict:
        """単一キーワードの分析"""
        safe_keyword = self.html_collector._make_safe_filename(keyword)
        
        # 各クエリタイプのHTMLファイルパスを取得
        files = self.html_collector.get_collected_files(keyword)
        
        # 各クエリの結果を解析
        allintitle_data = self.html_analyzer.analyze_html_file(files.get('allintitle'))
        intitle_data = self.html_analyzer.analyze_html_file(files.get('intitle'))
        standard_data = self.html_analyzer.analyze_html_file(files.get('standard'))
        
        # 弱いライバルのランクを特定
        weak_ranks = self._identify_weak_competitors(standard_data['top_results'])
        
        # AIM判定
        aim_judgement = self._calculate_aim(
            allintitle_data['total_results'],
            intitle_data['total_results']
        )
        
        # お宝キーワード判定
        treasure_judgement, reason = self._judge_treasure_keyword(
            allintitle_data['total_results'],
            weak_ranks
        )
        
        return {
            'keyword': keyword,
            'allintitle': allintitle_data['total_results'],
            'intitle': intitle_data['total_results'],
            'Q&Aサイト': weak_ranks.get('Q&Aサイト'),
            'SNS': weak_ranks.get('SNS'),
            '無料ブログ': weak_ranks.get('無料ブログ'),
            'AIM判定': aim_judgement,
            'お宝判定': treasure_judgement,
            '判定根拠': reason
        }
    
    def _identify_weak_competitors(self, top_results: List[Dict]) -> Dict:
        """上位結果から弱いライバルのランクを特定"""
        weak_ranks = {'Q&Aサイト': None, 'SNS': None, '無料ブログ': None}
        
        for result in top_results:
            site_type = result.get('site_type')
            if site_type and weak_ranks[site_type] is None:
                weak_ranks[site_type] = result['rank']
        
        return weak_ranks
    
    def _calculate_aim(self, allintitle: int, intitle: int) -> str:
        """AIM判定（既存ロジックと同じ）"""
        if allintitle <= 10 and intitle <= 30000:
            return '[OK]'
        return '[NG]'
    
    def _judge_treasure_keyword(self, allintitle: int, weak_ranks: Dict) -> tuple[str, str]:
        """お宝キーワード判定（既存ロジックと同じ）"""
        # Q&Aサイト、無料ブログ、SNSが1ページ目に表示 = 強力シグナル
        for site_type, rank in weak_ranks.items():
            if rank is not None:
                return "***★★ (お宝候補)", f"{site_type}が{rank}位に存在"
        
        # allintitle判定
        if allintitle <= 10:
            return "***★☆ (参入の価値あり)", f"allintitleが{allintitle}件と非常に少ない"
        if allintitle <= 30:
            return "***☆☆ (要検討)", f"allintitleが{allintitle}件"
        
        return "★☆☆☆☆ (競合多め)", f"明確な弱点シグナルなし"
    
    def _sort_by_aim_judgement(self, df: pd.DataFrame) -> pd.DataFrame:
        """AIM判定と弱いライバル情報でソート"""
        # お宝判定の優先順位を数値化
        treasure_priority = {
            "***★★ (お宝候補)": 1,
            "***★☆ (参入の価値あり)": 2,
            "***☆☆ (要検討)": 3,
            "★☆☆☆☆ (競合多め)": 4
        }
        
        df['お宝優先度'] = df['お宝判定'].map(treasure_priority).fillna(5)
        
        # ソート順序: お宝優先度 → Q&Aサイト → SNS → 無料ブログ
        df_sorted = df.sort_values(
            by=['お宝優先度', 'Q&Aサイト', 'SNS', '無料ブログ'],
            ascending=[True, True, True, True],
            na_position='last'
        )
        
        # 一時的な列を削除
        df_sorted = df_sorted.drop('お宝優先度', axis=1)
        
        return df_sorted
    
    def save_results(self, df: pd.DataFrame, output_dir: str = "analysis_results") -> str:
        """分析結果をExcelファイルに保存"""
        output_path = Path(output_dir)
        output_path.mkdir(exist_ok=True)
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"yahoo_competitor_analysis_{timestamp}.xlsx"
        filepath = output_path / filename
        
        try:
            # Excelファイルに保存
            with pd.ExcelWriter(filepath, engine='openpyxl') as writer:
                df.to_excel(writer, sheet_name='競合分析結果', index=False)
                
                # 統計情報シート
                stats_df = self._create_statistics_sheet(df)
                stats_df.to_excel(writer, sheet_name='統計情報', index=False)
            
            print(f"[OK] 分析結果を保存しました: {filepath}")
            return str(filepath)
            
        except Exception as e:
            print(f"[ERROR] 結果の保存に失敗: {e}")
            return ""
    
    def _create_statistics_sheet(self, df: pd.DataFrame) -> pd.DataFrame:
        """統計情報シート用のデータフレームを作成"""
        stats = []
        
        # 基本統計
        total_keywords = len(df)
        aim_ok_count = len(df[df['AIM判定'] == '[OK]'])
        aim_ng_count = len(df[df['AIM判定'] == '[NG]'])
        
        stats.append({
            '項目': '総キーワード数',
            '値': total_keywords,
            '詳細': ''
        })
        stats.append({
            '項目': 'AIM判定[OK]',
            '値': aim_ok_count,
            '詳細': f"{aim_ok_count/total_keywords*100:.1f}%"
        })
        stats.append({
            '項目': 'AIM判定[NG]',
            '値': aim_ng_count,
            '詳細': f"{aim_ng_count/total_keywords*100:.1f}%"
        })
        
        # お宝キーワード統計
        treasure_counts = df['お宝判定'].value_counts()
        for judgement, count in treasure_counts.items():
            stats.append({
                '項目': f'お宝判定: {judgement}',
                '値': count,
                '詳細': f"{count/total_keywords*100:.1f}%"
            })
        
        # 弱いライバル統計
        weak_site_stats = ['Q&Aサイト', 'SNS', '無料ブログ']
        for site_type in weak_site_stats:
            weak_count = len(df[df[site_type].notna()])
            stats.append({
                '項目': f'{site_type}が上位に存在',
                '値': weak_count,
                '詳細': f"{weak_count/total_keywords*100:.1f}%"
            })
        
        return pd.DataFrame(stats)
    
    def get_analysis_summary(self, df: pd.DataFrame) -> str:
        """分析結果のサマリーを取得"""
        summary = f"=== Yahoo検索ベース競合分析サマリー ===\n"
        summary += f"分析対象キーワード数: {len(df)}件\n"
        summary += f"分析日時: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n"
        
        # AIM判定サマリー
        aim_ok = len(df[df['AIM判定'] == '[OK]'])
        aim_ng = len(df[df['AIM判定'] == '[NG]'])
        summary += f"AIM判定サマリー:\n"
        summary += f"  [OK] (参入推奨): {aim_ok}件 ({aim_ok/len(df)*100:.1f}%)\n"
        summary += f"  [NG] (参入困難): {aim_ng}件 ({aim_ng/len(df)*100:.1f}%)\n\n"
        
        # お宝キーワードサマリー
        treasure_counts = df['お宝判定'].value_counts()
        summary += "お宝キーワード分布:\n"
        for judgement, count in treasure_counts.items():
            summary += f"  {judgement}: {count}件 ({count/len(df)*100:.1f}%)\n"
        
        return summary
    
    def manual_cleanup(self, keywords: list[str] = None):
        """手動でHTMLファイルをクリーンアップ"""
        if keywords:
            print(f"指定されたキーワードのHTMLファイルを手動クリーンアップ中...")
            self.html_collector.cleanup_after_analysis(keywords)
        else:
            print(f"全HTMLファイルを手動クリーンアップ中...")
            self.html_collector.force_cleanup_all()
    
    def get_storage_status(self) -> dict:
        """現在のストレージ状況を取得"""
        return self.html_collector.get_storage_info()

# テスト用コード
if __name__ == "__main__":
    async def test_analyzer():
        # 自動クリーンアップ有効で初期化
        analyzer = YahooCompetitorAnalyzer(auto_cleanup=True, cleanup_after_hours=1)
        
        # テスト用キーワード
        test_keywords = ["日傘 おすすめ", "プログラミングスクール", "ダイエット方法"]
        
        print("テスト分析を開始...")
        results_df = await analyzer.run_analysis(test_keywords)
        
        print("\n分析結果:")
        print(results_df)
        
        print("\nサマリー:")
        summary = analyzer.get_analysis_summary(results_df)
        print(summary)
        
        # 結果を保存
        output_file = analyzer.save_results(results_df)
        if output_file:
            print(f"\n結果を保存しました: {output_file}")
        
        # ストレージ状況を確認
        storage_status = analyzer.get_storage_status()
        print(f"\n最終ストレージ状況: {storage_status}")
    
    asyncio.run(test_analyzer())
