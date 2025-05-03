#!/usr/bin/env python
# -*- coding: utf-8 -*-

import json
import os
import re
from dotenv import load_dotenv


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


def preview_post_text(post_data):
    """
    投稿テキストをプレビューする
    """
    if not post_data:
        print("投稿データがありません。")
        return False

    # 投稿テキスト準備
    post_text = post_data.get("post_text", "").strip()

    # アフィリエイトURL
    affiliate_url = post_data.get("affiliateURL", "")

    # URLパラメータの置換処理
    if affiliate_url and "kntbouzu777-990&ch=api" in affiliate_url:
        # 990&ch=api を 001&ch=toolbar&ch_id=link に置換
        affiliate_url = affiliate_url.replace(
            "kntbouzu777-990&ch=api", "kntbouzu777-001&ch=toolbar&ch_id=link"
        )
        print("アフィリエイトURLのパラメータを置換しました")

    if not post_text:
        print("投稿テキストがありません。")
        return False

    # URLがすでにテキストに含まれている場合は削除（二重投稿防止）
    post_text = re.sub(r"https?://[^\s]+", "", post_text).strip()

    # 連続した改行を整理
    post_text = re.sub(r"\n{3,}", "\n\n", post_text)

    # アフィリエイトURLを末尾に追加
    if affiliate_url:
        # 投稿テキストにURLを追加
        if post_text.endswith("#PR"):
            # #PRタグの後に改行を入れてアフィリエイトURLを追加
            post_text = post_text + "\n" + affiliate_url
        else:
            # 末尾に改行とアフィリエイトURLを追加
            post_text = post_text + "\n\n" + affiliate_url

    # タイトル情報
    title = post_data.get("title", "")
    if title:
        print(f"【タイトル】\n{title}\n")

    # 画像情報
    if "imageURL" in post_data and post_data["imageURL"]:
        if isinstance(post_data["imageURL"], dict):
            for size, url in post_data["imageURL"].items():
                print(f"【画像({size})】\n{url}\n")
                break
        else:
            print(f"【画像】\n{post_data['imageURL']}\n")

    # 投稿プレビューを表示
    print("【投稿プレビュー】")
    print("=" * 50)
    print(post_text)
    print("=" * 50)

    # 文字数カウント
    print(f"\n文字数: {len(post_text)}")

    return True


def main():
    """
    メイン処理
    """
    print("X（Twitter）投稿内容のプレビューを表示します")

    # 投稿データを読み込む
    post_data = load_post_data()
    if not post_data:
        print("投稿データの読み込みに失敗しました")
        return False

    # 投稿テキストをプレビュー
    preview_post_text(post_data)


if __name__ == "__main__":
    main()
