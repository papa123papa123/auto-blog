import pandas as pd
import os

def import_keyword_planner_csv(file_path):
    """
    GoogleキーワードプランナーのCSVを読み込む。
    """
    if not os.path.exists(file_path):
        print(f"エラー: ファイルが見つかりません: {file_path}")
        return None

    # header=2 は「ファイルの3行目をヘッダーとして使用する」という意味
    header_row = 2 

    settings_to_try = [
        {'encoding': 'utf-16', 'sep': '\t'},
        {'encoding': 'utf-8', 'sep': '\t'},
        {'encoding': 'utf-16', 'sep': ','},
        {'encoding': 'utf-8', 'sep': ','},
        {'encoding': 'cp932', 'sep': ','},
    ]

    for setting in settings_to_try:
        try:
            df = pd.read_csv(file_path, header=header_row, **setting)
            if len(df.columns) > 1 and 'Keyword' in df.columns:
                print(f"★ 読み込み成功！ (エンコーディング: {setting['encoding']}, 区切り文字: {repr(setting['sep'])}, ヘッダー行: {header_row + 1}行目)")
                return df
        except Exception:
            continue

    print("読み込みに失敗しました。ファイルの形式を確認してください。")
    return None

if __name__ == '__main__':
    test_csv_path = 'Keyword Stats 2025-06-12 at 02_29_16.csv'
    print(f"--- Importer単体テスト: {test_csv_path} ---")
    df = import_keyword_planner_csv(test_csv_path)
    if df is not None:
        print("\n--- 読み込み成功データ (先頭5行) ---")
        print(df.head())