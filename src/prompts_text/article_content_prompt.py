# src/prompts_text/article_content_prompt.py
from typing import Dict, List, Any

def create_h3_content_prompt(main_keyword: str, h3_to_write: str, relevant_info: str) -> str:
    """
    指定されたH3見出しの内容を会話形式で生成するプロンプト。
    """
    prompt = f"""
# 指示
「{main_keyword}」について、以下の見出しの内容を会話形式で執筆してください。

## 見出し
{h3_to_write}

## 参考情報
{relevant_info}

## 執筆ルール
- 会話形式：困っている女性客と親切な専門家店員
- 内容：参考情報を基に、分かりやすく説明
- 文字数：300-600文字程度
- 出力：本文のみ（見出し不要）

上記ルールに従って執筆してください。
"""
    return prompt
