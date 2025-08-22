# Auto Blog - 競合分析システム最適化プロジェクト

## 🎯 プロジェクト概要

このプロジェクトは、SEO競合分析と記事生成を自動化するシステムです。最新の最適化により、APIコストの削減と記事生成成功率の向上を実現しています。

## 🚀 主要機能

### 1. 競合分析システム
- **厳密判定基準**: allintitle ≤ 10件 AND intitle ≤ 30,000件
- **3つの実装版**:
  - 基本版: `run_fast_competitor_research.py`
  - DataForSEO版: `run_dataforseo_competitor_research.py`
  - SerpAPI最適化版: `run_serpapi_optimized_competitor_research.py`

### 2. 記事生成システム
- **簡素化されたプロンプト**: 記事生成成功率向上
- **会話形式**: 親しみやすく分かりやすい内容
- **画像生成**: Vertex AI Imagen対応

## 📁 ファイル構成

```
auto blog/
├── run_fast_competitor_research.py          # 基本版（厳密判定基準付き）
├── run_dataforseo_competitor_research.py   # DataForSEO版
├── run_serpapi_optimized_competitor_research.py # SerpAPI最適化版
├── auto_load_summary.py                     # 会話要約自動読み込み
├── conversation_summary.md                  # 会話要約
├── src/
│   ├── prompt_manager.py                   # プロンプト管理
│   └── prompts_text/                       # プロンプトテキスト
│       ├── persona_prompt.py               # 簡素化済み
│       ├── article_style_prompt.py         # 簡素化済み
│       └── article_content_prompt.py       # 簡素化済み
└── KWラッコエクセル/                        # キーワードデータ
```

## 🚀 クイックスタート

### 1. 環境設定
```bash
# 仮想環境の有効化
.\venv\Scripts\Activate.ps1

# 依存関係のインストール
pip install -r requirements.txt
```

### 2. 環境変数の設定
`.env` ファイルを作成し、以下を設定：
```bash
DATAFORSEO_LOGIN=your_login
DATAFORSEO_PASSWORD=your_password
SERPAPI_API_KEY=your_key
```

### 3. 前回の作業内容確認
```bash
python auto_load_summary.py
```

### 4. 競合分析の実行
```bash
# DataForSEO版（推奨）
python run_dataforseo_competitor_research.py

# または SerpAPI最適化版
python run_serpapi_optimized_competitor_research.py
```

## 💰 コスト比較

| 方式 | キーワード数 | クエリ数 | 料金 | 特徴 |
|------|-------------|----------|------|------|
| **基本版** | 10個 | 30回 | 約30円 | 3クエリ/KW |
| **DataForSEO版** | 10個 | 20回 | 約20円 | 2クエリ/KW、効率化 |
| **SerpAPI最適化** | 10個 | 20回 | 約20円 | 2クエリ/KW、非同期処理 |

## ⚠️ 重要な注意事項

### API料金について
- **バッチ処理 ≠ 料金削減**
- キーワード数 × クエリ数 = 総料金
- バッチ処理は「効率化」であって「料金削減」ではない

### 厳密基準の重要性
- **allintitle ≤ 10件** は絶対条件
- **intitle ≤ 30,000件** も重要
- 両方をクリアするキーワードを探す

## 🔄 作業の継続性

### 自動読み込み機能
次回作業開始時は `python auto_load_summary.py` を実行することで：
- 前回の作業内容を自動確認
- クイックスタートガイドを表示
- 作業の継続性を保証

### 会話要約
`conversation_summary.md` には以下が記録されています：
- 発見された問題点と解決策
- 実装された機能の詳細
- 次のステップの明確化
- 重要な注意事項

## 🎯 次のステップ

1. **厳密基準をクリアするキーワードの特定**
2. **最適化版システムのテスト実行**
3. **記事作成への移行**
4. **Cursorエージェントを活用したAPIコスト削減**

## 📞 サポート

問題が発生した場合は、`conversation_summary.md` と `auto_load_summary.py` を確認してください。

---

**最終更新**: 2025年8月23日  
**バージョン**: 2.0
