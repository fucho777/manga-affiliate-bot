#!/usr/bin/env python
# -*- coding: utf-8 -*-

import json
import os
import sys
import time
import requests
from dotenv import load_dotenv
import logging
import urllib.parse
import urllib.request
from datetime import datetime
import re
import random

# ロギング設定
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler("x_posting.log", encoding="utf-8"),
    ],
)
logger = logging.getLogger(__name__)


def load_post_data():
    """
    current_post.jsonから投稿データを読み込む
    """
    try:
        with open("current_post.json", "r", encoding="utf-8") as f:
            post_data = json.load(f)
        return post_data
    except Exception as e:
        logger.error(f"投稿データの読み込みに失敗しました: {e}")
        return None


def download_image(image_url, save_path):
    """
    画像をダウンロードして保存する
    """
    try:
        urllib.request.urlretrieve(image_url, save_path)
        logger.info(f"画像をダウンロードしました: {save_path}")
        return True
    except Exception as e:
        logger.error(f"画像のダウンロードに失敗しました: {e}")
        return False


def create_twitter_client():
    """
    Twitter APIクライアントを作成する
    """
    try:
        # python-twitter-v2をインポート (pipでインストールする必要がある)
        try:
            import tweepy
        except ImportError:
            logger.error(
                "tweepyモジュールがインストールされていません。'pip install tweepy'を実行してください。"
            )
            return None

        # 環境変数から認証情報を読み込む
        load_dotenv()
        api_key = os.getenv("X_API_KEY")
        api_secret = os.getenv("X_API_SECRET")
        access_token = os.getenv("X_ACCESS_TOKEN")
        access_secret = os.getenv("X_ACCESS_SECRET")

        if not all([api_key, api_secret, access_token, access_secret]):
            logger.error(
                "TwitterのAPI認証情報が不足しています。.envファイルを確認してください。"
            )
            return None

        # Twitter API v2クライアントを作成
        client = tweepy.Client(
            consumer_key=api_key,
            consumer_secret=api_secret,
            access_token=access_token,
            access_token_secret=access_secret,
        )

        # 画像アップロード用のAPIv1.1クライアント
        auth = tweepy.OAuth1UserHandler(
            api_key, api_secret, access_token, access_secret
        )
        api_v1 = tweepy.API(auth)

        return {"client": client, "api_v1": api_v1}

    except Exception as e:
        logger.error(f"Twitterクライアントの作成に失敗しました: {e}")
        return None


def add_variation_to_text(text):
    """
    投稿テキストにバリエーションを追加して重複投稿エラーを回避する
    """
    # 現在時刻を取得
    now = datetime.now()
    time_str = now.strftime("%H:%M")
    
    # ランダムな絵文字を選択
    emojis = ["🔥", "✨", "💯", "👀", "📚", "🎮", "📲", "🌟", "💫", "🆕"]
    rand_emoji = random.choice(emojis)
    
    # ランダムなフレーズを選択
    phrases = [
        f"【{time_str}更新】",
        f"【オススメ{rand_emoji}】",
        f"【注目作品{rand_emoji}】",
        f"【今すぐチェック{rand_emoji}】",
        f"【{rand_emoji}話題の作品】",
        f"{rand_emoji}いま読むべき！",
        f"{rand_emoji}チェックしてみて",
        f"【{rand_emoji}{now.strftime('%m/%d')}】"
    ]
    
    variation = random.choice(phrases)
    
    # テキストの先頭にバリエーションを追加
    # ただし、すでに【】で始まっている場合は置き換える
    if text.startswith("【"):
        # 【】で囲まれた部分を検索
        match = re.match(r"【[^】]*】", text)
        if match:
            text = text.replace(match.group(0), variation, 1)
        else:
            text = variation + " " + text
    else:
        text = variation + " " + text
        
    return text


def is_duplicate_content_error(e):
    """
    エラーが重複コンテンツによるものかを判定
    """
    error_text = str(e).lower()
    return ("403" in error_text or "forbidden" in error_text) and "duplicate content" in error_text


def post_to_twitter(post_data, twitter_client, retry_count=0):
    """
    Twitterに投稿する
    """
    try:
        if not twitter_client or not post_data:
            logger.error("投稿に必要なデータがありません。")
            return False

        client = twitter_client["client"]
        api_v1 = twitter_client["api_v1"]

        # 投稿テキスト準備
        post_text = post_data.get("post_text", "").strip()

        # アフィリエイトURL（current_post.jsonからの直接取得を優先）
        affiliate_url = post_data.get("affiliateURL", "")

        # URLパラメータの置換処理
        if affiliate_url and "kntbouzu777-990&ch=api" in affiliate_url:
            # 990&ch=api を 001&ch=toolbar&ch_id=link に置換
            affiliate_url = affiliate_url.replace(
                "kntbouzu777-990&ch=api", "kntbouzu777-001&ch=toolbar&ch_id=link"
            )
            logger.info("アフィリエイトURLのパラメータを置換しました")

        if not post_text:
            logger.error("投稿テキストがありません。")
            return False

        # リトライの場合はテキストにバリエーションを追加
        if retry_count > 0:
            post_text = add_variation_to_text(post_text)
            logger.info(f"重複エラー回避のため投稿テキストを変更しました（リトライ{retry_count}回目）")

        # URLがすでにテキストに含まれている場合は削除（二重投稿防止）
        post_text = re.sub(r"https?://[^\s]+", "", post_text).strip()

        # 連続した改行を整理
        post_text = re.sub(r"\n{3,}", "\n\n", post_text)

        # アフィリエイトURLを末尾に追加
        if affiliate_url:
            # 投稿テキストにURLを追加（改行で区切る）
            if post_text.endswith("#PR"):
                # #PRタグの後に改行を入れてアフィリエイトURLを追加
                post_text = post_text + "\n" + affiliate_url
            else:
                # 末尾に改行とアフィリエイトURLを追加
                post_text = post_text + "\n\n" + affiliate_url

        try:
            # テキストのみの投稿を作成（画像なし）
            response = client.create_tweet(text=post_text)

            if response.data:
                tweet_id = response.data["id"]
                logger.info(f"投稿に成功しました！ Tweet ID: {tweet_id}")
                logger.info(f"投稿内容: {post_text}")

                # 投稿履歴を保存
                save_post_history(post_data, tweet_id, post_text)
                return True
            else:
                logger.error("投稿に失敗しました。レスポンスデータがありません。")
                return False
                
        except Exception as e:
            # 重複コンテンツエラーの場合、最大3回までリトライ
            if is_duplicate_content_error(e) and retry_count < 3:
                logger.warning(f"重複コンテンツエラーが発生しました: {e}")
                logger.info(f"投稿テキストにバリエーションを追加して再試行します（{retry_count+1}/3）")
                # 少し待機してから再試行
                time.sleep(2)
                return post_to_twitter(post_data, twitter_client, retry_count + 1)
            else:
                # それ以外のエラーまたはリトライ回数オーバー
                raise

    except Exception as e:
        logger.error(f"投稿処理でエラーが発生しました: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return False


def save_post_history(post_data, tweet_id, actual_post_text=None):
    """
    投稿履歴を保存する
    """
    try:
        history_file = "post_history.json"

        # 既存の履歴を読み込む
        history = []
        if os.path.exists(history_file):
            try:
                with open(history_file, "r", encoding="utf-8") as f:
                    history = json.load(f)
            except:
                history = []

        # 投稿履歴を追加
        history_entry = {
            "title": post_data["title"],
            "post_text": actual_post_text or post_data["post_text"],  # 実際に投稿したテキストを保存
            "tweet_id": tweet_id,
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        }

        history.append(history_entry)

        # 履歴を保存
        with open(history_file, "w", encoding="utf-8") as f:
            json.dump(history, f, ensure_ascii=False, indent=2)

        logger.info("投稿履歴を保存しました")

    except Exception as e:
        logger.error(f"投稿履歴の保存に失敗しました: {e}")


def check_post_history(title):
    """
    過去に同じタイトルの投稿があるかチェック
    """
    try:
        history_file = "post_history.json"
        if not os.path.exists(history_file):
            return False
            
        with open(history_file, "r", encoding="utf-8") as f:
            history = json.load(f)
            
        # 過去7日以内に同じタイトルの投稿があるかをチェック
        now = datetime.now()
        seven_days_ago = now.timestamp() - (7 * 24 * 60 * 60)
        
        for entry in history:
            if entry["title"] == title:
                try:
                    post_time = datetime.strptime(entry["timestamp"], "%Y-%m-%d %H:%M:%S")
                    if post_time.timestamp() > seven_days_ago:
                        logger.warning(f"過去7日以内に同じタイトルの投稿があります: {title}")
                        return True
                except:
                    pass
                    
        return False
    except Exception as e:
        logger.error(f"投稿履歴のチェックに失敗しました: {e}")
        return False


def main():
    """
    メイン処理
    """
    logger.info("X（Twitter）への投稿処理を開始します")

    # 投稿データを読み込む
    post_data = load_post_data()
    if not post_data:
        logger.error("投稿データの読み込みに失敗しました")
        return False
        
    # 過去7日以内に同じタイトルの投稿があるかチェック
    title = post_data.get("title", "")
    if title and check_post_history(title):
        logger.warning("過去7日以内に同じタイトルの投稿があるため、処理を中止します")
        # この場合は成功として扱い、別の投稿が選ばれるようにする
        return True

    # Twitterクライアントを作成
    twitter_client = create_twitter_client()
    if not twitter_client:
        logger.error("Twitterクライアントの作成に失敗しました")
        return False

    # 投稿する
    success = post_to_twitter(post_data, twitter_client)

    if success:
        logger.info("投稿処理が完了しました")
        return True
    else:
        logger.error("投稿処理に失敗しました")
        return False


if __name__ == "__main__":
    result = main()
    sys.exit(0 if result else 1)
