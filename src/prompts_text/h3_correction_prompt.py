# src/prompts_text/h3_correction_prompt.py
# 注意: このファイルは1ターン生成システムでは使用されません
# 後方互換性のために残しています

from typing import List

def create_h3_correction_prompt(main_keyword: str, forbidden_words: List[str], incorrect_h3s: List[str]) -> str:
    """
    【非推奨】H3見出しの修正用プロンプト（1ターン生成システムでは使用されません）
    
    新しいシステムでは、最適化されたプロンプトで1ターンで完璧な見出しを生成します。
    このメソッドは後方互換性のために残していますが、使用は推奨されません。
    """
    print("[INFO] H3修正プロンプトは非推奨です。1ターン生成システムを使用してください。")
    
    # 最小限の修正プロンプト（緊急時用）
    forbidden_words_str = "、".join(f"「{word}」" for word in forbidden_words)
    incorrect_h3s_str = "\n".join(f"- {h3}" for h3 in incorrect_h3s)

    prompt = f"""
# 緊急修正用プロンプト（非推奨）
以下のH3見出しを修正してください：

## 禁止ワード（使用厳禁）: {forbidden_words_str}

## 修正が必要な見出し:
{incorrect_h3s_str}

## 修正ルール:
- 禁止ワードを別の表現に置き換える
- 見出しの意図は変えない
- 自然な日本語にする

## 出力:
修正された12個のH3見出しをJSONリストで出力

```json
[
  "修正後のH3見出し1",
  "修正後のH3見出し2",
  ...
  "修正後のH3見出し12"
]
```
"""
    return prompt
