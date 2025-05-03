import os
import requests
from dotenv import load_dotenv


def check_dmm_auth():
    """DMM API認証のテスト"""
    # 環境変数の読み込み
    load_dotenv()

    # APIキーの取得
    api_id = os.getenv("DMM_API_ID")
    affiliate_id = os.getenv("DMM_AFFILIATE_ID")

    # テスト用のAPIリクエストパラメータ
    params = {
        "api_id": api_id,
        "affiliate_id": affiliate_id,
        "site": "FANZA",
        "service": "digital",
        "floor": "videoa",  # floorをvideoaに変更
        "hits": 10,
        "sort": "date",
        "output": "json",
    }

    try:
        # APIリクエスト
        response = requests.get(
            "https://api.dmm.com/affiliate/v3/ItemList", params=params
        )

        # レスポンスをチェック
        if response.status_code == 200:
            data = response.json()
            if "result" in data:
                print("DMM API認証成功！")
                print(f"取得した作品数: {data['result']['result_count']}")
                return True
            else:
                print(f"API応答エラー: {data}")
                return False
        else:
            print(f"APIリクエストエラー: ステータスコード {response.status_code}")
            print(f"エラー詳細: {response.text}")  # エラーの詳細を表示
            return False

    except Exception as e:
        print(f"DMM API接続エラー: {e}")
        return False


if __name__ == "__main__":
    check_dmm_auth()
