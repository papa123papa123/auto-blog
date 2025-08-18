# =================================================================
# Git Push Script for PowerShell (v5 - Encoding Fix)
# =================================================================

# --- 設定項目 ---
# push先のブランチ名（通常は 'main' または 'master'）
$branch_name = "main"
# =================

# 文字化け対策: 出力エンコーディングをUTF-8に設定
$OutputEncoding = [System.Text.Encoding]::UTF8

try {
    # 1. コミットの種類の選択
    Write-Host "コミットの種類を選択してください:" -ForegroundColor Yellow
    Write-Host "1: feat (新機能の追加)"
    Write-Host "2: fix  (バグの修正)"
    Write-Host "3: docs (ドキュメントの変更)"
    Write-Host "4: style(コードスタイルの修正)"
    Write-Host "5: refactor (リファクタリング)"
    Write-Host "6: chore(その他の雑多な変更)"

    $choice = Read-Host "番号を入力してください"
    $commit_type = ""

    if ($choice -eq "1") {
        $commit_type = "feat"
    } elseif ($choice -eq "2") {
        $commit_type = "fix"
    } elseif ($choice -eq "3") {
        $commit_type = "docs"
    } elseif ($choice -eq "4") {
        $commit_type = "style"
    } elseif ($choice -eq "5") {
        $commit_type = "refactor"
    } elseif ($choice -eq "6") {
        $commit_type = "chore"
    } else {
        Write-Host "無効な選択です。スクリプトを終了します。" -ForegroundColor Red
        Read-Host "何かキーを押すと終了します..."
        exit
    }

    # 2. コミットメッセージの入力
    $commit_description = Read-Host "このコミットの具体的な説明を入力してください (例: Suno用のプロンプト生成機能を追加)"
    if ([string]::IsNullOrWhiteSpace($commit_description)) {
        Write-Host "コミットメッセージは必須です。スクリプトを終了します。" -ForegroundColor Red
        Read-Host "何かキーを押すと終了します..."
        exit
    }

    # 3. 日付入りのコミットメッセージを生成
    $date_str = Get-Date -Format "yyyy-MM-dd"
    $commit_message = "$($commit_type): $($date_str) - $($commit_description)"

    # 4. Gitコマンドの実行
    Write-Host "--------------------------------" -ForegroundColor Cyan
    Write-Host "以下のコマンドを実行します..."
    Write-Host "git add ."
    Write-Host "git commit -m `"$($commit_message)`""
    Write-Host "git push origin $($branch_name)"
    Write-Host "--------------------------------" -ForegroundColor Cyan

    # 全ての変更をステージング
    git add .
    Write-Host "✅ ステージング完了" -ForegroundColor Green

    # 日付入りのコミットメッセージでローカルに記録
    git commit -m "$commit_message"
    Write-Host "✅ コミット完了" -ForegroundColor Green

    # GitHubにアップロード
    git push origin $branch_name
    Write-Host "✅ GitHubへのPush完了！" -ForegroundColor Green
}
catch {
    Write-Host "エラーが発生しました: $($_.Exception.Message)" -ForegroundColor Red
    Write-Host "スクリプトの実行を中止しました。"
}
finally {
    Read-Host "何かキーを押すと終了します..."
}
