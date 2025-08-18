# src/user_input_collector.py
import tkinter as tk
from tkinter import filedialog, simpledialog, messagebox

class UserInputCollector:
    """
    ユーザーからの手動入力を受け付けるためのUI関連の機能を提供するクラス。
    - スクリーンショット（画像ファイル）の選択
    - コピー＆ペーストされたテキストの入力
    """

    def __init__(self):
        self.root = tk.Tk()
        self.root.withdraw()  # メインウィンドウは表示しない

    def get_screenshot_paths(self) -> list[str]:
        """
        ファイル選択ダイアログを開き、ユーザーに1つ以上の画像ファイルを選択させる。
        """
        messagebox.showinfo("スクリーンショット選択", "次に、解析したいスクリーンショットの画像ファイルを1つ以上選択してください。")
        filepaths = filedialog.askopenfilenames(
            title="スクリーンショット画像を選択",
            filetypes=[("Image files", "*.png *.jpg *.jpeg *.gif *.bmp"), ("All files", "*.*")]
        )
        if not filepaths:
            print("画像が選択されませんでした。")
            return []
        
        print(f"{len(filepaths)}個の画像ファイルが選択されました。")
        return list(filepaths)

    def get_pasted_text(self) -> str:
        """
        シンプルなテキスト入力ボックスを開き、ユーザーにテキストを貼り付けさせる。
        """
        messagebox.showinfo("テキスト貼り付け", "次に、参考にするテキストがあれば、以下のボックスに貼り付けてください。\n（不要な場合はキャンセルを押してください）")
        
        # simpledialogはメインウィンドウが必要なので一時的に作成
        text_window = tk.Toplevel(self.root)
        text_window.withdraw()
        
        pasted_text = simpledialog.askstring(
            "テキスト入力", 
            "ここにテキストを貼り付け (Ctrl+V):",
            parent=text_window
        )
        text_window.destroy()

        if not pasted_text:
            print("テキストは入力されませんでした。")
            return ""
            
        print("テキストが入力されました。")
        return pasted_text.strip()

if __name__ == '__main__':
    # テスト用
    collector = UserInputCollector()
    
    # スクリーンショット選択のテスト
    selected_images = collector.get_screenshot_paths()
    if selected_images:
        print("\n選択された画像パス:")
        for path in selected_images:
            print(f"- {path}")

    # テキスト入力のテスト
    user_text = collector.get_pasted_text()
    if user_text:
        print("\n入力されたテキスト:")
        print(user_text)
