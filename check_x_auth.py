import os
import tweepy
from dotenv import load_dotenv

def check_x_auth():
    """X API認証のテスト"""
    # 環境変数の読み込み
    load_dotenv()
    
    # APIキーの取得
    api_key = os.getenv('X_API_KEY')
    api_secret = os.getenv('X_API_SECRET')
    access_token = os.getenv('X_ACCESS_TOKEN')
    access_secret = os.getenv('X_ACCESS_SECRET')
    
    try:
        # 認証オブジェクトの作成
        auth = tweepy.OAuth1UserHandler(
            api_key, api_secret, access_token, access_secret
        )
        
        # APIインスタンスの作成
        api = tweepy.API(auth)
        
        # アカウント情報を取得してチェック
        user = api.verify_credentials()
        print(f"認証成功！ @{user.screen_name}としてログインしています。")
        return True
    
    except Exception as e:
        print(f"認証エラー: {e}")
        return False

if __name__ == "__main__":
    check_x_auth()