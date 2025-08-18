# src/flows/keyword_research_flow.py

import pandas as pd
from src.serp_analyzer import SerpAnalyzer

class KeywordResearchFlow:
    """
    キーワードの競合を分析し、「お宝キーワード」の発見を支援するフロー。
    """

    def __init__(self, serp_analyzer: SerpAnalyzer):
        """
        必要な専門家（SerpAnalyzer）を受け取る。

        Args:
            serp_analyzer (SerpAnalyzer): 検索結果を分析する専門家。
        """
        self.serp_analyzer = serp_analyzer

    def run(self):
        """
        キーワード分析フローを実行する。
        """
        print("\n--- キーワード発見・分析フローを開始します ---")
        print("分析したいキーワードを1行に1つずつ入力してください。")
        print("入力を終えたら、何も入力せずにEnterキーを押してください。")

        keywords = []
        while True:
            # ユーザーからの入力を受け付け
            keyword = input("> ")
            if not keyword:
                break
            keywords.append(keyword)

        if not keywords:
            print("キーワードが入力されませんでした。フローを終了します。")
            return

        print(f"\n{len(keywords)}件のキーワードについて、競合分析を開始します...")

        results_data = []
        # 入力された各キーワードについてループ処理
        for i, keyword in enumerate(keywords, 1):
            print(f"\n[{i}/{len(keywords)}] \"{keyword}\" の分析を開始...")
            
            # SerpAnalyzerを使って、allintitle, intitle, 上位10位の情報を取得
            allintitle, intitle, weak_sites = self.serp_analyzer.analyze_top10_serps(keyword)
            
            # 判定ロジックでお宝キーワードかどうかを評価
            judgement, reason = self._judge_keyword(keyword, allintitle, weak_sites)

            # 分析結果をリストに追加
            results_data.append({
                "キーワード": keyword,
                "判定": judgement,
                "allintitle": allintitle,
                "intitle": intitle,
                "Q&Aサイト": f"Top{weak_sites['Q&Aサイト']}" if weak_sites.get('Q&Aサイト') else 'なし',
                "SNS": f"Top{weak_sites['SNS']}" if weak_sites.get('SNS') else 'なし',
                "無料ブログ": f"Top{weak_sites['無料ブログ']}" if weak_sites.get('無料ブログ') else 'なし',
                "根拠": reason
            })
            print(f"-> 分析完了: {judgement} ({reason})")

        # 全ての分析結果を見やすい表形式で表示
        self._display_results_table(results_data)
        
        print("\n--- キーワード発見・分析フローを完了しました ---")

    def _judge_keyword(self, keyword: str, allintitle: int, weak_sites: dict) -> tuple[str, str]:
        """
        分析結果に基づき、キーワードのポテンシャルを判定する内部メソッド。

        Args:
            keyword (str): 分析対象のキーワード。
            allintitle (int): allintitleの検索結果件数。
            weak_sites (dict): 弱いライバルサイトのランク情報。

        Returns:
            tuple[str, str]: 判定結果の文字列と、その根拠。
        """
        # 「サブキーワード選定法.pdf」のシグナルに基づき判定 
        # Q&Aサイト、無料ブログ、SNSが1ページ目に表示されていれば、それは強力なシグナル 
        for site_type, rank in weak_sites.items():
            if rank is not None:
                return "***★★ (お宝候補)", f"{site_type}が{rank}位に存在"

        # allintitleが10件以下の場合も強力なシグナル 
        if allintitle <= 10:
            return "***★☆ (参入の価値あり)", f"allintitleが{allintitle}件と非常に少ない"
        
        if allintitle <= 30:
             return "***☆☆ (要検討)", f"allintitleが{allintitle}件"

        return "★☆☆☆☆ (競合多め)", f"明確な弱点シグナルなし (allintitle: {allintitle})"

    def _display_results_table(self, results_data: list[dict]):
        """
        分析結果のリストをpandas DataFrameに変換して、見やすく表示する。

        Args:
            results_data (list[dict]): 分析結果の辞書のリスト。
        """
        if not results_data:
            print("分析結果がありません。")
            return
            
        try:
            df = pd.DataFrame(results_data)
            # 表示する列の順番を定義
            columns_order = ["キーワード", "判定", "根拠", "Q&Aサイト", "SNS", "無料ブログ", "allintitle", "intitle"]
            df_display = df[columns_order]
            
            print("\n\n===========================================")
            print("         キーワード競合分析 総合結果")
            print("===========================================")
            # to_string()を使って、ターミナル幅に合わせて全列を表示
            print(df_display.to_string())
            print("===========================================\n")
            
            # 結果をCSVファイルとして保存
            output_filename = "keyword_analysis_results.csv"
            df.to_csv(output_filename, index=False, encoding='utf-8-sig')
            print(f"[OK] 分析結果を {output_filename} に保存しました。")

        except ImportError:
            print("\n[エラー] pandasライブラリが必要です。`pip install pandas` を実行してください。")
        except Exception as e:
            print(f"結果の表示またはCSV保存中にエラーが発生しました: {e}")