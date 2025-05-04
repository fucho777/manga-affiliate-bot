import json
import pandas as pd
from datetime import datetime
import requests
import os
from dotenv import load_dotenv
import time
import subprocess
import re  # 正規表現のモジュール
import urllib.parse  # URLエンコード用のモジュール追加
import sys  # プログラム終了用にsysモジュール追加

# プログラム開始時に環境変数を読み込み
load_dotenv()


# 必須環境変数のチェック
def check_required_env_vars():
    """
    必須環境変数が設定されているかチェックし、不足している場合はエラーメッセージを表示して終了
    """
    required_vars = [
        "AFFILIATE_ID",
        "AFFILIATE_SITE",
        "AFFILIATE_CHANNEL",
        "AFFILIATE_POST_SITE",
        "AFFILIATE_POST_CHANNEL",
        "AFFILIATE_POST_CHANNEL_ID",
        "OPENROUTER_API_KEY",
        "OPENROUTER_MODEL",
        "OPENROUTER_SYSTEM_PROMPT",
        "OPENROUTER_USER_PROMPT_TEMPLATE",
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


# 環境変数チェックを実行
check_required_env_vars()

# アフィリエイト関連の設定を環境変数から取得（エラーチェック済みなのでデフォルト値不要）
AFFILIATE_ID = os.getenv("AFFILIATE_ID")
AFFILIATE_SITE = os.getenv("AFFILIATE_SITE")
AFFILIATE_CHANNEL = os.getenv("AFFILIATE_CHANNEL")


def update_manga_data():
    """
    fetch_manga_data.pyを実行して最新のデータを取得する
    """
    print("データを更新しています...")
    try:
        # fetch_manga_data.pyを実行
        result = subprocess.run(
            ["python", "fetch_manga_data.py"],
            capture_output=True,
            text=True,
            check=True,
        )
        print("データ更新完了")
        print(result.stdout)
        return True
    except subprocess.CalledProcessError as e:
        print(f"データ更新エラー: {e}")
        print(f"エラー出力: {e.stderr}")
        return False


def rewrite_text_with_ai(original_text):
    """
    オープンルーターAPIを使用して投稿テキストをリライトする
    """
    # 環境変数は既にプログラム開始時に読み込み済みのため、ここでは不要
    # load_dotenv()

    # APIキーを環境変数から取得
    api_key = os.getenv("OPENROUTER_API_KEY")

    if not api_key:
        raise ValueError(
            "環境変数OPENROUTER_API_KEYが設定されていません。処理を中止します。"
        )

    # モデルとプロンプトを環境変数から取得（デフォルト値なし）
    model = os.getenv("OPENROUTER_MODEL")
    if not model:
        raise ValueError(
            "環境変数OPENROUTER_MODELが設定されていません。処理を中止します。"
        )

    print(f"使用するAIモデル: {model}")

    # システムプロンプトを取得
    system_prompt = os.getenv("OPENROUTER_SYSTEM_PROMPT")
    if not system_prompt:
        raise ValueError(
            "環境変数OPENROUTER_SYSTEM_PROMPTが設定されていません。処理を中止します。"
        )

    # ユーザープロンプトテンプレートを取得
    user_prompt_template = os.getenv("OPENROUTER_USER_PROMPT_TEMPLATE")
    if not user_prompt_template:
        raise ValueError(
            "環境変数OPENROUTER_USER_PROMPT_TEMPLATEが設定されていません。処理を中止します。"
        )

    # ユーザープロンプトにテキストを挿入
    user_prompt = user_prompt_template.format(text=original_text)

    # オープンルーターAPIエンドポイント
    url = "https://openrouter.ai/api/v1/chat/completions"

    # リクエストヘッダー
    headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}

    # リクエストボディ
    data = {
        "model": model,
        "messages": [
            {
                "role": "system",
                "content": system_prompt,
            },
            {
                "role": "user",
                "content": user_prompt,
            },
        ],
    }

    try:
        # リクエスト送信
        response = requests.post(url, headers=headers, json=data)

        # デバッグ情報として生のレスポンスを出力
        print(f"API レスポンスステータス: {response.status_code}")
        print(f"API レスポンス内容: {response.text[:500]}...")

        # レスポンスを処理
        if response.status_code == 200:
            response_data = response.json()

            # レスポンス構造のデバッグ
            print(f"レスポンスのキー: {list(response_data.keys())}")

            # 応答データ構造の確認と処理
            if "choices" in response_data and response_data["choices"]:
                # 従来の形式
                raw_text = response_data["choices"][0]["message"]["content"].strip()
            elif "data" in response_data and response_data["data"]:
                # 代替の形式1
                raw_text = response_data["data"][0]["content"].strip()
            elif "response" in response_data:
                # 代替の形式2
                raw_text = response_data["response"].strip()
            else:
                # レスポンス形式が判断できない場合
                print("API レスポンスの構造が変更されています。完全なレスポンス:")
                print(json.dumps(response_data, indent=2, ensure_ascii=False))

                # エラーではなく、フォールバックテキストを使用する
                print("レスポンス形式が不明なため、フォールバックテキストを使用します")
                return extract_rewritten_text("", original_text)

            # デバッグ出力
            print("AIのレスポンス（処理前）:")
            print(raw_text[:100] + "..." if len(raw_text) > 100 else raw_text)

            # AIの応答から実際のリライト結果を抽出
            rewritten_text = extract_rewritten_text(raw_text, original_text)

            # デバッグ出力
            print("抽出後のテキスト:")
            print(
                rewritten_text[:100] + "..."
                if len(rewritten_text) > 100
                else rewritten_text
            )

            # レート制限を回避するための待機
            time.sleep(1)
            return rewritten_text
        elif response.status_code == 429:
            # クォータ超過エラー
            print(
                "APIクォータ超過エラー（429）が発生しました。フォールバックテキストを使用します。"
            )
            return extract_rewritten_text("", original_text)
        else:
            error_msg = f"APIエラー: {response.status_code} - {response.text}"
            print(error_msg)
            # APIエラー時もフォールバックテキストを使用する
            print("APIエラーのため、フォールバックテキストを使用します")
            return extract_rewritten_text("", original_text)

    except Exception as e:
        error_msg = f"リライト処理エラー: {e}"
        print(error_msg)
        # 例外発生時もフォールバックテキストを使用する
        print("例外発生のため、フォールバックテキストを使用します")
        return extract_rewritten_text("", original_text)


def extract_rewritten_text(text, original_text=None):
    """
    AIの応答から実際のリライト結果だけを抽出する
    思考プロセスや英語の分析を除去し、日本語の投稿テキストのみを返す
    特に「羨ましすぎる」「背徳感やばい」などのカジュアルな表現を優先的に抽出する
    """
    import re
    import random

    # ログ出力（デバッグ用）
    print(f"元のAI応答テキスト:\n{text}")

    # マークダウン形式のヘッダーを削除 (# や ## で始まる行)
    text = re.sub(r"^#+ .*$", "", text, flags=re.MULTILINE)

    # マークダウンの強調表示を削除 (**text** や *text*)
    text = re.sub(r"\*\*(.*?)\*\*", r"\1", text)
    text = re.sub(r"\*(.*?)\*", r"\1", text)

    # マークダウン形式のリスト（数字や記号で始まる行）を検出して除去
    text = re.sub(r"^\d+\.\s.*$", "", text, flags=re.MULTILINE)  # 数字リスト
    text = re.sub(r"^[•*\-]\s.*$", "", text, flags=re.MULTILINE)  # 記号リスト

    # コード部分やマークダウンブロックを除去
    text = re.sub(r"```.*?```", "", text, flags=re.DOTALL)

    # 金額に関する表現を削除（例：100円、1,000円、¥500など）
    text = re.sub(r'\d{1,3}(,\d{3})*円', '', text)
    text = re.sub(r'¥\d{1,3}(,\d{3})*', '', text)
    text = re.sub(r'\d+(円|万円|千円)', '', text)
    
    # 金額を含む文章パターンを削除（「〜円で」などの表現）
    text = re.sub(r'[\d,.]+円[でにはが]', '', text)
    text = re.sub(r'コスパ[がは]?[良最高]', '', text)
    
    # 価格に関連する表現を削除
    text = re.sub(r'(お買い得|格安|安い|高い|値段|料金|価格)', '', text)

    # ハッシュタグ候補を用意
    hashtag_candidates = [
        "#官能",
        "#ファンタジー",
        "#背徳感",
        "#ドキドキ",
        "#興奮",
        "#ハーレム",
        "#アダルト",
        "#エロマンガ",
        "#成人向け",
        "#エロ漫画",
        "#おすすめ",
        "#人気",
        "#新刊",
        "#BL",
        "#GL",
        "#TL",
        "#マンガ",
        "#漫画",
        "#コミック",
        "#妄想",
        "#大人の時間",
        "#フェチ",
        "#ギャル",
        "#美少女",
        "#エッチ",
        "#読書",
        "#電子書籍",
        "#濡れる",
        "#おうち時間",
        "#熱い",
    ]

    # タイトルから適切なハッシュタグを選ぶ
    title_keywords = {
        "ハーレム": "#ハーレム",
        "孕ませ": "#大人の時間",
        "絶頂": "#エッチ",
        "搾": "#フェチ",
        "魔物": "#ファンタジー",
        "触手": "#フェチ",
        "女子校生": "#美少女",
        "JK": "#美少女",
        "妹": "#背徳感",
        "姉": "#背徳感",
        "先生": "#背徳感",
        "義理": "#背徳感",
        "学園": "#青春",
        "ファンタジー": "#ファンタジー",
        "ダンジョン": "#ファンタジー",
        "メイド": "#美少女",
        "巨乳": "#おっぱい",
        "爆乳": "#おっぱい",
        "BL": "#BL",
        "GL": "#GL",
        "TL": "#TL",
    }

    # 原文からタイトルを抽出（後で使用）
    title = ""
    if original_text:
        title_match = re.search(r"『(.+?)』", original_text)
        if title_match:
            title = title_match.group(1)

    # タイトルからハッシュタグを選定
    selected_hashtag = None
    if title:
        for keyword, tag in title_keywords.items():
            if keyword in title:
                selected_hashtag = tag
                break

    # タイトルから選べなかった場合は適切なカテゴリまたはランダム選択
    if not selected_hashtag:
        if "BL" in text:
            selected_hashtag = "#BL"
        elif "百合" in text or "GL" in text:
            selected_hashtag = "#GL"
        elif "TL" in text:
            selected_hashtag = "#TL"
        else:
            selected_hashtag = random.choice(hashtag_candidates)

    # AIのテキストから投稿用の文章を選択するロジック
    # 明示的な指示や例の部分を取り除く
    filtered_text = re.sub(r"^(例:|例：|ツイート例|投稿例|以下のような).*$", "", text, flags=re.MULTILINE)
    
    # 日本語テキスト部分を抽出
    japanese_lines = []
    for line in filtered_text.split("\n"):
        # 空行やマークダウン記号のみの行をスキップ
        if not line.strip() or line.strip() in ["---", "***", "___"]:
            continue
        # 明らかな解説や指示は除外
        if re.match(r"^(これは|ここで|このツイート|この投稿|解説：)", line):
            continue
        # 日本語を含む行を抽出
        if re.search(r"[ぁ-んァ-ン一-龥]", line):
            japanese_lines.append(line.strip())
    
    # 日本語テキストが見つからなかった場合のフォールバック
    if not japanese_lines:
        fallback_texts = [
            "これマジでヤバい内容…見た瞬間興奮が止まらない😳",
            "背徳感すごいのに目が離せない…こんなの反則だろ🔥",
            "見てるだけで羨ましすぎる…最高かよ😍",
            "こんな展開待ってた！超興奮する内容でヤバい😳",
            "私の理性が崩壊しそう…こんな濃厚な展開ヤバすぎ💦",
            "これ見た瞬間に我慢できなくなって即買いしたわw🔥",
            "急にこんなシチュエーションになるとか反則すぎる…💦",
        ]
        final_text = random.choice(fallback_texts) + "…！"
    else:
        # 変更点: カジュアルさを優先しつつも、テキストがより残るようにする
        # 一旦全ての日本語テキストを連結（最大3行まで）
        main_text = " ".join(japanese_lines[:3])
        
        # 長すぎる場合は調整（最大120文字）- 以前の60文字から拡大
        if len(main_text) > 120:
            main_text = main_text[:120] + "…"
        
        # 最終的に金額情報が含まれていないか再チェック
        main_text = re.sub(r'\d{1,3}(,\d{3})*円', '', main_text)
        main_text = re.sub(r'¥\d{1,3}(,\d{3})*', '', main_text)
        main_text = re.sub(r'[\d,.]+円[でにはが]', '', main_text)
        
        final_text = main_text

    # 絵文字がなければ追加
    if not re.search(r"[😍😳🔥💦❤️]", final_text):
        emoji_options = ["😳", "😍", "🔥", "💦", "❤️"]
        final_text += random.choice(emoji_options)

    # PRタグとハッシュタグを追加
    final_text = final_text.strip() + "\n\n" + selected_hashtag + " #PR"

    # 最終チェック - 空の投稿や絵文字だけの投稿にならないようにする
    text_content = re.sub(r"[😍😳🔥💦❤️\s]", "", final_text)
    if len(text_content) < 5:  # 実質的な内容が少なすぎる場合
        fallback = (
            "これヤバすぎる内容…興奮が止まらない😳\n\n" + selected_hashtag + " #PR"
        )
        print(
            f"テキスト内容が不足しているため、フォールバックテキストを使用します: {fallback}"
        )
        return fallback

    print(f"最終的に抽出されたテキスト: {final_text}")
    return final_text


def get_next_post_index():
    """
    次に処理すべき投稿のインデックスを取得する
    """
    # 最後に処理した投稿のインデックスを保存するファイルのパス
    index_file = "last_processed_index.txt"

    # ファイルが存在する場合は内容を読み込む
    if os.path.exists(index_file):
        try:
            with open(index_file, "r") as f:
                last_index = int(f.read().strip())
                return last_index + 1  # 次のインデックスを返す
        except:
            return 0  # エラーが発生した場合は最初から
    else:
        return 0  # ファイルがない場合は最初から


def save_processed_index(index):
    """
    処理したインデックスを保存する
    """
    # 最後に処理した投稿のインデックスを保存するファイルのパス
    index_file = "last_processed_index.txt"

    # インデックスをファイルに保存
    with open(index_file, "w") as f:
        f.write(str(index))


def process_manga_data(process_single=True):
    """
    取得した漫画データを整形・選定
    process_single: Trueの場合、次のインデックスの投稿1件だけをリライト
    """
    try:
        # 生データの読み込み
        with open("manga_data_raw.json", "r", encoding="utf-8") as f:
            manga_data = json.load(f)

        print(f"読み込んだデータ: {len(manga_data)}件")

        # データフレームに変換
        df = pd.DataFrame(manga_data)

        print("データフレーム作成完了")

        # 必要なフラグを追加
        df["is_fanza_exclusive"] = df["URL"].apply(
            lambda x: "exclusive" in x or "独占" in str(x) if pd.notna(x) else False
        )

        # 予約商品の除外（date列の日付が未来のもの）
        today = datetime.now().strftime("%Y-%m-%d")

        def is_reservation(row):
            """予約商品かどうかを判定する関数"""
            if "date" in row and pd.notna(row["date"]):
                try:
                    # 日付文字列から日付部分のみを取り出す（時間部分を除外）
                    release_date = str(row["date"]).split(" ")[0]
                    # 現在の日付と比較
                    return release_date > today
                except:
                    # 日付解析エラーの場合は予約商品ではないと判定
                    return False
            # date列がない場合も予約商品ではないと判定
            return False

        df["is_reservation"] = df.apply(is_reservation, axis=1)

        print("予約商品判定完了")

        # 価格を数値に変換する関数（400円未満の除外判定に使用）
        def extract_price(row):
            if (
                "prices" in row
                and isinstance(row["prices"], dict)
                and "price" in row["prices"]
            ):
                try:
                    # 価格から数字だけを取り出す
                    price_str = str(row["prices"]["price"])
                    price_num = int("".join(filter(str.isdigit, price_str)))
                    return price_num
                except:
                    return None
            return None

        # 価格を数値に変換
        df["price_value"] = df.apply(extract_price, axis=1)

        print("価格抽出完了")

        # 条件に合致するかどうかをチェック
        df["is_new"] = df.get("is_new", False)
        df["is_exclusive"] = df["is_fanza_exclusive"]

        # タイトルに「単話」を含むかどうかのフラグを追加
        df["is_tankowa"] = df["title"].apply(
            lambda x: "単話" in str(x) if pd.notna(x) else False
        )

        # タイトルに「ノベル」を含むかどうかのフラグを追加
        df["is_novel"] = df["title"].apply(
            lambda x: "ノベル" in str(x) if pd.notna(x) else False
        )

        print("単話・ノベル判定完了")

        # 予約商品を除外
        df = df[~df["is_reservation"]]

        print(f"予約商品除外後: {len(df)}件")

        # 新着作品から、400円未満と単話とノベルを除外
        selected_manga = df[
            (df["is_new"] == True)
            & ((df["price_value"].isnull()) | (df["price_value"] >= 400))
            & (~df["is_tankowa"])
            & (~df["is_novel"])
        ].copy()

        print(f"条件適合作品絞り込み完了: {len(selected_manga)}件")

        # 以下、選定された作品のみに適用する処理（ランキング情報の表示は残す）
        def format_ranking(row):
            if "ranking_info" not in row:
                return ""

            ranking_info = row["ranking_info"]
            ranking_text = []

            if "daily_rank" in ranking_info and ranking_info["daily_rank"] <= 50:
                ranking_text.append(f"日間{ranking_info['daily_rank']}位")

            if "weekly_rank" in ranking_info and ranking_info["weekly_rank"] <= 100:
                ranking_text.append(f"週間{ranking_info['weekly_rank']}位")

            if "monthly_rank" in ranking_info and ranking_info["monthly_rank"] <= 200:
                ranking_text.append(f"月間{ranking_info['monthly_rank']}位")

            return "・".join(ranking_text)

        selected_manga["ranking_text"] = selected_manga.apply(format_ranking, axis=1)

        # 投稿用テキスト作成
        def create_post_text(row):
            post_parts = []

            # タイトル
            title = row.get("title", "")
            post_parts.append(f"『{title}』")

            # 作者
            if "author" in row:
                author = row["author"]
                if author:
                    post_parts.append(f"作者: {author}")
            elif "artistName" in row:
                author = row["artistName"]
                if author:
                    post_parts.append(f"作者: {author}")

            # 特徴（新着・限定のみ表示）
            features = []
            if row["is_new"]:
                features.append("🆕新着")
            if row["is_exclusive"]:
                features.append("🔒FANZA限定")

            if features:
                post_parts.append("【" + "・".join(features) + "】")

            # ランキング情報があれば表示
            if row["ranking_text"]:
                post_parts.append(f"📊ランキング: {row['ranking_text']}")

            # 価格
            if (
                "prices" in row
                and isinstance(row["prices"], dict)
                and "price" in row["prices"]
            ):
                price = row["prices"]["price"]
                post_parts.append(f"💴価格: {price}円")

            # ハッシュタグを本文の後に配置
            post_parts.append("#PR")

            # URLはpost_textには含めない（JSONの別フィールドとして保存）
            # アフィリエイトURLはリライト時にJSONから直接取得する

            return "\n".join(post_parts)

        # 初期の投稿テキスト作成
        selected_manga["post_text"] = selected_manga.apply(create_post_text, axis=1)

        # 選定結果をJSONで保存
        result = []
        for _, row in selected_manga.iterrows():
            # アフィリエイトURLを構築
            original_url = row.get("affiliateURL", "") or row.get("URL", "")

            # URLがある場合、パラメータを修正
            if original_url:
                # 基本URL部分を抽出 (クエリ文字列の前まで)
                base_url_parts = original_url.split("?")
                base_url = base_url_parts[0]

                # クエリ部分があれば解析
                lurl = ""
                if len(base_url_parts) > 1:
                    query = base_url_parts[1]
                    query_parts = query.split("&")
                    for part in query_parts:
                        if part.startswith("lurl="):
                            lurl = part
                            break

                # アフィリエイトIDが設定されているかチェック
                if not AFFILIATE_ID:
                    print(
                        "警告: 環境変数AFFILIATE_IDが設定されていません。アフィリエイトリンクが作成できません。"
                    )
                    fixed_url = original_url
                else:
                    # 新しいURLを構築
                    if lurl:
                        fixed_url = f"{base_url}?{lurl}&af_id={AFFILIATE_ID}-{AFFILIATE_SITE}&ch={AFFILIATE_CHANNEL}"
                    else:
                        # lurlが見つからない場合は元のURLにパラメータを付ける
                        fixed_url = f"{original_url}"
                        if "?" in fixed_url:
                            fixed_url = (
                                fixed_url.split("?")[0]
                                + "?lurl="
                                + urllib.parse.quote(fixed_url.split("?")[1])
                                + f"&af_id={AFFILIATE_ID}-{AFFILIATE_SITE}&ch={AFFILIATE_CHANNEL}"
                            )
                        else:
                            fixed_url = (
                                fixed_url
                                + f"?af_id={AFFILIATE_ID}-{AFFILIATE_SITE}&ch={AFFILIATE_CHANNEL}"
                            )
            else:
                fixed_url = ""

            # 画像URLは含めない
            item = {
                "title": row.get("title", ""),
                "affiliateURL": fixed_url,
                "post_text": row.get("post_text", ""),
            }
            # authorフィールドが存在する場合のみ追加
            if "author" in row:
                item["author"] = row["author"]
            result.append(item)

        with open("selected_manga.json", "w", encoding="utf-8") as f:
            json.dump(result, f, ensure_ascii=False, indent=2)

        print(f"抽出完了: {len(result)}件の新着作品を抽出しました")

        # 1件だけリライト処理をする場合
        if process_single and result:
            # 次に処理すべきインデックスを取得
            next_index = get_next_post_index()

            # インデックスがリストの範囲外の場合は最初からやり直す
            if next_index >= len(result):
                next_index = 0
                print(f"すべての投稿を処理しました。インデックスを0にリセットします。")

                # インデックスが0にリセットされる場合、データを更新するが、無限ループ防止のためここでは再実行せず終了する
                print(
                    "すべての投稿を処理したため、終了します。次回実行時に新しいデータが取得されます。"
                )
                save_processed_index(next_index)  # リセットされたインデックスを保存
                return True  # ここで処理を終了

            print(
                f"投稿 {next_index+1}/{len(result)} を処理します: {result[next_index]['title']}"
            )

            # 投稿テキストを取得
            post_text = result[next_index]["post_text"]

            # AIでリライト処理
            print("AIによるテキストリライト処理を開始します...")
            rewritten_text = rewrite_text_with_ai(post_text)

            # リライトされたテキストで結果を更新
            result[next_index]["post_text"] = rewritten_text

            # 単一の投稿結果をJSONで保存
            with open("current_post.json", "w", encoding="utf-8") as f:
                json.dump(result[next_index], f, ensure_ascii=False, indent=2)

            # 処理したインデックスを保存
            save_processed_index(next_index)

            print(f"投稿 {next_index+1} のリライト処理完了")
            print(f"リライト結果を current_post.json に保存しました")

        return True

    except Exception as e:
        print(f"データ処理エラー: {e}")
        import traceback

        print(f"詳細: {traceback.format_exc()}")
        return False


if __name__ == "__main__":
    # コマンドライン引数があれば処理
    import sys

    if len(sys.argv) > 1 and sys.argv[1] == "--all":
        # 全件リライトする場合
        process_manga_data(process_single=False)
    else:
        # デフォルトは1件だけリライト
        process_manga_data(process_single=True)
