#!/usr/bin/env python
# -*- coding: utf-8 -*-

import json
import os
import sys
from dotenv import load_dotenv
import urllib.parse

# 環境変数を読み込む
load_dotenv()

# アフィリエイト関連の設定を環境変数から取得（デフォルト値付き）
AFFILIATE_ID = os.getenv("AFFILIATE_ID", "")
# プロセス用とX投稿用のアフィリエイト設定
AFFILIATE_PROCESS_SITE = os.getenv("AFFILIATE_SITE", "990")  # データ処理用
AFFILIATE_PROCESS_CHANNEL = os.getenv("AFFILIATE_CHANNEL", "api")  # データ処理用
AFFILIATE_POST_SITE = os.getenv("AFFILIATE_POST_SITE", "001")  # X投稿用
AFFILIATE_POST_CHANNEL = os.getenv("AFFILIATE_POST_CHANNEL", "toolbar")  # X投稿用
AFFILIATE_POST_CHANNEL_ID = os.getenv(
    "AFFILIATE_POST_CHANNEL_ID", "link"
)  # X投稿用チャンネルID


def load_post_data():
    """
    current_post.jsonから投稿データを読み込む
    """
    try:
        with open("current_post.json", "r", encoding="utf-8") as f:
            post_data = json.load(f)
        return post_data
    except Exception as e:
        print(f"投稿データの読み込みに失敗しました: {e}")
        return None


def preview_post():
    """
    投稿内容をプレビューする
    """
    # 投稿データを読み込む
    post_data = load_post_data()
    if not post_data:
        print("投稿データの読み込みに失敗しました")
        return False

    # データを表示
    print("\n===== 投稿データ =====")
    print(f"タイトル: {post_data.get('title', '未設定')}")
    if "author" in post_data:
        print(f"作者: {post_data.get('author', '不明')}")

    print("\n----- 元のアフィリエイトURL -----")
    affiliate_url = post_data.get("affiliateURL", "")
    print(affiliate_url)

    # URLパラメータの置換処理
    if affiliate_url and AFFILIATE_ID:
        # データ処理用のパラメータをX投稿用のパラメータに置換
        process_params = (
            f"{AFFILIATE_ID}-{AFFILIATE_PROCESS_SITE}&ch={AFFILIATE_PROCESS_CHANNEL}"
        )
        post_params = f"{AFFILIATE_ID}-{AFFILIATE_POST_SITE}&ch={AFFILIATE_POST_CHANNEL}&ch_id={AFFILIATE_POST_CHANNEL_ID}"

        # 古いパラメータも互換性のために処理
        old_process_params = f"kntbouzu777-990&ch=api"

        if process_params in affiliate_url:
            new_url = affiliate_url.replace(process_params, post_params)
            print("\n----- X投稿用に変換されたURL（環境変数使用） -----")
            print(new_url)
            print(f"\nパラメータ変更: {process_params} → {post_params}")
        elif old_process_params in affiliate_url:
            new_url = affiliate_url.replace(old_process_params, post_params)
            print("\n----- X投稿用に変換されたURL（旧形式から変換） -----")
            print(new_url)
            print(f"\nパラメータ変更: {old_process_params} → {post_params}")
        else:
            print(
                "\n※ URLパラメータの置換は行われませんでした（パターンが一致しません）"
            )
    else:
        print("\n※ アフィリエイトURLが見つからないか、AFFILIATE_IDが設定されていません")

    # 投稿テキスト準備
    post_text = post_data.get("post_text", "").strip()

    # 投稿プレビュー
    print("\n===== 投稿テキストプレビュー =====")
    print(post_text)

    # URLを含めた最終的な投稿
    print("\n===== 最終投稿プレビュー =====")

    # URLがすでにテキストに含まれている場合は削除（二重投稿防止）
    cleaned_text = post_text.strip()

    # アフィリエイトURLを末尾に追加
    if affiliate_url:
        # 投稿テキストにURLを追加（改行で区切る）
        if cleaned_text.endswith("#PR"):
            # #PRタグの後に改行を入れてアフィリエイトURLを追加
            final_text = cleaned_text + "\n" + new_url
        else:
            # 末尾に改行とアフィリエイトURLを追加
            final_text = cleaned_text + "\n\n" + new_url

        print(final_text)
        print(f"\n文字数: {len(final_text)}文字")
    else:
        print(cleaned_text)
        print(f"\n文字数: {len(cleaned_text)}文字")

    return True


if __name__ == "__main__":
    print("X（Twitter）への投稿プレビューを表示します（実際の投稿は行いません）")
    preview_post()
