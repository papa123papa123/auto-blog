# src/advanced_user_input_collector.py
import sys
from PyQt6.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QLabel, QLineEdit,
    QTextEdit, QPushButton, QScrollArea, QGridLayout, QMessageBox
)
from PyQt6.QtGui import QPixmap, QClipboard
from PyQt6.QtCore import Qt, QBuffer
from PIL import Image
import pyperclip
import io

class AdvancedUserInputCollector(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("AI見出し作成ツール")
        self.setGeometry(100, 100, 800, 600)

        self.main_keyword = ""
        self.suggested_text = ""
        self.image_paths = []
        self.temp_image_count = 0

        self._init_ui()

    def _init_ui(self):
        main_layout = QVBoxLayout(self)

        # 1. メインキーワード入力
        main_layout.addWidget(QLabel("メインキーワード:"))
        self.keyword_input = QLineEdit()
        main_layout.addWidget(self.keyword_input)

        # 2. サジェストキーワード入力
        main_layout.addWidget(QLabel("関連サジェスト（コピー＆ペースト）:"))
        self.suggest_input = QTextEdit()
        self.suggest_input.setPlaceholderText("ここにGoogleサジェストなどを貼り付け...")
        self.suggest_input.setMinimumHeight(200)
        main_layout.addWidget(self.suggest_input)

        # 3. 画像貼り付けエリア
        main_layout.addWidget(QLabel("スクリーンショット（Ctrl+Vで貼り付け）:"))
        self.image_grid_layout = QGridLayout()
        self.image_grid_layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        
        container_widget = QWidget()
        container_widget.setLayout(self.image_grid_layout)

        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setWidget(container_widget)
        scroll_area.setMinimumHeight(200)
        main_layout.addWidget(scroll_area)

        # 4. 完了ボタン
        self.submit_button = QPushButton("完了")
        self.submit_button.clicked.connect(self._on_submit)
        main_layout.addWidget(self.submit_button)

    def keyPressEvent(self, event):
        """ Ctrl+Vが押されたときのイベントハンドラ """
        if event.key() == Qt.Key.Key_V and event.modifiers() == Qt.KeyboardModifier.ControlModifier:
            focused_widget = QApplication.focusWidget()
            if isinstance(focused_widget, (QLineEdit, QTextEdit)):
                # テキスト入力ウィジェットがフォーカスされている場合は、通常の貼り付けを実行
                focused_widget.paste()
            else:
                # それ以外の場合は、画像を貼り付け
                self._paste_image_from_clipboard()

    def _paste_image_from_clipboard(self):
        clipboard = QApplication.clipboard()
        mime_data = clipboard.mimeData()

        if mime_data.hasImage():
            image = clipboard.image()
            if not image.isNull():
                self.temp_image_count += 1
                filepath = f"temp_screenshot_{self.temp_image_count}.png"
                
                # QImageをPillowで扱える形式に変換
                buffer = QBuffer()
                buffer.open(QBuffer.OpenModeFlag.ReadWrite)
                image.save(buffer, "PNG")
                pil_img = Image.open(io.BytesIO(buffer.data()))
                pil_img.save(filepath, "PNG")

                self.image_paths.append(filepath)
                self._add_image_to_grid(filepath)
        else:
            QMessageBox.information(self, "情報", "クリップボードに画像が見つかりませんでした。")

    def _add_image_to_grid(self, filepath):
        pixmap = QPixmap(filepath)
        thumbnail = pixmap.scaled(150, 150, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
        
        image_label = QLabel()
        image_label.setPixmap(thumbnail)
        
        row = len(self.image_paths) - 1
        self.image_grid_layout.addWidget(image_label, row, 0)
        self.image_grid_layout.addWidget(QLabel(filepath), row, 1)

    def _on_submit(self):
        self.main_keyword = self.keyword_input.text().strip()
        self.suggested_text = self.suggest_input.toPlainText().strip()

        if not self.main_keyword:
            QMessageBox.warning(self, "入力エラー", "メインキーワードを入力してください。")
            return

        if not self.suggested_text and not self.image_paths:
            QMessageBox.warning(self, "入力エラー", "サジェストかスクリーンショットを少なくとも1つは入力してください。")
            return
        
        print("データ収集完了:")
        print(f"  メインキーワード: {self.main_keyword}")
        print(f"  サジェストテキスト:\n{self.suggested_text[:200]}...")
        print(f"  画像パス: {self.image_paths}")
        
        self.close()

    def get_user_input(self) -> (str, str, list[str]):
        self.exec()
        return self.main_keyword, self.suggested_text, self.image_paths

def main():
    """ テスト用のメイン関数 """
    app = QApplication(sys.argv)
    collector_ui = AdvancedUserInputCollector()
    collector_ui.show()
    app.exec() # イベントループを開始

    main_kw, suggest_text, img_paths = (
        collector_ui.main_keyword,
        collector_ui.suggested_text,
        collector_ui.image_paths
    )

    if main_kw:
        print("\n--- 収集したデータ ---")
        print(f"メインキーワード: {main_kw}")
        print(f"サジェスト:\n{suggest_text}")
        print(f"画像パス: {img_paths}")
        print("--------------------")

if __name__ == "__main__":
    main()
