import random
import re

import streamlit as st

st.set_page_config(page_title="しりとりゲーム", page_icon="🔤", layout="centered")

# ============================================================
# コンピュータの語彙（すべて「ん」で終わらない、ひらがなの単語）
# ============================================================
WORD_LIST = [
    "あめ", "あさ", "あき", "あお", "あし", "あに", "あね", "あくび", "あひる", "あたま",
    "いぬ", "いえ", "いす", "いろ", "いか", "いちご", "いわ", "いと",
    "うみ", "うし", "うさぎ", "うた", "うで", "うちわ", "うわぎ",
    "えき", "えんぴつ", "えだ", "えがお",
    "おかし", "おふろ", "おに", "おか", "おと", "おんがく", "おかね", "おとうと",
    "かめ", "かさ", "かに", "かぜ", "かみ", "かお", "かえる", "かがみ",
    "きつね", "きのこ", "きって", "きもの", "きゅうり", "きしゃ", "きいろ",
    "くつ", "くも", "くじら", "くるま", "くり", "くすり",
    "けむり", "けしごむ", "けいと", "けんか", "げた",
    "こおり", "こども", "こま", "こえ", "こおろぎ", "ごりら",
    "さかな", "さくら", "さる", "さとう", "さいふ", "さんかく", "ざる",
    "しお", "しか", "しま", "しろ", "しっぽ", "じてんしゃ",
    "すいか", "すし", "すずめ", "すいとう", "すな",
    "せみ", "せかい", "せんせい", "せなか", "ぜんまい",
    "そら", "そうじき", "そば", "そうじ", "ぞう",
    "たまご", "たいこ", "たぬき", "たこ", "たいよう", "たけ", "だんご",
    "ちず", "ちから", "ちきゅう", "ちょうちょ",
    "つき", "つくえ", "つばめ", "つゆ", "つの",
    "てがみ", "てぶくろ", "てんき", "てんとうむし", "でんしゃ",
    "とけい", "とり", "とうふ", "とかげ", "とんぼ", "どんぐり",
    "なつ", "なし", "なべ", "なみだ", "なわとび",
    "にじ", "にわとり", "にく",
    "ぬいぐるみ", "ぬま",
    "ねこ", "ねずみ",
    "のはら", "のり", "のうか", "のみもの",
    "はな", "はし", "はと", "はさみ", "はれ", "はくちょう",
    "ひこうき", "ひまわり", "ひつじ", "ひかり", "ひも",
    "ふね", "ふくろう", "ふゆ", "ふで",
    "へび", "へや", "へいわ",
    "ほし", "ほうき", "ほたる", "ほお", "ぼうし",
    "まど", "まつり", "まめ", "まくら", "まほう",
    "みず", "みち", "みみ", "みどり",
    "むし", "むぎ", "むら", "むかし",
    "め", "めがね", "めだか",
    "もり", "もも", "もち", "もくば",
    "やま", "やさい", "やね", "やぎ",
    "ゆき", "ゆび", "ゆめ", "ゆびわ",
    "よる", "ようふく", "よこ",
    "らくだ", "らっぱ",
    "りんご", "りす", "りゆう",
    "るす",
    "れいぞうこ", "れきし",
    "ろうそく", "ろば",
    "わに", "わた", "わりばし",
    "がっこう", "がか", "ぎんこう", "ぎゅうにゅう", "ぐんて",
    "ばら", "びわ", "ぶた", "べんとう", "ぱんだ",
]

# 小さい文字 → 対応する大きい文字（しりとりの継続判定に使う）
SMALL_TO_BIG = {
    "ぁ": "あ", "ぃ": "い", "ぅ": "う", "ぇ": "え", "ぉ": "お",
    "っ": "つ",
    "ゃ": "や", "ゅ": "ゆ", "ょ": "よ",
    "ゎ": "わ",
}

HIRAGANA_PATTERN = re.compile(r"^[ぁ-ん]+$")


def normalize_kana(char: str) -> str:
    """小さい文字を対応する大きい文字に変換する"""
    return SMALL_TO_BIG.get(char, char)


def is_valid_hiragana(word: str) -> bool:
    return bool(HIRAGANA_PATTERN.fullmatch(word))


# ============================================================
# セッション状態の初期化
# ============================================================
def reset_game():
    st.session_state.history = []       # [(speaker, word), ...]
    st.session_state.used_words = set()
    st.session_state.required_start = None
    st.session_state.game_over = False
    st.session_state.winner = None
    st.session_state.message = None      # (kind, text)


if "history" not in st.session_state:
    reset_game()


# ============================================================
# ゲームロジック
# ============================================================
def computer_turn():
    required = st.session_state.required_start
    candidates = [
        w for w in WORD_LIST
        if normalize_kana(w[0]) == required and w not in st.session_state.used_words
    ]
    if not candidates:
        st.session_state.game_over = True
        st.session_state.winner = "player"
        st.session_state.message = ("success", "コンピュータは言葉に詰まってしまいました…あなたの勝ちです！🎉")
        return

    word = random.choice(candidates)
    st.session_state.used_words.add(word)
    st.session_state.history.append(("コンピュータ", word))
    st.session_state.required_start = normalize_kana(word[-1])


def process_player_word(raw_word: str):
    word = raw_word.strip()

    if word == "":
        st.session_state.message = ("warning", "言葉を入力してください。")
        return

    if not is_valid_hiragana(word):
        st.session_state.message = ("error", "ひらがなだけを使って入力してください。")
        return

    if word[0] == "ん":
        st.session_state.message = ("error", "「ん」で始まる言葉は使えません。")
        return

    if word in st.session_state.used_words:
        st.session_state.message = ("error", f"「{word}」はすでに使われています。別の言葉を入力してください。")
        return

    if st.session_state.required_start is not None:
        if normalize_kana(word[0]) != st.session_state.required_start:
            st.session_state.message = (
                "error",
                f"「{st.session_state.required_start}」から始まる言葉を入力してください。",
            )
            return

    # ここまで来たら受理
    st.session_state.used_words.add(word)
    st.session_state.history.append(("あなた", word))
    st.session_state.message = None

    if normalize_kana(word[-1]) == "ん":
        st.session_state.game_over = True
        st.session_state.winner = "computer"
        st.session_state.message = ("error", f"「{word}」は「ん」で終わっています。あなたの負けです…")
        return

    st.session_state.required_start = normalize_kana(word[-1])
    computer_turn()


# ============================================================
# サイドバー
# ============================================================
with st.sidebar:
    st.header("📖 遊び方")
    st.markdown(
        """
- **ひらがなだけ**で、単語を入力します。
- 前の単語の**最後の文字**から始まる言葉をつなげます。
  （小さい文字「ゃ・っ」などは、大きい文字とみなします）
- 一度使った言葉はもう一度使えません。
- **「ん」で終わる言葉を言うと負け**です。
- コンピュータが言葉に詰まったら、あなたの勝ちです！
"""
    )
    st.divider()
    st.header("📊 状況")
    st.metric("これまでに出た言葉", len(st.session_state.history))
    if st.session_state.used_words:
        with st.expander("使った言葉一覧"):
            st.write("、".join(sorted(st.session_state.used_words)))
    st.divider()
    st.button("🔄 最初からやり直す", on_click=reset_game, use_container_width=True)


# ============================================================
# メイン画面
# ============================================================
st.title("🔤 しりとりゲーム")
st.caption("コンピュータと日本語しりとり対決！ ひらがなだけで言葉をつなげよう。")

# --- これまでのやり取りをチャット形式で表示 ---
if not st.session_state.history:
    st.info("好きな言葉（ひらがな）を入力して、しりとりを始めましょう！")
else:
    for speaker, word in st.session_state.history:
        role = "user" if speaker == "あなた" else "assistant"
        avatar = "🧑" if speaker == "あなた" else "🤖"
        with st.chat_message(role, avatar=avatar):
            st.write(f"**{word}**")

# --- ステータスメッセージ ---
if st.session_state.message:
    kind, text = st.session_state.message
    getattr(st, kind)(text)

st.divider()

# --- 入力フォーム or 終了画面 ---
if st.session_state.game_over:
    if st.session_state.winner == "player":
        st.balloons()
        st.success("🏆 あなたの勝ちです！おめでとうございます！")
    else:
        st.error("😢 あなたの負けです。もう一度挑戦してみましょう！")
    st.button("🔄 もう一度あそぶ", type="primary", on_click=reset_game, use_container_width=True)
else:
    if st.session_state.required_start:
        prompt = f"「{st.session_state.required_start}」から始まる言葉を入力してください"
    else:
        prompt = "最初の言葉（ひらがな）を入力してください"

    with st.form("word_form", clear_on_submit=True):
        user_word = st.text_input(prompt, key="word_input")
        col1, col2 = st.columns([2, 1])
        submitted = col1.form_submit_button("送信する", type="primary", use_container_width=True)
        give_up = col2.form_submit_button("ギブアップ", use_container_width=True)

    if submitted:
        process_player_word(user_word)
        st.rerun()

    if give_up:
        st.session_state.game_over = True
        st.session_state.winner = "computer"
        st.session_state.message = ("info", "ギブアップしました。また挑戦してくださいね！")
        st.rerun()