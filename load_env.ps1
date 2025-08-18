# load_env.ps1
# このスクリプトは、スクリプトがあるディレクトリの親ディレクトリにある .env ファイルを読み込みます。

# スクリプト自身のディレクトリパスを取得
$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Definition

# .env ファイルが親ディレクトリにあるので、親ディレクトリのパスを構築
$envFilePath = Join-Path (Get-Item $scriptDir).Parent.FullName ".env"

# .env ファイルが存在するか確認
if (Test-Path $envFilePath) {
    # .env ファイルの内容を1行ずつ読み込む
    Get-Content $envFilePath | ForEach-Object {
        # 各行が "KEY=VALUE" の形式になっているかチェック
        if ($_ -match "^\s*([a-zA-Z_][a-zA-Z0-9_]*)\s*=\s*(.*)\s*$") {
            # キーと値を抽出
            $varName = $matches[1]
            $varValue = $matches[2]

            # 値の周りのクォーテーション（"" や ''）を削除（もしあれば）
            $varValue = $varValue -replace '^"|"$', '' -replace "^'|'$", ''

            # 環境変数として設定
            Set-Item -Path Env:$varName -Value $varValue
        }
    }
} else {
    Write-Warning "`.env` file not found at `$envFilePath`. Please ensure it's in the correct location."
}