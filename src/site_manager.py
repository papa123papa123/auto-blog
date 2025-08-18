import os
import json
from datetime import datetime
from typing import Dict, List, Optional
import pandas as pd
from pathlib import Path

class SiteManager:
    def __init__(self):
        project_root = Path(__file__).parent.parent
        config_path = project_root / "config"
        
        self.sites_manager_file = config_path / "sites_manager.json"
        self.credentials_file = config_path / "WP API.xlsx"

        self.sites_config = self._load_json(self.sites_manager_file)
        self.credentials_df = self._load_credentials()

        # *** この機能がExcelを読み込み、空のJSONにサイトを自動登録します ***
        if not self.credentials_df.empty:
            self._synchronize_sites()

    def _synchronize_sites(self):
        """ExcelのサイトリストとJSONの管理リストを同期する"""
        print("[INFO] ExcelとJSONのサイト情報を同期中...")
        excel_sites = self.credentials_df.to_dict('records')
        
        tracked_site_names = [site['name'] for site in self.sites_config['active_sites']] + \
                             [site['name'] for site in self.sites_config['completed_sites']]
        
        sites_added = False
        for site_in_excel in excel_sites:
            site_name = site_in_excel.get('site_name')
            domain = site_in_excel.get('url')
            
            if site_name and site_name not in tracked_site_names:
                print(f"  -> 新規サイト「{site_name}」をExcelから発見。自動登録します。")
                self.add_new_site(site_name, domain)
                sites_added = True
        
        if sites_added:
            print("[OK] 同期が完了し、新規サイトが登録されました。")
        else:
            print("[OK] サイト情報は既に最新の状態です。")


    def _load_credentials(self) -> pd.DataFrame:
        """Excelファイルから認証情報を読み込む"""
        try:
            df = pd.read_excel(self.credentials_file)
            print("[OK] 認証ファイル(Excel)の読み込みに成功しました。")
            return df
        except FileNotFoundError:
            print(f"[NG] 警告: 認証ファイル `WP API.xlsx` が `config` フォルダに見つかりません。")
            return pd.DataFrame()
        except Exception as e:
            print(f"[NG] 認証ファイルの読み込み中にエラーが発生しました: {e}")
            return pd.DataFrame()

    def get_credentials_by_name(self, site_name: str) -> Optional[Dict]:
        """サイト名で認証情報を取得する"""
        if self.credentials_df.empty:
            return None
        
        site_data = self.credentials_df[self.credentials_df['site_name'] == site_name]
        
        if not site_data.empty:
            return site_data.iloc[0].to_dict()
        
        return None

    def _load_json(self, filepath: str) -> dict:
        try:
            with open(filepath, 'r', encoding="utf-8") as f:
                return json.load(f)
        except FileNotFoundError:
            # ファイルがない場合は、空の基本構造を返す
            return {
                "site_management": {"max_articles_per_site": 100, "auto_create_new_site": true},
                "active_sites": [], "completed_sites": [], "site_counter": 0
            }

    def _save_json(self, data: dict, filepath: str):
        os.makedirs(os.path.dirname(filepath), exist_ok=True)
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

    def add_new_site(self, site_name: str, domain: str):
        """新しいサイト情報をsites_manager.jsonに追加する"""
        site_counter = self.sites_config.get("site_counter", 0) + 1
        site_id = f"site_{site_counter:03d}"

        new_site = {
            "id": site_id, "name": site_name, "domain": domain,
            "created_date": datetime.now().isoformat(), "article_count": 0,
            "status": "active",
            "max_articles": self.sites_config["site_management"]["max_articles_per_site"]
        }
        
        self.sites_config["active_sites"].append(new_site)
        self.sites_config["site_counter"] = site_counter
        self._save_json(self.sites_config, self.sites_manager_file)
        return new_site

    def get_next_available_site(self) -> Optional[Dict]:
        """次に記事を投稿すべきサイト情報を取得する"""
        active_sites = self.sites_config.get("active_sites", [])
        if not active_sites:
            return None
        
        for site in active_sites:
            if site.get("article_count", 0) < site.get("max_articles", 100):
                return site
        return None

    def update_article_count(self, site_id: str, increment: int = 1):
        """サイトの記事数を更新し、上限に達したら完了済みに移動する"""
        site_to_move = None
        for site in self.sites_config["active_sites"]:
            if site["id"] == site_id:
                site["article_count"] += increment
                print(f"[OK] サイト「{site['name']}」の記事数を更新しました: {site['article_count']}")
                if site["article_count"] >= site["max_articles"]:
                    site_to_move = site
                break

        if site_to_move:
            site_to_move["status"] = "completed"
            site_to_move["completed_date"] = datetime.now().isoformat()
            self.sites_config["active_sites"].remove(site_to_move)
            self.sites_config["completed_sites"].append(site_to_move)
            print(f"[DONE] サイト「{site_to_move['name']}」が記事数上限に達したため、完了済みに移動しました。")

        self._save_json(self.sites_config, self.sites_manager_file)