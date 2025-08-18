# src/prompts_text/article_intro_prompt.py
from typing import List

def create_intro_prompt(main_keyword: str, h3_headings: List[str], title: str, summarized_text: str, persona_prompt: str, style_prompt: str) -> str:
    h3_list_str = "\n".join(f"- {h3}" for h3 in h3_headings)
    prompt = f"""
# 指示
あなたはプロの「WEBライター」として、以下の条件に従ってブログ記事の**導入文**を作成してください。

## 1. 記事の基本情報
- **記事タイトル:** {title}
- **読者ターゲット:** 「{main_keyword}」で検索しているユーザー
- **記事のスタンス:** 読者が前向きな気持ちになり、商品や情報に興味を持てるように紹介する

## 2. 執筆の元となる参考情報
- 以下のデータベースの情報のみを、正確に使用してください。
```json
{summarized_text}
```

## 3. 本文のルール
- **トーン＆マナー:**
  - {persona_prompt}
  - {style_prompt}
- **内容:**
  - 読者の悩みや疑問に共感し、「この記事を読めば、あなたの知りたいことがすべて分かりますよ」という期待感を抱かせる内容にしてください。
  - これから解説する内容（H3見出しのリスト）を簡潔に紹介し、記事を読むメリットを提示してください。
- **文字数:** 300〜400文字程度でお願いします。
- **出力:** **導入文の本文だけ**を出力してください。タイトルや見出しは不要です。

## 4. これから解説するH3見出しのリスト
{h3_list_str}

上記全てのルールを厳格に守り、読者の心を掴む最高の導入文を完成させてください。
"""
    return prompt
