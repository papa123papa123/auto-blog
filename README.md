# Auto Blog System - 日本語自動ブログ生成システム

## システム概要
このシステムは、AIとWebスクレイピングを使用して日本語の記事を自動生成するシステムです。

## システム構成

### メインモード
- **モード1**: 統合フロー（キーワード選定から記事生成・投稿まで）
- **モード2**: 手動KW選定（スクショ/コピペからAIが見出し作成）
- **モード3**: キーワード発見・分析（競合度チェック）
- **モード4**: 本文生成（要約テキストを元に記事を作成）
- **モード5**: 記事生成テスト（キーワード入力から記事生成まで）
- **モード6**: 画像投稿テスト（生成済みテキストから画像のみ投稿）
- **モード7**: 高速テストモード（DBを使って生成から投稿まで）
- **モード8**: テスト用（本文収集＆要約フロー）
- **モード9**: 再投稿（ローカルキャッシュから記事と画像を再投稿）
- **モード10**: 連続実行（サジェスト収集 → SEO用コンテンツ抽出）

## 重要なバックアップ情報

### 古いシステムのバックアップ
**⚠️ 注意**: 古いSERP APIシステムは以下の場所にバックアップされています：

```
backup_old_systems/
├── collect_google_suggestions_old_backup.py    # 古いGoogleサジェスト収集システム
├── extract_seo_content_old_backup.py          # 古いSEOコンテンツ抽出システム
└── haru_system_old_backup.py                 # 古いharu_system（SERP API処理含む）
```

### システム変更履歴
- **2025年8月26日**: モード1から古いSERP API処理を削除し、モード10のシステムを使用するように変更
- 古いシステムは`backup_old_systems/`ディレクトリに保存済み

## 使用方法

### 基本実行
```bash
python main.py
```

### 特定モードの実行
```bash
python main.py --mode 1 --yes
```

### 環境変数の設定
`.env`ファイルに以下の設定が必要：
- `GEMINI_API_KEY`: Gemini APIキー
- `SERPAPI_API_KEY`: SERP APIキー
- `GOOGLE_CLOUD_PROJECT_ID`: Google Cloud プロジェクトID

## 依存関係
```bash
pip install -r requirements.txt
```

## ディレクトリ構造
```
auto blog/
├── src/                    # ソースコード
├── config/                 # 設定ファイル
├── prompts/                # プロンプトテンプレート
├── backup_old_systems/     # 古いシステムのバックアップ
├── seo_results/            # SEO結果
├── serp_results/           # SERP結果
└── main.py                 # メインエントリーポイント
```

## トラブルシューティング

### 古いシステムが必要な場合
もし古いSERP APIシステムが必要な場合は、`backup_old_systems/`ディレクトリから該当ファイルを復元してください。

### よくある問題
1. **依存関係エラー**: `pip install -r requirements.txt`を実行
2. **環境変数エラー**: `.env`ファイルの設定を確認
3. **API制限エラー**: APIキーの使用量制限を確認

## 開発者向け情報
- Python 3.11以上が必要
- 仮想環境（venv）の使用を推奨
- コードコメントは日本語で記載

## ライセンス
このプロジェクトは内部使用目的で開発されています。
