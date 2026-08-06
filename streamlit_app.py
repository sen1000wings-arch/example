# -*- coding: utf-8 -*-
"""
POSシステムを学ぶ授業用Webアプリ
対象: 情報Ⅰ(4章「情報通信ネットワークとデータの活用」/ 情報システムとそのサービス)
      情報Ⅱ(「情報システムとプログラミング」)

このアプリは外部API・ネットワーク通信を一切使用せず、
すべての処理をアプリ内(ローカル)で完結させています。
"""

import random
import datetime

import numpy as np
import pandas as pd
import streamlit as st

# ============================================================
# 基本設定
# ============================================================
st.set_page_config(
    page_title="POSシステムを学ぼう",
    page_icon="🛒",
    layout="wide",
    initial_sidebar_state="expanded",
)

ITEM_MASTER = {
    "おにぎり(鮭)": 150,
    "おにぎり(梅)": 140,
    "サンドイッチ": 280,
    "お茶(500ml)": 150,
    "コーヒー": 180,
    "からあげ弁当": 480,
    "肉まん": 150,
    "アイスクリーム": 200,
    "雑誌": 500,
    "電池(単三4本)": 400,
}

WEATHERS = ["晴れ", "曇り", "雨", "雪"]
TIME_SLOTS = ["早朝(5-8時)", "午前(8-11時)", "昼(11-14時)", "午後(14-17時)",
              "夕方(17-20時)", "夜(20-23時)", "深夜(23-5時)"]
AGE_GROUPS = ["10代以下", "20代", "30代", "40代", "50代", "60代以上"]
GENDERS = ["男性", "女性", "回答しない"]


# ============================================================
# 共通UI部品(HTML/CSSでボックス&矢印の図解を描く)
# ============================================================
def box_html(title, subtitle="", color="#e3f2fd", border="#1976d2"):
    sub = f'<div style="font-size:12px;color:#333;margin-top:6px;line-height:1.4;">{subtitle}</div>' if subtitle else ""
    return f"""
    <div style="background:{color};border:2px solid {border};border-radius:12px;
                padding:14px 12px;text-align:center;min-width:130px;max-width:190px;
                flex:1;margin:6px;display:flex;flex-direction:column;justify-content:center;">
        <div style="font-weight:700;font-size:15px;color:#0d47a1;">{title}</div>
        {sub}
    </div>"""


def arrow_html(label=""):
    lab = f'<div style="font-size:10.5px;color:#555;max-width:90px;text-align:center;">{label}</div>' if label else ""
    return f"""
    <div style="display:flex;flex-direction:column;align-items:center;justify-content:center;
                min-width:46px;margin:6px 0;">
        <div style="font-size:26px;color:#1976d2;line-height:1;">→</div>
        {lab}
    </div>"""


def down_arrow_html(label=""):
    lab = f'<div style="font-size:10.5px;color:#555;">{label}</div>' if label else ""
    return f"""
    <div style="display:flex;flex-direction:column;align-items:center;justify-content:center;margin:2px 0;">
        <div style="font-size:22px;color:#1976d2;line-height:1;">↓</div>
        {lab}
    </div>"""


def flow_row(parts):
    html = ('<div style="display:flex;align-items:center;flex-wrap:wrap;'
            'justify-content:center;margin:18px 0;">')
    html += "".join(parts)
    html += "</div>"
    st.markdown(html, unsafe_allow_html=True)


def section_title(emoji, text, desc=None):
    st.markdown(f"## {emoji} {text}")
    if desc:
        st.caption(desc)


# ============================================================
# データ生成(実データではなく学習用の疑似データ)
# ============================================================
@st.cache_data
def generate_synthetic_sales(days=30, seed=42):
    rng = np.random.default_rng(seed)
    dates = pd.date_range("2025-06-01", periods=days, freq="D")

    slot_traffic = {
        "早朝(5-8時)": 0.5, "午前(8-11時)": 1.0, "昼(11-14時)": 2.2,
        "午後(14-17時)": 1.1, "夕方(17-20時)": 1.9, "夜(20-23時)": 1.0,
        "深夜(23-5時)": 0.3,
    }
    base_item_weight = {k: 1.0 for k in ITEM_MASTER}

    records = []
    tx_id = 1
    for d in dates:
        weather = rng.choice(WEATHERS, p=[0.45, 0.25, 0.25, 0.05])

        weight = dict(base_item_weight)
        if weather == "晴れ":
            weight["アイスクリーム"] *= 3.0
            weight["お茶(500ml)"] *= 1.6
        elif weather == "雨":
            weight["からあげ弁当"] *= 1.6
            weight["肉まん"] *= 1.5
            weight["コーヒー"] *= 1.4
            weight["アイスクリーム"] *= 0.3
        elif weather == "雪":
            weight["肉まん"] *= 2.2
            weight["コーヒー"] *= 1.6
            weight["アイスクリーム"] *= 0.1
        else:  # 曇り
            weight["コーヒー"] *= 1.1

        items = list(weight.keys())
        probs = np.array([weight[i] for i in items])
        probs = probs / probs.sum()

        for slot, mult in slot_traffic.items():
            n_tx = rng.poisson(lam=14 * mult)
            for _ in range(n_tx):
                item = rng.choice(items, p=probs)
                qty = rng.choice([1, 1, 1, 2, 2, 3], p=[0.45, 0.2, 0.15, 0.1, 0.06, 0.04])
                age = rng.choice(AGE_GROUPS)
                gender = rng.choice(GENDERS, p=[0.46, 0.46, 0.08])
                price = ITEM_MASTER[item]
                records.append({
                    "取引ID": tx_id,
                    "日付": d.date(),
                    "商品": item,
                    "数量": int(qty),
                    "金額": int(price * qty),
                    "天候": weather,
                    "時間帯": slot,
                    "客層(年代)": age,
                    "客層(性別)": gender,
                })
                tx_id += 1
    return pd.DataFrame(records)


# ============================================================
# セッション状態の初期化
# ============================================================
if "cart" not in st.session_state:
    st.session_state.cart = []
if "sales_log" not in st.session_state:
    st.session_state.sales_log = []
if "next_tx_id" not in st.session_state:
    st.session_state.next_tx_id = 1


# ============================================================
# ページ: ホーム
# ============================================================
def page_home():
    st.markdown(
        """
        <div style="background:linear-gradient(90deg,#1976d2,#42a5f5);padding:28px 24px;
                    border-radius:16px;color:white;margin-bottom:20px;">
            <div style="font-size:30px;font-weight:800;">🛒 POSシステムを学ぼう</div>
            <div style="font-size:15px;margin-top:6px;opacity:0.95;">
                身近な「レジ」の裏側にある情報システムのしくみと、データ活用の価値を体験的に学ぶ教材
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    col1, col2 = st.columns([3, 2])
    with col1:
        st.markdown("### 📘 授業のねらい")
        st.write(
            "身近な情報システムである POS システムのしくみを理解し、"
            "収集されたデータが店舗経営の効率化や私たちの利便性向上にどう役立てられているか"
            "(データの蓄積・管理・分析)を考察します。"
        )

        st.markdown("### 🎯 対象単元")
        st.markdown(
            """
            - **情報Ⅰ**: 第4章「情報通信ネットワークとデータの活用」 (3) 情報システムとそのサービス
            - **情報Ⅱ**: (4) 情報システムとプログラミング
            """
        )

        st.markdown("### 🗺️ このアプリの使い方")
        st.markdown(
            """
            サイドバーのメニューから、以下の順番で進めていくことをおすすめします。

            1. **① 身近な事例** - コンビニのレジで集められているデータを考える
            2. **② POSのしくみ** - POSレジとPOSシステムの違い・データの流れを理解する
            3. **③ データの活用** - 蓄積されたデータが経営判断にどう活かされるかを分析体験
            4. **🧪 ミニPOS体験** - 自分でレジ打ちをしてデータが記録される過程を体験する
            5. **🚀 発展学習** - 事例研究・DFD・状態遷移図・システム開発の流れ
            6. **📝 確認クイズ** - 学んだ内容の理解度チェック
            """
        )
    with col2:
        st.markdown("### 💡 まとめの視点")
        st.info(
            "POSシステムは単なる「会計の道具」ではなく、\n\n"
            "**「情報をネットワークで共有し、分析することで、"
            "新たな社会的な価値を生み出すしくみ」**\n\n"
            "として捉えることが、情報に関する科学的な見方・考え方を養う上で大切です。"
        )
        st.markdown("### 🔑 キーワード")
        st.markdown(
            "`POSレジ` `POSシステム` `バーコード` `クラウド型POS` `客層ボタン` "
            "`ビッグデータ` `在庫最適化` `データフロー図(DFD)` `状態遷移図`"
        )


# ============================================================
# ページ①: 身近な事例からの課題発見
# ============================================================
DATA_ITEMS = [
    ("購入日時", True, "レシートに印字される基本情報で、時間帯ごとの売れ筋分析に使われます。"),
    ("天候(晴れ・雨など)", True, "クラウド型POSでは気象データと連携し、天候による売上の違いを分析することがあります。"),
    ("客の性別・年代(客層ボタン)", True, "レジ担当者が押す『客層ボタン』により、匿名の統計情報として収集されます。"),
    ("店舗名・レジ番号", True, "どの店舗のどのレジで販売されたかを記録し、店舗ごとの比較に使われます。"),
    ("支払い方法(現金・カード等)", True, "キャッシュレス化の進捗や客単価の分析に利用されます。"),
    ("ポイントカードの会員ID", True, "会員の場合は購入履歴を継続的に分析でき、非会員は匿名データとして扱われます。"),
    ("一緒に買われた商品の組み合わせ", True, "「バスケット分析」と呼ばれ、商品の配置やおすすめ商品の検討に使われます。"),
    ("客の氏名", False, "通常のPOSレジでは氏名は入力されません。氏名が必要な場合は会員登録データと別に管理されます。"),
    ("客の自宅住所", False, "POSシステム単体では住所は記録されません。通販・配送サービスと連携した場合のみ扱われます。"),
    ("クレジットカードの番号そのもの", False, "セキュリティ上、カード番号自体は店舗のPOSには保存されず、決済代行会社側でトークン化されて処理されます。"),
]


def page1():
    section_title("①", "身近な事例からの課題発見",
                   "コンビニのレジで、商品の代金以外にどのようなデータが集められているか考えてみよう")

    st.write(
        "レジでは「商品の代金」以外にも、実は様々なデータが記録されています。"
        "下のリストから、**実際にPOSシステムで収集されていると思うもの** を選んでみましょう。"
    )

    options = [d[0] for d in DATA_ITEMS]
    selected = st.multiselect("集められていると思うデータを選んでください", options)

    if st.button("✅ 答え合わせをする", type="primary"):
        st.session_state["p1_checked"] = True

    if st.session_state.get("p1_checked"):
        st.markdown("---")
        st.markdown("### 📋 答え合わせ")
        correct_count = 0
        total_correct = sum(1 for d in DATA_ITEMS if d[1])
        for name, is_collected, explanation in DATA_ITEMS:
            user_picked = name in selected
            if user_picked == is_collected:
                if is_collected:
                    correct_count += 1
                icon = "✅" if is_collected else "🚫"
                result = "正解！" if user_picked else "(未選択でしたが、実際には収集されません)"
            else:
                icon = "⚠️"
                result = "選択が違います"
            color = "#e8f5e9" if user_picked == is_collected else "#fff3e0"
            collected_tag = "収集される" if is_collected else "収集されない(通常は)"
            st.markdown(
                f"""<div style="background:{color};border-radius:8px;padding:10px 14px;margin-bottom:6px;">
                <b>{icon} {name}</b> ー <i>{collected_tag}</i><br>
                <span style="font-size:13px;color:#444;">{explanation}</span>
                </div>""",
                unsafe_allow_html=True,
            )
        st.success(f"収集される項目のうち {correct_count}/{total_correct} 個を正しく選べました。")

        st.markdown("### 🧭 ポイント")
        st.info(
            "POSシステムが集めるのは、**氏名や住所のような個人を直接特定する情報ではなく**、"
            "購入日時・天候・客層(年代/性別)・商品の組み合わせなど、"
            "**匿名化された「行動データ」が中心** である点がポイントです。"
            "こうしたデータの積み重ねが、次の展開で学ぶ「ビッグデータ分析」につながっていきます。"
        )


# ============================================================
# ページ②: POSシステムのしくみ
# ============================================================
def page2():
    section_title("②", "POSシステムのしくみと構成要素の理解",
                   "バーコードスキャンから売上データの記録までの流れを見てみよう")

    st.markdown("### 🔄 データの流れ(概要)")
    flow_row([
        box_html("お客様", "商品をレジへ", "#fff3e0", "#ef6c00"),
        arrow_html("商品を渡す"),
        box_html("POSレジ端末", "バーコードをスキャン", "#e3f2fd", "#1976d2"),
        arrow_html("売上データを送信"),
        box_html("店舗サーバー<br>／クラウド", "データを蓄積", "#e8f5e9", "#2e7d32"),
        arrow_html("集計・分析"),
        box_html("本部の分析<br>システム", "経営判断に活用", "#fce4ec", "#ad1457"),
    ])

    st.markdown("### 🏪 POSレジ と POSシステムの違い")
    c1, c2 = st.columns(2)
    with c1:
        st.markdown(
            """
            <div style="background:#e3f2fd;border-radius:12px;padding:16px;height:100%;">
            <b>📟 POSレジ (Point of Sale レジ)</b><br><br>
            店頭にある<b>端末そのもの</b>。<br>
            バーコードの読み取り、金額の計算、レシートの発行など、
            <b>会計の実務</b>を行う道具。
            </div>
            """, unsafe_allow_html=True,
        )
    with c2:
        st.markdown(
            """
            <div style="background:#e8f5e9;border-radius:12px;padding:16px;height:100%;">
            <b>🖥️ POSシステム (POS全体のしくみ)</b><br><br>
            レジ端末だけでなく、<b>データを送受信するネットワーク</b>、
            蓄積する<b>サーバー</b>、分析する<b>ソフトウェア</b>までを含む<br>
            <b>「情報システム」全体</b>を指す。
            </div>
            """, unsafe_allow_html=True,
        )

    st.markdown("### ☁️ POSの種類の変化")
    df_type = pd.DataFrame({
        "種類": ["従来型(オンプレミス)POS", "タブレット型POS", "クラウド型POS"],
        "特徴": [
            "店舗内の専用サーバーでデータを管理。初期費用が高く、変更に時間がかかる。",
            "汎用タブレット+専用アプリで動作。低コストで導入しやすい。",
            "データをインターネット上のサーバーで一元管理。複数店舗の状況をリアルタイムに把握できる。",
        ],
        "データの保存場所": ["店舗内サーバー", "店舗内 or クラウド", "インターネット上(クラウド)"],
    })
    st.table(df_type)

    st.info(
        "近年は、複数店舗の売上をリアルタイムで本部が把握できる**クラウド型POS**や、"
        "初期費用を抑えられる**タブレット型POS**の導入が広がっています。"
    )


# ============================================================
# ページ③: データの活用
# ============================================================
def page3():
    section_title("③", "データの蓄積・分析による価値の創造",
                   "集まった膨大なデータ(ビッグデータ)は、お店のどんな工夫に活かせるだろうか？")

    df = generate_synthetic_sales()

    st.caption(
        "※以下は学習用に生成した**疑似データ**(30日分・約1万件)です。実在の店舗データではありません。"
    )

    tab1, tab2, tab3 = st.tabs(["📦 在庫の最適化", "📈 販売戦略(天候・時間帯)", "👥 客層分析"])

    # ---- 在庫最適化 ----
    with tab1:
        st.markdown("#### 売れ筋を把握し、品切れ・食品ロスを防ぐ")
        item = st.selectbox("商品を選択", list(ITEM_MASTER.keys()), key="stock_item")
        item_df = df[df["商品"] == item]
        daily = item_df.groupby("日付")["数量"].sum()
        avg_daily = daily.mean() if len(daily) else 0

        st.bar_chart(daily, height=250)
        st.write(f"**{item}** の1日あたり平均販売数: **{avg_daily:.1f} 個**")

        st.markdown("##### 🧮 発注点シミュレーター")
        col1, col2, col3 = st.columns(3)
        with col1:
            current_stock = st.number_input("現在の在庫数", min_value=0, value=int(avg_daily * 2), step=1)
        with col2:
            lead_time = st.slider("発注リードタイム(日)", 1, 7, 2)
        with col3:
            safety_factor = st.slider("安全係数(多めに持つ日数)", 0, 5, 1)

        reorder_point = avg_daily * lead_time + avg_daily * safety_factor
        st.metric("発注点(この在庫数を下回ったら発注)", f"{reorder_point:.1f} 個")

        if current_stock < reorder_point:
            st.error(
                f"⚠️ 現在庫({current_stock}個)が発注点を下回っています。"
                f"品切れを防ぐため、そろそろ発注が必要です。"
            )
        else:
            st.success(f"✅ 現在庫({current_stock}個)は十分です。まだ発注しなくて大丈夫そうです。")

    # ---- 天候・時間帯 ----
    with tab2:
        st.markdown("#### 天候や時間帯による売上の傾向を分析する")

        weather_sel = st.multiselect("天候で絞り込み(複数選択可)", WEATHERS, default=WEATHERS)
        filtered = df[df["天候"].isin(weather_sel)] if weather_sel else df

        colA, colB = st.columns(2)
        with colA:
            st.markdown("**天候別 商品販売数**")
            pivot_w = filtered.pivot_table(index="商品", columns="天候", values="数量", aggfunc="sum", fill_value=0)
            st.bar_chart(pivot_w, height=300)
        with colB:
            st.markdown("**時間帯別 来店(取引)件数**")
            slot_count = filtered.groupby("時間帯")["取引ID"].nunique().reindex(TIME_SLOTS)
            st.bar_chart(slot_count, height=300)

        st.info(
            "天候によって売れる商品が変化していることが読み取れます。"
            "たとえば雨の日は温かい商品(からあげ弁当・肉まん・コーヒー)が伸びる、"
            "といった傾向を踏まえて、**棚の並べ方やキャンペーンの計画**に活かすことができます。"
        )

        st.markdown("##### ⏰ 忙しい時間帯からスタッフ配置を考える")
        busy_slot = slot_count.idxmax() if len(slot_count) else "-"
        st.write(f"取引件数が最も多い時間帯: **{busy_slot}**")
        st.caption("忙しい時間帯を事前に予測できれば、スタッフの配置(勤怠管理)を最適化できます。")

    # ---- 客層分析 ----
    with tab3:
        st.markdown("#### 客層(年代・性別)による購買傾向")
        colA, colB = st.columns(2)
        with colA:
            age_count = df.groupby("客層(年代)")["数量"].sum().reindex(AGE_GROUPS)
            st.markdown("**年代別 購入数**")
            st.bar_chart(age_count, height=280)
        with colB:
            gender_item = df.pivot_table(index="商品", columns="客層(性別)", values="数量", aggfunc="sum", fill_value=0)
            st.markdown("**性別 × 商品 の購入数**")
            st.bar_chart(gender_item, height=280)

        st.info(
            "客層ボタンによって集計された匿名の統計データから、"
            "どの年代・性別にどの商品が支持されているかを把握し、"
            "品ぞろえや陳列を調整する判断材料にできます。"
        )

    with st.expander("📄 元データ(疑似データ)を確認する"):
        st.dataframe(df, use_container_width=True, height=300)


# ============================================================
# ページ: ミニPOS体験
# ============================================================
def page_mini_pos():
    section_title("🧪", "ミニPOS体験",
                   "実際にレジ打ちをして、データが記録されていく過程を体験してみよう")

    st.write(
        "自分がレジ担当者になったつもりで、商品をスキャン(選択)してカートに入れ、"
        "会計してみましょう。会計するたびに「取引データ」が蓄積されていきます。"
    )

    st.markdown("### 🧾 来店情報を入力(客層ボタン・環境情報)")
    c1, c2, c3, c4 = st.columns(4)
    with c1:
        weather = st.selectbox("天候", WEATHERS)
    with c2:
        time_slot = st.selectbox("時間帯", TIME_SLOTS, index=2)
    with c3:
        age = st.selectbox("客層(年代ボタン)", AGE_GROUPS)
    with c4:
        gender = st.selectbox("客層(性別ボタン)", GENDERS)

    member = st.checkbox("💳 ポイントカード会員として会計する")

    st.markdown("### 📷 商品をスキャン")
    c1, c2, c3 = st.columns([3, 1, 1])
    with c1:
        item = st.selectbox("商品を選ぶ(バーコードスキャンの代わり)", list(ITEM_MASTER.keys()))
    with c2:
        qty = st.number_input("数量", min_value=1, value=1, step=1)
    with c3:
        st.write("")
        st.write("")
        if st.button("🛒 カートに追加", use_container_width=True):
            st.session_state.cart.append({"商品": item, "数量": qty, "単価": ITEM_MASTER[item]})

    st.markdown("### 🛍️ 現在のカート")
    if st.session_state.cart:
        cart_df = pd.DataFrame(st.session_state.cart)
        cart_df["小計"] = cart_df["数量"] * cart_df["単価"]
        st.dataframe(cart_df, use_container_width=True, hide_index=True)
        total = int(cart_df["小計"].sum())
        st.markdown(f"### 💰 合計: {total:,} 円")

        colA, colB = st.columns(2)
        with colA:
            if st.button("🧹 カートを空にする"):
                st.session_state.cart = []
                st.rerun()
        with colB:
            if st.button("✅ 会計する", type="primary"):
                points_earned = total // 100 if member else 0
                tx_id = st.session_state.next_tx_id
                st.session_state.next_tx_id += 1
                now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                for row in st.session_state.cart:
                    st.session_state.sales_log.append({
                        "取引ID": tx_id,
                        "記録時刻": now,
                        "商品": row["商品"],
                        "数量": row["数量"],
                        "金額": row["数量"] * row["単価"],
                        "天候": weather,
                        "時間帯": time_slot,
                        "客層(年代)": age,
                        "客層(性別)": gender,
                        "会員": "会員" if member else "非会員",
                        "獲得ポイント": points_earned if row is st.session_state.cart[0] else 0,
                    })
                st.session_state.cart = []
                st.success(
                    f"会計が完了しました！ 合計 {total:,} 円"
                    + (f"(獲得ポイント: {points_earned}pt)" if member else "")
                )
                st.rerun()
    else:
        st.caption("カートは空です。商品を選んで「カートに追加」を押してください。")

    st.markdown("---")
    st.markdown("### 📊 蓄積された取引データ(POSに記録された履歴)")
    if st.session_state.sales_log:
        log_df = pd.DataFrame(st.session_state.sales_log)
        st.dataframe(log_df, use_container_width=True, height=250)

        colA, colB = st.columns(2)
        with colA:
            st.markdown("**商品別 販売数**")
            st.bar_chart(log_df.groupby("商品")["数量"].sum())
        with colB:
            st.markdown("**時間帯別 売上金額**")
            st.bar_chart(log_df.groupby("時間帯")["金額"].sum())

        st.info(
            "このように、レジでの1回1回の会計が積み重なることで、"
            "**「どの商品が」「いつ」「どんな客層に」売れたか** というデータが自動的に蓄積されていきます。"
            "これこそがPOSシステムの本質的な役割です。"
        )
        if st.button("🗑️ 蓄積データをリセットする"):
            st.session_state.sales_log = []
            st.rerun()
    else:
        st.caption("まだ取引データがありません。上で会計を行うとここに記録されます。")


# ============================================================
# ページ: 発展学習
# ============================================================
def page_advanced():
    section_title("🚀", "発展的な学習(実習・探究)",
                   "事例研究・システムのモデル化・プログラミングとの連携")

    tab1, tab2, tab3 = st.tabs(["🏢 事例研究", "🧩 システムのモデル化", "💻 開発工程の体験"])

    # --- 事例研究 ---
    with tab1:
        st.markdown("#### 大手飲食チェーンのPOSリプレイス事例")
        st.write(
            "大手飲食チェーンなどでは、従来型の他社製POSシステムから、"
            "タブレットなどを用いた**モバイルPOS**へ切り替える動きが進んでいます。"
            "こうした「リプレイス(入れ替え)」によって、次のような効果が期待できます。"
        )
        st.markdown(
            """
            - 複数店舗の売上をクラウド上でリアルタイムに一元管理できる
            - 専用のサーバー機器が不要になり、**運用の手間とコストを削減**できる
            - メニュー変更や価格改定を、本部から一括で素早く反映できる
            - 売上データと在庫データを連携させ、発注業務を効率化できる
            """
        )
        st.info(
            "このような取り組みは、単に「レジを新しくする」だけでなく、"
            "**業務プロセス全体を情報システムで最適化するDX(デジタルトランスフォーメーション)** "
            "の一例として捉えることができます。"
        )
        st.markdown("##### 📝 考えてみよう")
        st.text_area(
            "自分の身近なお店(コンビニ・飲食店など)で、POSシステムがどのように"
            "業務効率化に役立っていそうか、気づいたことを書いてみましょう。",
            height=100,
            key="case_study_note",
        )

    # --- モデル化 ---
    with tab2:
        st.markdown("#### データフロー図(DFD)でPOSシステムを図解する")
        st.caption("○:プロセス(処理) 　▭:外部実体 　▭▭(二重線):データストア(保存場所)")

        flow_row([
            box_html("お客様", "商品を持ってくる", "#fff3e0", "#ef6c00"),
            arrow_html("商品情報"),
            box_html("① 会計処理", "バーコードを読み取り<br>金額を計算する", "#e3f2fd", "#1976d2"),
        ])
        flow_row([
            box_html("商品マスタ<br>(データストア)", "商品名・価格の一覧", "#f3e5f5", "#6a1b9a"),
            arrow_html("価格を照会"),
            box_html("① 会計処理", "(上と同じプロセス)", "#e3f2fd", "#1976d2"),
            arrow_html("売上を記録"),
            box_html("売上データ<br>(データストア)", "いつ・何が・いくつ売れたか", "#e8f5e9", "#2e7d32"),
        ])
        flow_row([
            box_html("会員データベース<br>(データストア)", "ポイント・購入履歴", "#fce4ec", "#ad1457"),
            arrow_html("会員情報を照会/更新"),
            box_html("① 会計処理", "(上と同じプロセス)", "#e3f2fd", "#1976d2"),
            arrow_html("集計データを送信"),
            box_html("② 分析システム", "売上の集計・分析を行う", "#fff9c4", "#f9a825"),
        ])

        st.markdown("#### 状態遷移図で1回の取引の流れを図解する")
        flow_row([
            box_html("待機中", "次のお客様を待つ", "#eceff1", "#455a64"),
            arrow_html("商品を受け取る"),
            box_html("商品スキャン中", "バーコードを<br>読み取っている", "#e3f2fd", "#1976d2"),
            arrow_html("スキャン完了"),
            box_html("会計処理中", "金額を計算し<br>支払いを受ける", "#fff3e0", "#ef6c00"),
            arrow_html("支払い完了"),
            box_html("取引完了", "レシートを発行し<br>データを送信", "#e8f5e9", "#2e7d32"),
        ])
        st.caption("「取引完了」の後は、再び「待機中」の状態に戻ります。")

    # --- 開発工程 ---
    with tab3:
        st.markdown("#### 小規模な注文・精算システムの開発工程を体験する")
        st.write(
            "実際のシステム開発では、次のような工程を経てプログラムが作られます。"
            "「🧪 ミニPOS体験」で操作した簡易レジも、この考え方に沿って設計されています。"
        )

        steps = [
            ("① 要求分析", "どんな機能が必要か整理する", "例:バーコードで商品を特定したい／合計金額を自動計算したい／客層データを記録したい"),
            ("② 設計", "データの流れや画面構成を考える", "例:商品マスタ(商品名・価格)をどう持つか、会計処理の手順をどう組むか"),
            ("③ 実装(プログラミング)", "実際にプログラムを書く", "例:商品を選ぶ→カートに追加→合計を計算→会計処理を行う、という一連の処理を作成"),
            ("④ テスト", "正しく動くか確認する", "例:数量0で追加したらどうなるか？合計金額の計算は正しいか？などを確認"),
        ]
        for i, (title, sub, ex) in enumerate(steps):
            st.markdown(
                f"""<div style="background:#f5f5f5;border-left:5px solid #1976d2;border-radius:6px;
                padding:10px 14px;margin-bottom:8px;">
                <b>{title}</b> ー {sub}<br>
                <span style="font-size:13px;color:#555;">{ex}</span>
                </div>""",
                unsafe_allow_html=True,
            )
            if i < len(steps) - 1:
                st.markdown(
                    '<div style="text-align:center;color:#1976d2;font-size:20px;">↓</div>',
                    unsafe_allow_html=True,
                )

        st.markdown("##### 📝 演習")
        st.write(
            "「🧪 ミニPOS体験」のページを、上の4つの工程に当てはめて振り返ってみましょう。"
            "たとえば、「客層ボタンを追加する」機能を新たに作るとしたら、"
            "①〜④のそれぞれで何をする必要があるか、考えてみましょう。"
        )
        st.text_area("あなたの考えを書いてみよう", height=120, key="dev_process_note")


# ============================================================
# ページ: 確認クイズ
# ============================================================
QUIZ = [
    {
        "q": "「POS」の略称として正しいものはどれか。",
        "options": ["Point of Sale", "Point of Service", "Personal Operating System", "Point of Stock"],
        "answer": 0,
        "explanation": "POSは Point of Sale(販売時点)の略で、商品が販売された時点の情報を記録するしくみです。",
    },
    {
        "q": "「POSレジ」と「POSシステム」の関係として最も適切な説明はどれか。",
        "options": [
            "POSレジとPOSシステムはまったく同じものである",
            "POSレジは店頭の端末、POSシステムはデータの管理・分析まで含む仕組み全体である",
            "POSシステムは店頭の端末のことで、POSレジはネットワーク全体を指す",
            "POSレジは会員カードのことである",
        ],
        "answer": 1,
        "explanation": "POSレジは会計を行う「端末」、POSシステムはネットワークやサーバーを含む「しくみ全体」を指します。",
    },
    {
        "q": "クラウド型POSの利点として最も適切なものはどれか。",
        "options": [
            "インターネットに接続しなくても使える",
            "複数店舗のデータを本部がリアルタイムに一元管理しやすい",
            "個人情報を必ず保存できる",
            "バーコードを使わなくても会計できる",
        ],
        "answer": 1,
        "explanation": "クラウド型POSはデータをインターネット上のサーバーで管理するため、複数店舗の状況をリアルタイムに把握しやすいという利点があります。",
    },
    {
        "q": "POSデータを使った「在庫の最適化」の説明として適切なものはどれか。",
        "options": [
            "売れ筋商品を把握し、品切れや過剰在庫(食品ロス)を防ぐこと",
            "従業員の給料を自動的に決定すること",
            "客の氏名と住所を蓄積すること",
            "レジの色を変えること",
        ],
        "answer": 0,
        "explanation": "売上データから売れ筋・売れ残りを分析し、発注量を調整することで在庫を最適化できます。",
    },
    {
        "q": "POSデータの活用例として適切でないものはどれか。",
        "options": [
            "天候や時間帯による売上傾向を分析し、キャンペーンを計画する",
            "忙しい時間帯を予測し、スタッフの配置を最適化する",
            "一緒に買われやすい商品を把握し、陳列を工夫する",
            "収集したデータをもとに、来店していない客に無断で商品を配送する",
        ],
        "answer": 3,
        "explanation": "POSデータの活用は、あくまで店舗運営の効率化や利便性向上のためのものであり、個人の同意なく行動を決めつけて一方的にサービスを行うことは適切ではありません。",
    },
    {
        "q": "データフロー図(DFD)についての説明として正しいものはどれか。",
        "options": [
            "プログラムのソースコードそのものを表す図である",
            "システム内における情報(データ)の流れを図示したものである",
            "店舗の内装レイアウトを表す図である",
            "従業員の勤務シフトを表す図である",
        ],
        "answer": 1,
        "explanation": "DFD(データフロー図)は、システム内で情報がどこからどこへ流れるかを図示したもので、システム設計の基本的な手法の一つです。",
    },
]


def page_quiz():
    section_title("📝", "確認クイズ", "学んだ内容を振り返ってみよう")

    answers = []
    for i, q in enumerate(QUIZ):
        st.markdown(f"**Q{i + 1}. {q['q']}**")
        ans = st.radio("選択肢", q["options"], key=f"quiz_{i}", label_visibility="collapsed", index=None)
        answers.append(ans)
        st.markdown("")

    if st.button("🖊️ 採点する", type="primary"):
        if any(a is None for a in answers):
            st.warning("すべての問題に回答してから採点してください。")
        else:
            score = 0
            st.markdown("---")
            st.markdown("### 結果")
            for i, q in enumerate(QUIZ):
                correct_text = q["options"][q["answer"]]
                is_correct = answers[i] == correct_text
                if is_correct:
                    score += 1
                icon = "✅" if is_correct else "❌"
                bg = "#e8f5e9" if is_correct else "#ffebee"
                st.markdown(
                    f"""<div style="background:{bg};border-radius:8px;padding:10px 14px;margin-bottom:8px;">
                    <b>{icon} Q{i+1}. {q['q']}</b><br>
                    あなたの回答: {answers[i]}<br>
                    正解: {correct_text}<br>
                    <span style="font-size:13px;color:#444;">{q['explanation']}</span>
                    </div>""",
                    unsafe_allow_html=True,
                )
            st.markdown(f"## 📊 得点: {score} / {len(QUIZ)}")
            if score == len(QUIZ):
                st.balloons()
                st.success("満点です！POSシステムのしくみをよく理解できています。")
            elif score >= len(QUIZ) * 0.6:
                st.info("よくできました。復習したい箇所をもう一度確認してみましょう。")
            else:
                st.warning("①〜③のページをもう一度見直してから、再チャレンジしてみましょう。")


# ============================================================
# サイドバー & ルーティング
# ============================================================
def main():
    st.sidebar.markdown("## 🛒 POSシステム学習アプリ")
    st.sidebar.caption("情報Ⅰ・情報Ⅱ 対応教材")

    page = st.sidebar.radio(
        "ページを選択",
        [
            "🏠 ホーム",
            "① 身近な事例",
            "② POSのしくみ",
            "③ データの活用",
            "🧪 ミニPOS体験",
            "🚀 発展学習",
            "📝 確認クイズ",
        ],
    )

    st.sidebar.markdown("---")
    st.sidebar.markdown("#### ℹ️ このアプリについて")
    st.sidebar.caption(
        "本アプリはすべてローカルで動作し、外部API・ネットワーク通信は使用していません。"
        "データはすべて学習用に生成した疑似データです。"
    )

    if page == "🏠 ホーム":
        page_home()
    elif page == "① 身近な事例":
        page1()
    elif page == "② POSのしくみ":
        page2()
    elif page == "③ データの活用":
        page3()
    elif page == "🧪 ミニPOS体験":
        page_mini_pos()
    elif page == "🚀 発展学習":
        page_advanced()
    elif page == "📝 確認クイズ":
        page_quiz()


if __name__ == "__main__":
    main()