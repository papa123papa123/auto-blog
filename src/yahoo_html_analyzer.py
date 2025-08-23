# src/yahoo_html_analyzer.py

from bs4 import BeautifulSoup
import re
from pathlib import Path
from typing import Dict, List, Optional
import logging

# ロガーの設定
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

class YahooHTMLAnalyzer:
    def __init__(self):
        # 弱いライバルサイトの定義（既存のKeywordAnalyzerと同じ）
        self.weak_sites = {
            'Q&Aサイト': [
                "chiebukuro.yahoo.co.jp", "okwave.jp", "oshiete.goo.ne.jp",
                "komachi.yomiuri.co.jp", "qa.itmedia.co.jp", "teratail.com",
                "stackexchange.com", "quora.com", "reddit.com"
            ],
            'SNS': [
                "x.com", "twitter.com", "instagram.com", "facebook.com",
                "youtube.com", "tiktok.com", "pinterest.jp", "pinterest.com"
            ],
            '無料ブログ': [
                "ameblo.jp", "hatenablog.com", "note.com", "livedoor.jp",
                "fc2.com", "seesaa.net", "jugem.jp", "exblog.jp",
                "rakuten.co.jp/plaza", "goo.ne.jp/blog"
            ]
        }
        
        print("[OK] YahooHTMLAnalyzerの初期化に成功しました。")
    
    def analyze_html_file(self, html_path: Path) -> Dict:
        """Yahoo検索結果のHTMLを解析"""
        try:
            with open(html_path, 'r', encoding='utf-8') as f:
                html_content = f.read()
            
            soup = BeautifulSoup(html_content, 'html.parser')
            
            # 検索結果件数の抽出
            total_results = self._extract_yahoo_total_results(soup)
            
            # 上位結果の解析
            top_results = self._analyze_yahoo_top_results(soup)
            
            return {
                'total_results': total_results,
                'top_results': top_results
            }
            
        except FileNotFoundError:
            print(f"[WARN] HTMLファイルが見つかりません: {html_path}")
            return {'total_results': 0, 'top_results': []}
        except Exception as e:
            print(f"[ERROR] HTML解析中にエラーが発生: {html_path} - {e}")
            return {'total_results': 0, 'top_results': []}
    
    def _extract_yahoo_total_results(self, soup: BeautifulSoup) -> int:
        """Yahoo検索結果件数を抽出"""
        # Yahoo検索結果の件数表示部分を特定（複数のパターンを試行）
        result_stats = None
        
        # パターン1: SearchResultInfoクラス
        result_stats = soup.find('div', {'class': 'SearchResultInfo'})
        
        # パターン2: 件数を含むテキストを検索
        if not result_stats:
            result_stats = soup.find(string=re.compile(r'[\d,]+件'))
            if result_stats:
                result_stats = result_stats.parent
        
        # パターン3: 検索結果の概要部分
        if not result_stats:
            result_stats = soup.find('div', {'class': 'SearchResultSummary'})
        
        # パターン4: より広範囲で件数を検索
        if not result_stats:
            for element in soup.find_all(['div', 'span', 'p']):
                text = element.get_text()
                if re.search(r'[\d,]+件', text):
                    result_stats = element
                    break
        
        if result_stats:
            text = result_stats.get_text()
            # 数字部分を抽出（カンマ区切り対応）
            match = re.search(r'([\d,]+)\s*件', text)
            if match:
                try:
                    return int(match.group(1).replace(',', ''))
                except ValueError:
                    pass
        
        # 件数が見つからない場合
        print(f"[WARN] 検索結果件数を抽出できませんでした。HTMLの構造を確認してください。")
        return 0
    
    def _analyze_yahoo_top_results(self, soup: BeautifulSoup) -> List[Dict]:
        """Yahoo検索結果の上位結果を解析"""
        results = []
        
        # Yahoo検索結果の各項目を特定（複数のパターンを試行）
        search_results = []
        
        # パターン1: Algoクラス（一般的なYahoo検索結果）
        search_results = soup.find_all('div', {'class': 'Algo'})
        
        # パターン2: 検索結果のコンテナ
        if not search_results:
            search_results = soup.find_all('div', {'class': 'SearchResult'})
        
        # パターン3: より広範囲で検索結果を検索
        if not search_results:
            # リンクとタイトルの組み合わせを探す
            links = soup.find_all('a', href=True)
            for link in links:
                if link.get('href') and link.get('href').startswith('http'):
                    title = link.get_text().strip()
                    if title and len(title) > 10:  # 意味のあるタイトル
                        search_results.append(link)
        
        # 上位10件まで解析
        for i, result in enumerate(search_results[:10]):
            title_elem = None
            link_elem = None
            
            # 結果の構造に応じてタイトルとリンクを取得
            if hasattr(result, 'find'):
                # BeautifulSoup要素の場合
                title_elem = result.find('h3') or result.find('a', {'class': 'title'}) or result
                link_elem = result.find('a') or result
            else:
                # 直接リンク要素の場合
                title_elem = result
                link_elem = result
            
            if title_elem and link_elem:
                title = title_elem.get_text().strip()
                link = link_elem.get('href', '')
                
                # 空のタイトルやリンクはスキップ
                if not title or not link or link.startswith('#'):
                    continue
                
                # 弱いライバルサイトの判定
                site_type = self._classify_site(link)
                
                results.append({
                    'rank': i + 1,
                    'title': title,
                    'url': link,
                    'site_type': site_type
                })
        
        return results
    
    def _classify_site(self, url: str) -> Optional[str]:
        """URLからサイトタイプを判定"""
        for site_type, domains in self.weak_sites.items():
            if any(domain in url for domain in domains):
                return site_type
        return None
    
    def get_analysis_summary(self, html_path: Path) -> str:
        """HTML解析結果のサマリーを取得"""
        analysis_result = self.analyze_html_file(html_path)
        
        total_results = analysis_result['total_results']
        top_results = analysis_result['top_results']
        
        summary = f"検索結果件数: {total_results:,}件\n"
        summary += f"解析対象結果: {len(top_results)}件\n"
        
        # 弱いライバルの分布
        weak_sites_count = {}
        for result in top_results:
            site_type = result.get('site_type')
            if site_type:
                weak_sites_count[site_type] = weak_sites_count.get(site_type, 0) + 1
        
        if weak_sites_count:
            summary += "\n弱いライバルの分布:\n"
            for site_type, count in weak_sites_count.items():
                summary += f"  {site_type}: {count}件\n"
        else:
            summary += "\n弱いライバルは見つかりませんでした。\n"
        
        return summary

# テスト用コード
if __name__ == "__main__":
    analyzer = YahooHTMLAnalyzer()
    
    # テスト用のHTMLファイルパス
    test_html_path = Path("yahoo_htmls/test_standard.html")
    
    if test_html_path.exists():
        print("HTML解析テスト:")
        result = analyzer.analyze_html_file(test_html_path)
        print(f"検索結果件数: {result['total_results']}")
        print(f"上位結果数: {len(result['top_results'])}")
        
        summary = analyzer.get_analysis_summary(test_html_path)
        print(f"\n解析サマリー:\n{summary}")
    else:
        print("テスト用のHTMLファイルが見つかりません。")
        print("まずYahooHTMLCollectorでHTMLを収集してください。")
