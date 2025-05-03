import os
import json
import requests
import sys  # sysモジュールを追加
from datetime import datetime, timedelta
from dotenv import load_dotenv


# 必須環境変数のチェック
def check_required_env_vars():
    """必須環境変数が設定されているかチェックし、不足している場合はエラーメッセージを出力して終了"""
    required_vars = [
        "DMM_API_ID",
        "DMM_AFFILIATE_ID",
    ]

    missing_vars = []
    for var in required_vars:
        if not os.getenv(var):
            missing_vars.append(var)

    if missing_vars:
        print(
            f"エラー: 以下の必須環境変数が設定されていません: {', '.join(missing_vars)}"
        )
        print(
            "処理を中止します。.envファイルまたはGitHub Secretsで環境変数を設定してください。"
        )
        sys.exit(1)

    print("すべての必須環境変数が設定されています。処理を続行します。")


def get_available_floors(api_id, affiliate_id):
    """DMM APIから利用可能なフロア一覧を取得する"""
    params = {"api_id": api_id, "affiliate_id": affiliate_id, "output": "json"}

    try:
        response = requests.get(
            "https://api.dmm.com/affiliate/v3/FloorList", params=params
        )
        print(f"デバッグ: フロア一覧取得ステータスコード: {response.status_code}")

        if response.status_code == 200:
            data = response.json()
            if "result" in data and "site" in data["result"]:
                floors = []
                for site in data["result"]["site"]:
                    if "service" in site:
                        for service in site["service"]:
                            if "floor" in service:
                                for floor in service["floor"]:
                                    floors.append(
                                        {
                                            "site": site.get("name", ""),
                                            "service": service.get("name", ""),
                                            "floor": floor.get("id", ""),
                                            "floor_name": floor.get("name", ""),
                                        }
                                    )

                print(f"利用可能なフロア一覧を取得しました。合計: {len(floors)}件")
                return floors
            else:
                print(f"デバッグ: レスポンス構造異常: {data}")
                return []
        else:
            print(f"デバッグ: フロア一覧API呼び出しエラー: {response.text}")
            return []

    except Exception as e:
        print(f"フロア一覧取得エラー: {e}")
        return []


def fetch_manga_data():
    """FANZA APIから漫画データを取得（FANZAのみ）"""
    # 環境変数の読み込み
    load_dotenv()

    # 必須環境変数のチェックを実行
    check_required_env_vars()

    # APIキーの取得
    api_id = os.getenv("DMM_API_ID")
    affiliate_id = os.getenv("DMM_AFFILIATE_ID")

    # デバッグ情報: APIキーの確認
    print(f"デバッグ: API ID設定状態: {'設定済み' if api_id else '未設定'}")
    print(
        f"デバッグ: アフィリエイトID設定状態: {'設定済み' if affiliate_id else '未設定'}"
    )

    # 1週間前の日付を計算（新着判定用）
    one_week_ago = (datetime.now() - timedelta(days=7)).strftime("%Y-%m-%d")
    print(f"デバッグ: 新着判定用日付: {one_week_ago}")

    # 収集したデータを保存するリスト
    all_items = []

    try:
        # FANZAのコミックを取得
        print("\nFANZAのコミック商品を取得します")
        comic_items = fetch_items(
            api_id, affiliate_id, "FANZA", "ebook", "comic", one_week_ago
        )
        all_items.extend(comic_items)
        print(f"コミック商品: {len(comic_items)}件取得しました")

        # 取得したデータをJSON形式で保存
        with open("manga_data_raw.json", "w", encoding="utf-8") as f:
            json.dump(all_items, f, ensure_ascii=False, indent=2)

        # セール商品だけを別に抽出
        sale_items = [
            item
            for item in all_items
            if "prices" in item
            and "price" in item["prices"]
            and "list_price" in item["prices"]
            and int(item["prices"]["price"]) < int(item["prices"]["list_price"])
        ]

        # セール商品を価格順にソート
        sale_items.sort(key=lambda x: int(x["prices"]["price"]))

        # セール商品に割引率の情報を追加
        for item in sale_items:
            price = int(item["prices"]["price"])
            list_price = int(item["prices"]["list_price"])
            discount_rate = round((1 - price / list_price) * 100)
            item["discount_rate"] = discount_rate
            item["discount_info"] = f"{discount_rate}%OFF ({list_price}円 → {price}円)"

        # セール商品をJSON形式で保存
        with open("sale_manga_data.json", "w", encoding="utf-8") as f:
            json.dump(sale_items, f, ensure_ascii=False, indent=2)

        print(f"\n合計: {len(all_items)}作品のデータを取得しました")
        print(f"割引商品: {len(sale_items)}作品を発見しました")

        # 最大割引率のアイテムを表示
        if sale_items:
            max_discount_item = max(sale_items, key=lambda x: x["discount_rate"])
            print(
                f"最大割引商品: {max_discount_item.get('title', '不明')} - {max_discount_item.get('discount_info', '不明')}"
            )

        # 重要なセール情報を表示
        if sale_items:
            high_discount_items = [
                item for item in sale_items if item["discount_rate"] >= 50
            ]
            if high_discount_items:
                print(f"\n50%以上割引の商品: {len(high_discount_items)}件")
                for item in sorted(
                    high_discount_items, key=lambda x: x["discount_rate"], reverse=True
                )[:5]:
                    price = int(item["prices"]["price"])
                    print(
                        f"- {item.get('title', '不明')}: {item.get('discount_info', '不明')}"
                    )

        return True

    except Exception as e:
        print(f"データ取得エラー: {e}")
        import traceback

        print(f"詳細なエラー情報: {traceback.format_exc()}")
        return False


def fetch_items(api_id, affiliate_id, site_id, service_id, floor_id, one_week_ago):
    """指定されたパラメータでAPIからアイテムを取得"""
    items = []

    # 基本的なAPIパラメータ
    base_params = {
        "api_id": api_id,
        "affiliate_id": affiliate_id,
        "site": site_id,
        "service": service_id,
        "floor": floor_id,
        "hits": 100,  # 一度に取得する件数
        "output": "json",
    }

    # デバッグ情報: ベースパラメータ
    print(f"デバッグ: ベースパラメータ: {base_params}")

    # 1. ランキング上位作品の取得（デイリー）
    daily_params = base_params.copy()
    daily_params.update({"sort": "rank", "period": "day"})
    print(f"デバッグ: デイリーランキングAPI呼び出し: {daily_params}")
    response = requests.get(
        "https://api.dmm.com/affiliate/v3/ItemList", params=daily_params
    )
    if response.status_code == 200:
        data = response.json()
        if "result" in data and "items" in data["result"]:
            items_count = len(data["result"]["items"])
            print(f"デイリーランキング: {items_count}件取得")
            for item in data["result"]["items"]:
                item["ranking_info"] = {"daily_rank": item.get("rank", 0)}
                items.append(item)
    elif response.status_code == 400:
        # エラー時は簡潔なメッセージのみ表示
        print(f"デバッグ: デイリーランキング - リクエストエラー(400)")

    # 2. ランキング上位作品の取得（週間）
    weekly_params = base_params.copy()
    weekly_params.update({"sort": "rank", "period": "week"})
    print(f"デバッグ: 週間ランキングAPI呼び出し: {weekly_params}")
    response = requests.get(
        "https://api.dmm.com/affiliate/v3/ItemList", params=weekly_params
    )
    if response.status_code == 200:
        data = response.json()
        if "result" in data and "items" in data["result"]:
            items_count = len(data["result"]["items"])
            print(f"週間ランキング: {items_count}件取得")
            # 既存のデータと統合（content_idをキーとして）
            for item in data["result"]["items"]:
                content_id = item.get("content_id")
                existing = next(
                    (x for x in items if x.get("content_id") == content_id), None
                )
                if existing:
                    existing["ranking_info"]["weekly_rank"] = item.get("rank", 0)
                else:
                    item["ranking_info"] = {"weekly_rank": item.get("rank", 0)}
                    items.append(item)
    elif response.status_code == 400:
        # エラー時は簡潔なメッセージのみ表示
        print(f"デバッグ: 週間ランキング - リクエストエラー(400)")

    # 3. ランキング上位作品の取得（月間）
    monthly_params = base_params.copy()
    monthly_params.update({"sort": "rank", "period": "month"})
    print(f"デバッグ: 月間ランキングAPI呼び出し: {monthly_params}")
    response = requests.get(
        "https://api.dmm.com/affiliate/v3/ItemList", params=monthly_params
    )
    if response.status_code == 200:
        data = response.json()
        if "result" in data and "items" in data["result"]:
            items_count = len(data["result"]["items"])
            print(f"月間ランキング: {items_count}件取得")
            # 既存のデータと統合
            for item in data["result"]["items"]:
                content_id = item.get("content_id")
                existing = next(
                    (x for x in items if x.get("content_id") == content_id), None
                )
                if existing:
                    existing["ranking_info"]["monthly_rank"] = item.get("rank", 0)
                else:
                    item["ranking_info"] = {"monthly_rank": item.get("rank", 0)}
                    items.append(item)
    elif response.status_code == 400:
        # エラー時は簡潔なメッセージのみ表示
        print(f"デバッグ: 月間ランキング - リクエストエラー(400)")

    # 4. 新着作品の取得
    new_params = base_params.copy()
    new_params.update({"sort": "date", "released_date_from": one_week_ago})
    print(f"デバッグ: 新着作品API呼び出し: {new_params}")
    response = requests.get(
        "https://api.dmm.com/affiliate/v3/ItemList", params=new_params
    )
    if response.status_code == 200:
        data = response.json()
        if "result" in data and "items" in data["result"]:
            items_count = len(data["result"]["items"])
            print(f"新着作品: {items_count}件取得")
            # 既存のデータと統合
            for item in data["result"]["items"]:
                content_id = item.get("content_id")
                existing = next(
                    (x for x in items if x.get("content_id") == content_id), None
                )
                if existing:
                    existing["is_new"] = True
                else:
                    item["is_new"] = True
                    item["ranking_info"] = {}
                    items.append(item)
    elif response.status_code == 400:
        # エラー時は簡潔なメッセージのみ表示
        print(f"デバッグ: 新着作品 - リクエストエラー(400)")

    # 5. セール/割引作品の取得
    sale_params = base_params.copy()
    sale_params.update({"sort": "price", "hits": 100})
    print(f"デバッグ: セール/割引作品API呼び出し: {sale_params}")
    response = requests.get(
        "https://api.dmm.com/affiliate/v3/ItemList", params=sale_params
    )
    if response.status_code == 200:
        data = response.json()
        if "result" in data and "items" in data["result"]:
            items_count = len(data["result"]["items"])
            # 割引商品を検出（通常価格と現在価格を比較）
            discount_count = 0
            for item in data["result"]["items"]:
                # 価格情報をチェック
                if "prices" in item:
                    prices = item["prices"]
                    if "price" in prices and "list_price" in prices:
                        price = int(prices["price"])
                        list_price = int(prices["list_price"])
                        if price < list_price:
                            discount_count += 1

                # 重複を避けて追加
                content_id = item.get("content_id")
                existing = next(
                    (x for x in items if x.get("content_id") == content_id), None
                )
                if not existing:
                    if "ranking_info" not in item:
                        item["ranking_info"] = {}
                    items.append(item)
            print(f"割引作品: {discount_count}件取得")
    elif response.status_code == 400:
        # エラー時は簡潔なメッセージのみ表示
        print(f"デバッグ: セール/割引作品 - リクエストエラー(400)")

    return items


if __name__ == "__main__":
    fetch_manga_data()
