# src/image_processor.py
import os
import logging
from google.cloud import aiplatform
from vertexai.preview.vision_models import ImageGenerationModel
from pathlib import Path
from typing import List

# ロガーの設定
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

class ImageProcessor:
    """
    Vertex AI (Imagen) を使用して画像生成を専門に行うクラス。
    """
    def __init__(self):
        """
        ImageProcessorを初期化します。
        環境変数から設定を読み込み、Vertex AIクライアントをセットアップします。
        """
        try:
            # 環境変数から設定を読み込み
            project_id = os.getenv("GOOGLE_CLOUD_PROJECT_ID")
            key_path = os.getenv("GOOGLE_APPLICATION_CREDENTIALS", "service_account_key.json")

            if not project_id:
                raise ValueError("環境変数 'GOOGLE_CLOUD_PROJECT_ID' が設定されていません。")

            if not os.path.exists(key_path):
                raise FileNotFoundError(f"認証キーファイルが見つかりません: {key_path}")

            # Vertex AIを初期化 (認証情報はライブラリが自動で環境変数から読み込む)
            os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = key_path
            aiplatform.init(project=project_id, location="asia-northeast1")
            
            # 画像生成モデルをロード
            self.model = ImageGenerationModel.from_pretrained("imagegeneration@006")
            logging.info("[OK] ImageProcessor (Vertex AI) の初期化に成功しました。")

        except Exception as e:
            logging.error(f"[NG] ImageProcessorの初期化中にエラーが発生しました: {e}")
            logging.error("  L .envファイルに 'GOOGLE_CLOUD_PROJECT_ID' が設定されているか確認してください。")
            logging.error("  L 'GOOGLE_APPLICATION_CREDENTIALS' で指定された認証キーファイルが存在するか確認してください。")
            raise

    def generate_images(self, prompt: str, output_base_path: str, number_of_images: int = 1, negative_prompt: str | None = None, aspect_ratio: str = "16:9") -> List[str]:
        """
        Imagen 2 を使用して複数の画像を生成し、指定されたパスに保存する。
        ファイル名には連番が付与される。

        Args:
            prompt (str): 画像生成のためのプロンプト。
            output_base_path (str): 保存する画像のベースパス。例: "output/image.png"
            number_of_images (int): 生成する画像の数。
            negative_prompt (str | None): 生成を避けたい内容を記述するネガティブプロンプト。
            aspect_ratio (str): 生成する画像のアスペクト比。

        Returns:
            List[str]: 生成された画像のパスのリスト。失敗した場合は空のリストを返す。
        """
        generated_image_paths = []
        if number_of_images <= 0:
            return generated_image_paths

        try:
            logging.info(f"  L 画像生成モデル (Imagen) にリクエストを送信中... ({number_of_images}枚)")
            
            generation_args = {
                "prompt": prompt,
                "number_of_images": number_of_images,
                "aspect_ratio": aspect_ratio,
                "add_watermark": False,
            }
            if negative_prompt:
                generation_args["negative_prompt"] = negative_prompt

            response = self.model.generate_images(**generation_args)
            
            base_path = Path(output_base_path)
            output_dir = base_path.parent
            base_filename = base_path.stem
            extension = base_path.suffix or '.png'

            # 出力ディレクトリが存在しない場合は作成
            output_dir.mkdir(parents=True, exist_ok=True)

            for i, image in enumerate(response.images):
                # 複数枚生成する場合、ファイル名が重複しないように連番を付与
                if number_of_images > 1:
                    final_filename = f"{base_filename}_{i+1}{extension}"
                else:
                    final_filename = f"{base_filename}{extension}"
                
                output_path = output_dir / final_filename
                
                # 生成された画像を保存
                image.save(location=str(output_path), include_generation_parameters=True)
                generated_image_paths.append(str(output_path))
                logging.info(f"[OK] 画像をローカルに保存しました: {output_path}")

            return generated_image_paths

        except Exception as e:
            logging.error(f"[NG] 画像生成中にエラーが発生しました: {e}")
            # 呼び出し元でエラーハンドリングができるように、空リストを返すか、例外を再raiseするか選択
            # ここでは空リストを返す仕様を維持
            return []