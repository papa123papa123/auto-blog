# 1. Pythonの公式イメージを土台にする
FROM python:3.11-slim

# ★★★ tkinterをインストールする命令を追加 ★★★
RUN apt-get update && apt-get install -y python3-tk

# 2. コンテナ内での作業ディレクトリを指定
WORKDIR /app

# 3. 必要なライブラリを先にインストール
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 4. プロジェクトのファイルを全部コンテナにコピー
COPY . .

# 5. コンテナが起動した時に実行するコマンド (main.pyを実行)
CMD [ "python", "main.py" ]