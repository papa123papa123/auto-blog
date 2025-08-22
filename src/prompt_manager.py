# src/prompt_manager.py

from src.prompts_text.article_outline_prompt import create_article_outline_prompt
from src.prompts_text.article_style_prompt import ARTICLE_STYLE_PROMPT
from src.prompts_text.article_content_prompt import create_h3_content_prompt
from src.prompts_text.article_intro_prompt import create_intro_prompt
from src.prompts_text.h2_intro_prompt import create_h2_intro_prompt
from src.prompts_text.h3_correction_prompt import create_h3_correction_prompt
from src.prompts_text.persona_prompt import PERSONA_PROMPT
from src.prompts_text.summarization_prompt import create_summarization_prompt_text
from typing import List, Dict, Any

class PromptManager:
    def __init__(self):
        print("[OK] PromptManagerの初期化に成功しました。（品質向上・会話形式対応版）")

    def create_summarization_prompt(self, main_keyword: str, text_to_summarize: str) -> str:
        """抽出したテキストから構造化されたJSONデータを生成させるためのプロンプト"""
        return create_summarization_prompt_text(main_keyword, text_to_summarize)

    def create_outline_prompt(self, main_keyword: str, sub_keywords: list[str]) -> str:
        """構成案を作成させるためのプロンプト"""
        return create_article_outline_prompt(main_keyword, sub_keywords)

    def create_h3_correction_prompt(self, main_keyword: str, forbidden_words: List[str], incorrect_h3s: List[str]) -> str:
        """H3見出しのルール違反を修正させるためのプロンプト"""
        return create_h3_correction_prompt(main_keyword, forbidden_words, incorrect_h3s)

    def create_intro_prompt(self, main_keyword: str, sub_keywords: List[str], title: str, summarized_text: str) -> str:
        """記事の導入部分（イントロダクション）を生成させるためのプロンプト"""
        return create_intro_prompt(
            main_keyword=main_keyword,
            h3_headings=sub_keywords,
            title=title,
            summarized_text=summarized_text,
            persona_prompt=PERSONA_PROMPT,
            style_prompt=ARTICLE_STYLE_PROMPT
        )

    def create_h2_intro_prompt(self, h2_heading: str, all_headings: List[str], current_index: int, summarized_text: str) -> str:
        """H2見出しの直後の導入文を生成させるためのプロンプト"""
        h3_list_for_h2 = []
        for i in range(current_index + 1, len(all_headings)):
            if all_headings[i].startswith('### '):
                h3_list_for_h2.append(all_headings[i].replace('### ', ''))
            elif all_headings[i].startswith('## '):
                break
        
        return create_h2_intro_prompt(
            h2_heading=h2_heading,
            h3_list_for_h2=h3_list_for_h2,
            summarized_text=summarized_text,
            persona_prompt=PERSONA_PROMPT,
            style_prompt=ARTICLE_STYLE_PROMPT
        )

    def create_content_prompt_for_section(self, main_keyword: str, current_h3: str, relevant_info: str) -> str:
        """【改善版】単一のH3本文を作成させるためのプロンプト"""
        return create_h3_content_prompt(
            main_keyword=main_keyword,
            h3_to_write=current_h3,
            relevant_info=relevant_info
        )

    def create_all_image_prompts_prompt(self, title: str, outline: List[Dict[str, Any]]) -> str:
        """記事構成案全体から、必要な全ての画像プロンプトを一度に生成させるためのプロンプト"""
        h3_list_str = ""
        for h2_section in outline:
            for h3 in h2_section.get('h3', []):
                h3_list_str += f"- {h3}\n"

        prompt = f"""
# 指示
記事タイトルと見出しに基づいて、画像生成用のAIプロンプトを作成してください。

## 記事情報
- タイトル: {title}
- H3見出し: {h3_list_str}

## 作成ルール
- アイキャッチ画像1枚と各H3見出しの画像用プロンプト
- 各プロンプトは具体的で分かりやすい内容
- 人物が含まれる場合は自然で親しみやすい表情

## 出力形式
JSON形式で以下の構造で出力してください：
```json
{{
  "eyecatch": {{
    "positive_prompt": "アイキャッチ用プロンプト",
    "negative_prompt": "ugly, scary, text, watermark"
  }},
  "h3_images": [
    {{
      "h3_title": "見出し名",
      "positive_prompt": "画像用プロンプト",
      "negative_prompt": "ugly, scary, text, watermark"
    }}
  ]
}}
```
"""
        return prompt
