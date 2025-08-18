# src/prompts_text/h2_intro_prompt.py
from typing import List

def create_h2_intro_prompt(h2_heading: str, h3_list_for_h2: List[str], summarized_text: str, persona_prompt: str, style_prompt: str) -> str:
    h3_list_text = "\n".join(f"- {h3}" for h3 in h3_list_for_h2)
    prompt = f"""
# 指示
あなたはプロの「WEBライター」として、以下の条件に従って、指定されたH2見出しの直後に挿入する**導入文**を作成してください。

## 1. このセクションの見出し
- **H2見出し:** {h2_heading}
- **このH2で解説するH3見出しリスト:**
{h3_list_text}

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
  - これから何について解説するのか、読者が明確に理解できるように記述してください。
  - 「このセクションでは〜」のような定型的な前置きは絶対に使用しないでください。
  - 読者の興味を引きつけ、続きを読む意欲をかき立てるような文章を心がけてください。
  - 最後に、このセクションで解説する内容の箇条書きリストを加えてください。
- **文字数:** 200文字以上でお願いします。
- **出力:** H2見出し自体は含めず、**導入文と箇条書きリストだけ**を出力してください。

上記全てのルールを厳格に守り、このセクションの導入として完璧な文章を完成させてください。
"""
    return prompt
