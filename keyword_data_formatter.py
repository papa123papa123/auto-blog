import pandas as pd
from datetime import datetime
from keyword_planner_importer import import_keyword_planner_csv

def find_latest_month_searches_col(columns):
    searches_cols = [col for col in columns if col.startswith('Searches:')]
    if not searches_cols:
        return None
    latest_col = max(searches_cols, key=lambda col: datetime.strptime(col.split(': ')[1], '%b %Y'))
    return latest_col

def format_keyword_data(raw_df: pd.DataFrame) -> pd.DataFrame:
    """
    生のDataFrameを整形する。（列選択、データ型変換、ソート）
    """
    df = raw_df.copy()
    latest_searches_col = find_latest_month_searches_col(df.columns)
    column_mapping = {'Keyword': 'keyword', 'Avg. monthly searches': 'avg_monthly_searches'}
    if latest_searches_col:
        column_mapping[latest_searches_col] = 'latest_month_searches'
    
    # 存在する列だけを対象にする
    existing_columns = [col for col in column_mapping.keys() if col in df.columns]
    df = df[existing_columns].rename(columns=column_mapping)
    df.dropna(subset=['keyword'], inplace=True)

    # データ型の変換
    if 'avg_monthly_searches' in df.columns:
        df['avg_monthly_searches'] = df['avg_monthly_searches'].fillna(0).astype(int)
    if 'latest_month_searches' in df.columns:
        df['latest_month_searches'] = df['latest_month_searches'].fillna(0).astype(int)

    # データを、直近月の検索ボリュームが多い順にソートする
    if 'latest_month_searches' in df.columns:
        df.sort_values(by='latest_month_searches', ascending=False, inplace=True)
        
    df.reset_index(drop=True, inplace=True)
    
    print("データの整形が完了しました。")
    return df


if __name__ == '__main__':
    print("--- データ成形モジュール テスト開始 ---")
    test_csv_path = 'Keyword Stats 2025-06-12 at 02_29_16.csv'
    raw_keyword_df = import_keyword_planner_csv(test_csv_path)

    if raw_keyword_df is not None:
        print("\n--- formatterを呼び出します ---")
        formatted_df = format_keyword_data(raw_keyword_df)
        
        print("\n--- ▼ 整形後の最終データ（一部） ---")
        print(formatted_df.head(10))
        formatted_df.info()