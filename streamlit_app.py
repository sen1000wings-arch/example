import streamlit as st
import networkx as nx
import matplotlib.pyplot as plt
import pandas as pd
import japanize_matplotlib  # noqa: F401  日本語の文字化け対策

st.set_page_config(
    page_title="マイ・ネットワーク・デザイナー",
    page_icon="🌐",
    layout="wide",
)

# ============================================================
# セッション状態の初期化
# ============================================================
def init_default_graph():
    G = nx.Graph()
    G.add_nodes_from(["R1", "R2", "R3", "R4", "R5"])
    G.add_edge("R1", "R2", weight=3)
    G.add_edge("R2", "R3", weight=1)
    G.add_edge("R1", "R4", weight=6)
    G.add_edge("R4", "R3", weight=2)
    G.add_edge("R3", "R5", weight=4)
    G.add_edge("R4", "R5", weight=1)
    return G


if "G" not in st.session_state:
    st.session_state.G = init_default_graph()
if "disabled" not in st.session_state:
    st.session_state.disabled = set()
if "last_path" not in st.session_state:
    st.session_state.last_path = None
if "pos" not in st.session_state:
    st.session_state.pos = None

G = st.session_state.G


def refresh_layout():
    """ノード構成が変わったときだけレイアウトを再計算し、位置のガタつきを防ぐ"""
    current_nodes = set(G.nodes())
    if st.session_state.pos is None or set(st.session_state.pos.keys()) != current_nodes:
        st.session_state.pos = nx.spring_layout(G, seed=42, k=0.9)


# ============================================================
# サイドバー：ネットワークの動的設計
# ============================================================
st.sidebar.title("🛠️ ネットワーク設計パネル")

# --- ① ノード管理 ---
st.sidebar.header("① ルータ（ノード）")
new_node = st.sidebar.text_input("新しいルータ名", placeholder="例: R6")
if st.sidebar.button("➕ ルータを追加", use_container_width=True):
    if not new_node:
        st.sidebar.warning("ルータ名を入力してください。")
    elif new_node in G.nodes:
        st.sidebar.warning("同名のルータが既に存在します。")
    else:
        G.add_node(new_node)
        st.session_state.pos = None
        st.rerun()

if len(G.nodes) > 0:
    node_to_remove = st.sidebar.selectbox(
        "削除するルータ", options=["(選択なし)"] + sorted(G.nodes)
    )
    if st.sidebar.button("🗑️ ルータを削除", use_container_width=True):
        if node_to_remove != "(選択なし)":
            G.remove_node(node_to_remove)
            st.session_state.disabled.discard(node_to_remove)
            st.session_state.pos = None
            st.rerun()

st.sidebar.divider()

# --- ② エッジ管理 ---
st.sidebar.header("② 回線（エッジ）設定")
if len(G.nodes) >= 2:
    node_a = st.sidebar.selectbox("ルータA", options=sorted(G.nodes), key="edge_a")
    node_b = st.sidebar.selectbox("ルータB", options=sorted(G.nodes), key="edge_b")
    cost = st.sidebar.number_input(
        "通信コスト（重み）", min_value=1, max_value=100, value=1, step=1
    )
    if st.sidebar.button("🔗 接続する", use_container_width=True):
        if node_a == node_b:
            st.sidebar.error("同じルータ同士は接続できません。")
        else:
            G.add_edge(node_a, node_b, weight=int(cost))
            st.rerun()

    if len(G.edges) > 0:
        edge_options = [
            f"{u} - {v} (コスト:{d['weight']})" for u, v, d in G.edges(data=True)
        ]
        edge_to_remove = st.sidebar.selectbox(
            "切断するエッジ", options=["(選択なし)"] + edge_options
        )
        if st.sidebar.button("✂️ 切断する", use_container_width=True):
            if edge_to_remove != "(選択なし)":
                idx = edge_options.index(edge_to_remove)
                u, v, _ = list(G.edges(data=True))[idx]
                G.remove_edge(u, v)
                st.rerun()
else:
    st.sidebar.info("ルータを2つ以上追加すると回線を設定できます。")

st.sidebar.divider()

# --- ③ 故障シミュレーション ---
st.sidebar.header("③ 故障シミュレーション")
faulty = st.sidebar.multiselect(
    "一時的に無効化（故障）させるルータ",
    options=sorted(G.nodes),
    default=sorted(st.session_state.disabled & set(G.nodes)),
)
st.session_state.disabled = set(faulty)

st.sidebar.divider()
if st.sidebar.button("🔄 初期構成にリセット", use_container_width=True):
    st.session_state.G = init_default_graph()
    st.session_state.disabled = set()
    st.session_state.last_path = None
    st.session_state.pos = None
    st.rerun()

refresh_layout()

# ============================================================
# 有効なネットワーク（故障ルータを除いたグラフ）
# ============================================================
active_G = G.copy()
active_G.remove_nodes_from(st.session_state.disabled)

# ============================================================
# グラフ描画関数
# ============================================================
def edge_in_path(u, v, path):
    if not path:
        return False
    for i in range(len(path) - 1):
        if (path[i] == u and path[i + 1] == v) or (path[i] == v and path[i + 1] == u):
            return True
    return False


def draw_network(G, pos, disabled_nodes, highlight_path=None):
    fig, ax = plt.subplots(figsize=(8, 5.5))

    if len(G.nodes) == 0:
        ax.text(0.5, 0.5, "ルータがまだありません", ha="center", va="center")
        ax.axis("off")
        return fig

    edges = list(G.edges(data=True))
    weights = [d["weight"] for _, _, d in edges]
    if weights:
        w_min, w_max = min(weights), max(weights)
    else:
        w_min, w_max = 0, 0

    def scale_width(w):
        if w_max == w_min:
            return 3.0
        return 1.0 + (w - w_min) / (w_max - w_min) * 6.0

    widths = [scale_width(d["weight"]) for _, _, d in edges]
    edge_colors = [
        "#C0392B" if edge_in_path(u, v, highlight_path) else "#B0B0B0"
        for u, v, _ in edges
    ]

    node_colors = [
        "#D9D9D9" if n in disabled_nodes else "#3E6FA8" for n in G.nodes
    ]
    node_edge_colors = [
        "#C0392B" if n in disabled_nodes else "#2C4C70" for n in G.nodes
    ]

    nx.draw_networkx_edges(G, pos, width=widths, edge_color=edge_colors, ax=ax)
    nx.draw_networkx_nodes(
        G,
        pos,
        node_color=node_colors,
        edgecolors=node_edge_colors,
        linewidths=2,
        node_size=1400,
        ax=ax,
    )
    for n, (x, y) in pos.items():
        ax.text(
            x, y, n, ha="center", va="center",
            fontsize=10, fontweight="bold",
            color="#8A8A8A" if n in disabled_nodes else "white",
        )

    edge_labels = {(u, v): d["weight"] for u, v, d in edges}
    nx.draw_networkx_edge_labels(
        G, pos, edge_labels=edge_labels, font_size=9,
        font_color="#333333", ax=ax,
        bbox=dict(boxstyle="round,pad=0.1", fc="white", ec="none", alpha=0.7),
    )

    for n in disabled_nodes:
        if n in pos:
            x, y = pos[n]
            ax.text(x, y - 0.14, "故障中", ha="center", va="center",
                     fontsize=8, color="#C0392B", fontweight="bold")

    ax.axis("off")
    fig.tight_layout()
    return fig


# ============================================================
# メイン画面
# ============================================================
st.title("🌐 マイ・ネットワーク・デザイナー")
st.caption("情報Ⅰ「ネットワークの仕組み」学習教材 ― グラフ理論とルーティングの論理を体験しよう")

st.markdown(
    """
コンピュータネットワークは、数学的には **「グラフ」** として表現できます。
ルータやコンピュータは **頂点（ノード）**、それらをつなぐ通信回線は **辺（エッジ）** に対応し、
回線の速度や混雑度は **重み（コスト）** として数値化されます。
このアプリでは、自分でネットワークを設計しながら、その裏側にあるデータ構造とルーティングの仕組みを確認します。
"""
)

st.divider()

# --- ① ネットワーク構成図 ---
st.header("① ネットワーク構成図")
col_graph, col_note = st.columns([2, 1])
with col_graph:
    fig = draw_network(G, st.session_state.pos, st.session_state.disabled, st.session_state.last_path)
    st.pyplot(fig)
with col_note:
    st.markdown("**読み方**")
    st.markdown(
        "- 丸（ノード）＝ ルータ\n"
        "- 線（エッジ）＝ 通信回線\n"
        "- 線の太さ ＝ 通信コストの大きさ（太いほどコストが高い）\n"
        "- 線上の数字 ＝ 重み（コスト）\n"
        "- 灰色のノード ＝ 故障中のルータ\n"
        "- 赤い線 ＝ ③で計算した最小コスト経路"
    )

st.divider()

# --- ② 内部データ表示 ---
st.header("② 内部データ：ネットワークの「地図」")
st.markdown(
    "コンピュータは図形そのものではなく、数値の表や辞書としてネットワークを記憶しています。"
    "同じネットワークが、コンピュータの中ではどのようなデータになっているかを見てみましょう。"
)

nodes_sorted = sorted(G.nodes)
col_matrix, col_list = st.columns(2)

with col_matrix:
    st.subheader("隣接行列（Adjacency Matrix）")
    if nodes_sorted:
        matrix = pd.DataFrame(0, index=nodes_sorted, columns=nodes_sorted)
        for u, v, d in G.edges(data=True):
            matrix.loc[u, v] = d["weight"]
            matrix.loc[v, u] = d["weight"]
        st.dataframe(matrix, use_container_width=True)
    else:
        st.info("ルータがありません。")
    st.caption(
        "行と列が交わるマスの数値は、2つのルータ間の通信コストを表します。"
        "0は「直接は接続されていない」ことを意味します。"
    )

with col_list:
    st.subheader("隣接リスト（Python辞書形式）")
    adjacency_dict = {
        n: {nbr: G[n][nbr]["weight"] for nbr in G.neighbors(n)} for n in nodes_sorted
    }
    st.code(repr(adjacency_dict), language="python")
    st.caption(
        "ルータは実際には、このような「キー：自分の名前」「値：接続先と回線コスト」の"
        "組み合わせ（辞書型データ）でネットワークの地図を記憶し、経路計算に使っています。"
    )

st.divider()

# --- ③ ルーティング・シミュレーション ---
st.header("③ ルーティング・シミュレーション（ダイクストラ法）")
st.markdown(
    "ルーティングとは、送信元から宛先までの経路のうち、**コストの合計が最小になる経路**を選ぶことです。"
    "「経由するルータの数（ホップ数）が少ない道」と「合計コストが最小の道」は、必ずしも一致しません。"
)

active_nodes = sorted(active_G.nodes)
if len(active_nodes) >= 2:
    c1, c2, c3 = st.columns([1, 1, 1])
    start = c1.selectbox("スタート", active_nodes, key="start_node")
    goal_index = 1 if len(active_nodes) > 1 else 0
    goal = c2.selectbox("ゴール", active_nodes, index=goal_index, key="goal_node")
    calc = c3.button("🧭 最小コスト経路を計算する", type="primary", use_container_width=True)

    if calc:
        if start == goal:
            st.warning("スタートとゴールが同じルータです。")
            st.session_state.last_path = None
        else:
            try:
                path = nx.dijkstra_path(active_G, start, goal, weight="weight")
                cost = nx.dijkstra_path_length(active_G, start, goal, weight="weight")
                st.session_state.last_path = path
                st.success(f"最小コスト経路： {' → '.join(path)} （合計コスト： {cost}）")

                hop_path = nx.shortest_path(active_G, start, goal)
                hop_cost = nx.path_weight(active_G, hop_path, weight="weight") if len(hop_path) > 1 else 0

                if hop_path != path:
                    st.info(
                        f"もし「経由するルータの数（ホップ数）」だけを基準に選ぶと "
                        f"{' → '.join(hop_path)}（ホップ数優先・コスト合計 {hop_cost}）という経路になりますが、"
                        f"実際のルーティングではコストの合計が最小の経路が選ばれます。"
                    )
                else:
                    st.info("この構成では、ホップ数最小の経路とコスト最小の経路がたまたま一致しています。")
            except nx.NetworkXNoPath:
                st.error(
                    "経路が見つかりません。ネットワークが分断されているか、"
                    "故障中のルータが通り道をふさいでいる可能性があります。"
                )
                st.session_state.last_path = None
    st.caption("計算結果は上の①ネットワーク構成図に赤線で反映されます。")
else:
    st.warning("経路計算を行うには、故障していない有効なルータが2つ以上必要です。")

st.divider()

# --- ④ トラブルシューティング実習 ---
st.header("④ トラブルシューティング実習：ルータ故障のシミュレーション")
st.markdown(
    "サイドバーの「③ 故障シミュレーション」で任意のルータを選択すると、そのルータが"
    "ネットワークから一時的に取り除かれます。実際のネットワークで機器が故障した状況を再現し、"
    "ルーティングがどのように**自動的に迂回路を再計算するか**を確認しましょう。"
)

if st.session_state.disabled:
    st.error(f"現在「故障中」のルータ： {', '.join(sorted(st.session_state.disabled))}")

    active_adjacency = {
        n: {nbr: active_G[n][nbr]["weight"] for nbr in active_G.neighbors(n)}
        for n in sorted(active_G.nodes)
    }

    colA, colB = st.columns(2)
    with colA:
        st.markdown("**故障前の隣接リスト（全体）**")
        st.code(repr(adjacency_dict), language="python")
    with colB:
        st.markdown("**故障後の隣接リスト（有効なネットワークのみ）**")
        st.code(repr(active_adjacency), language="python")

    st.caption(
        "故障したルータと、それにつながっていた回線（エッジ）が地図から消えていることが分かります。"
        "ルーティングは、この新しい地図をもとに、③のダイクストラ法で自動的に迂回路（別ルート）を"
        "再計算します。上のスタート・ゴールを選び直して、経路がどう変わるか試してみましょう。"
    )
else:
    st.info(
        "現在、故障中のルータはありません。サイドバーの「③ 故障シミュレーション」で"
        "ルータを選択すると、ここに影響が表示されます。"
    )

st.divider()
with st.expander("📘 用語のまとめ（情報Ⅰ）"):
    st.markdown(
        """
- **グラフ**：頂点（ノード）と辺（エッジ）から構成されるデータ構造。ネットワークの構造を表すのに使われる。
- **頂点（ノード）**：ネットワーク上の機器（ここではルータ）。
- **辺（エッジ）**：ノード同士をつなぐ通信回線。
- **重み（コスト）**：回線の通信速度や混雑度などを表す数値。値が大きいほど「通りにくい」経路とする。
- **隣接行列**：どのノード同士が接続されているかを、行と列の表（マトリックス）で表したもの。
- **隣接リスト**：各ノードについて、直接つながっている相手とコストを一覧にしたデータ（辞書型など）。
- **ダイクストラ法**：スタートからゴールまでの、合計コストが最小となる経路を求めるアルゴリズム。
- **ルーティング**：ネットワーク上でデータを送る際に、最適な経路を選択する仕組み・処理のこと。
"""
    )
