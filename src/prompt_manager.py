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
あなたはプロのフォトグラファー兼アートディレクターです。
以下の記事タイトルと見出しリストに基づき、この記事に必要な**全ての画像（アイキャッチ画像1枚と、各H3見出しの画像）**を生成するための、高品質なAIプロンプトを設計してください。

# 記事情報
## 記事タイトル
{title}

## H3見出しリスト
{h3_list_str}

# 絶対遵守のルール
1.  **品質とスタイル:**
    - 全ての画像は「professional photography, photorealistic, extremely detailed, sharp focus, soft natural lighting」を基本スタイルとします。
    - 人物が描かれる場合は、必ず**「a beautiful young Japanese woman (20s-30s) with a gentle smile and a natural, relatable expression」（自然で親しみやすい表情で優しく微笑む、20代～30代の美しい日本人女性）**という要素をプロンプトの中心にしてください。
2.  **プロンプトの内容:**
    - 各プロンプトは、タイトルや見出しの内容を**具体的かつ直接的に表現**してください。
    - 生成AIで直接使える、詳細な**英語のプロンプト**を作成してください。
3.  **出力形式:**
    - **必ず、以下のJSON形式に従って、全てのプロンプトを一つのJSONオブジェクトとして出力してください。**
    - `eyecatch`には記事タイトルを象徴するプロンプトを、`h3_images`には各H3見出しに対応するプロンプトをリストとして格納してください。
    - `h3_images`リストの**要素数と順序**は、提供された「H3見出しリスト」と**完全に一致**させてください。

# 出力JSONフォーマット
```json
{{
  "eyecatch": {{
    "positive_prompt": "（アイキャッチ用のポジティブプロンプト）",
    "negative_prompt": "ugly, scary, creepy, distorted face, unnatural expression, weird eyes, creepy smile, text, watermark, signature, logo"
  }},
  "h3_images": [
    {{
      "h3_title": "（1つ目のH3見出し）",
      "positive_prompt": "（1つ目のH3見出しに対応するポジティブプロンプト）",
      "negative_prompt": "ugly, scary, creepy, distorted face, unnatural expression, weird eyes, creepy smile, text, watermark, signature, logo"
    }}
  ]
}}
```
"""
        return prompt
