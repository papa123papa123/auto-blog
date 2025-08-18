# src/flows/article_creation_flow.py

import os
import json
from src.gemini_generator import GeminiGenerator
from src.keyword_suggester import KeywordSuggester
from src.serp_analyzer import SerpAnalyzer
from src.sub_keyword_selector import SubKeywordSelector
from src.prompts_text.article_outline_prompt import create_article_outline_prompt
from src.prompts_text.article_content_prompt import create_lead_prompt, create_h3_content_prompt, create_summary_prompt
from src.prompt_manager import PromptManager

class ArticleCreationFlow:
    """
    キーワード収集から記事生成まで、一連のフローを管理するクラス。
    """
    def __init__(self, gemini_generator: GeminiGenerator, keyword_suggester: KeywordSuggester, 
                 serp_analyzer: SerpAnalyzer, sub_keyword_selector: SubKeywordSelector,
                 prompt_manager: PromptManager):
        self.gemini_generator = gemini_generator
        self.keyword_suggester = keyword_suggester
        self.serp_analyzer = serp_analyzer
        self.sub_keyword_selector = sub_keyword_selector
        self.prompt_manager = prompt_manager

    def run(self):
        """
        記事作成のパイプラインを実行する。
        """
        print("\n--- 全自動記事生成パイプラインを開始します ---")

        # 1. メインキーワードの入力
        main_keyword = input("1. 記事のメインキーワードを入力してください: ")
        if not main_keyword:
            print("キーワードが入力されなかったため、処理を終了します。")
            return

        # 2. キーワード収集
        print("\n--- ステップ2: キーワード収集 ---")
        suggest_keywords = self.keyword_suggester.get_suggest_keywords(main_keyword)
        related_questions = self.serp_analyzer.get_related_questions(main_keyword)
        related_searches = self.serp_analyzer.get_related_searches(main_keyword)
        all_collected_keywords = list(set(suggest_keywords + related_questions + related_searches))
        print(f"収集したユニークキーワード数: {len(all_collected_keywords)}個")

        # 3. サブキーワード選定
        print("\n--- ステップ3: サブキーワード選定 ---")
        final_sub_keywords = self.sub_keyword_selector.select_sub_keywords(main_keyword, all_collected_keywords)
        if not final_sub_keywords:
            print("サブキーワードの選定に失敗しました。処理を終了します。")
            return

        # 4. 記事構成案の生成
        print("\n--- ステップ4: 記事構成案の生成 ---")
        outline_prompt = create_article_outline_prompt(main_keyword, final_sub_keywords)
        outline_response = self.gemini_generator.generate(outline_prompt)
        try:
            json_str = outline_response.split("```json")[1].split("```")[0].strip()
            outline_data = json.loads(json_str)
            print("構成案が正常に生成されました。")
            print(f"  - タイトル: {outline_data['title']}")
        except (json.JSONDecodeError, IndexError) as e:
            print(f"構成案のJSON解析に失敗しました: {e}")
            print(f"応答テキスト:\n{outline_response}")
            return
            
        # 5. 記事本文の生成
        print("\n--- ステップ5: 記事本文の生成 ---")
        
        # 5-1. ペルソナと文体の取得
        persona_prompt = self.prompt_manager.get_persona_prompt()
        style_prompt = self.prompt_manager.get_style_prompt()

        # 5-2. リード文の生成
        print("  - リード文を生成中...")
        lead_prompt = create_lead_prompt(main_keyword, outline_data['title'], outline_data['meta_description'], outline_data['outline'])
        lead_content = self.gemini_generator.generate(lead_prompt)

        # 5-3. H3ごとの本文生成
        article_body = ""
        for section in outline_data['outline']:
            h2_title = section['h2']
            article_body += f"<h2>{h2_title}</h2>\n"
            for h3_title in section['h3']:
                print(f"  - H3「{h3_title}」の本文を生成中...")
                h3_prompt = create_h3_content_prompt(main_keyword, outline_data['outline'], h3_title, persona_prompt, style_prompt)
                h3_content = self.gemini_generator.generate(h3_prompt)
                article_body += f"<h3>{h3_title}</h3>\n<p>{h3_content.replace(chr(10), '<br>')}</p>\n"

        # 5-4. まとめ部分の生成
        print("  - まとめ部分を生成中...")
        summary_prompt = create_summary_prompt(main_keyword, outline_data['title'], outline_data['outline'])
        summary_content = self.gemini_generator.generate(summary_prompt)
        # まとめは最後のH3なので、そのように扱う
        # 最後のH3見出しをoutline_dataから取得して、それと差し替える
        last_h3_title = outline_data['outline'][-1]['h3'][-1]
        article_body = article_body.replace(f"<h3>{last_h3_title}</h3>", f"<h3>{last_h3_title}</h3>\n<p>{summary_content.replace(chr(10), '<br>')}</p>\n")


        # 6. 最終成果物の組み立てと保存
        print("\n--- ステップ6: 最終成果物の組み立て ---")
        final_html = f"""
<!DOCTYPE html>
<html lang="ja">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{outline_data['title']}</title>
    <meta name="description" content="{outline_data['meta_description']}">
    <style>
        body {{ font-family: sans-serif; line-height: 1.6; padding: 20px; max-width: 800px; margin: 0 auto; }}
        h1, h2, h3 {{ color: #333; }}
        h1 {{ font-size: 2em; }}
        h2 {{ font-size: 1.5em; border-bottom: 2px solid #eee; padding-bottom: 5px; margin-top: 40px; }}
        h3 {{ font-size: 1.2em; border-left: 4px solid #667eea; padding-left: 10px; margin-top: 30px; }}
        p {{ margin-bottom: 15px; }}
        .lead {{ font-size: 1.1em; background-color: #f4f4f4; padding: 15px; border-radius: 5px; }}
    </style>
</head>
<body>
    <h1>{outline_data['title']}</h1>
    <div class="lead">{lead_content}</div>
    {article_body}
</body>
</html>
"""
        output_filename = f"{main_keyword.replace(' ', '_')}.html"
        with open(output_filename, "w", encoding="utf-8") as f:
            f.write(final_html)

        print(f"\n[SUCCESS] 記事の生成が完了しました！")
        print(f"ファイル名: {output_filename}")
        print("--- 全自動記事生成パイプラインを終了します ---")


if __name__ == '__main__':
    from dotenv import load_dotenv
    load_dotenv()
    
    GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
    SERPAPI_API_KEY = os.getenv("SERPAPI_API_KEY")

    if not GEMINI_API_KEY or not SERPAPI_API_KEY:
        print("エラー: 環境変数 `GEMINI_API_KEY` または `SERPAPI_API_KEY` が設定されていません。")
    else:
        gemini_gen = GeminiGenerator(api_key=GEMINI_API_KEY)
        suggester = KeywordSuggester()
        analyzer = SerpAnalyzer(api_key=SERPAPI_API_KEY)
        selector = SubKeywordSelector(gemini_generator=gemini_gen)
        prompter = PromptManager() # prompts_text配下のファイルを読み込む
        
        article_flow = ArticleCreationFlow(
            gemini_generator=gemini_gen,
            keyword_suggester=suggester,
            serp_analyzer=analyzer,
            sub_keyword_selector=selector,
            prompt_manager=prompter
        )
        article_flow.run()
