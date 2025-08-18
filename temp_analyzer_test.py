# temp_analyzer_test.py
import os
from src.haru_system import HaruOrchestrator

def main():
    # テスト対象のCSVファイルのパス
    # ユーザーのデスクトップにあると仮定
    csv_path = "rakkokeyword_202572803543.csv"

    if not os.path.exists(csv_path):
        print(f"エラー: テスト用のCSVファイルが見つかりません。")
        print(f"パス: {csv_path}")
        print("デスクトップに '@rakkokeyword_202572803543.csv' を配置してください。")
        return

    try:
        # HaruOrchestratorを初期化して、KeywordAnalyzerインスタンスを取得
        orchestrator = HaruOrchestrator()
        # KeywordAnalyzerの分析フローを実行
        orchestrator.keyword_analyzer.run_analysis(input_csv_path=csv_path)
    except Exception as e:
        print(f"テスト実行中にエラーが発生しました: {e}")

if __name__ == "__main__":
    main()
