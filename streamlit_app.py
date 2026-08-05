import streamlit as st
import networkx as nx
import matplotlib.pyplot as plt
import pandas as pd
import japanize_matplotlib  # 日本語文字化け対策

st.set_page_config(
    page_title="ネットワークのルーティングとグラフ理論 - 情報Ⅰ",
    page_icon="🌐",
    layout="wide",
)

# ============================================================
# セッション状態の初期化
# ============================================================
def init_default_graph():
    """初期の5台のルータ(A, B, C, D, E)と接続・コストを設定"""
    G = nx.Graph()
    nodes = ["A", "B", "C", "D", "E"]
    G.add_nodes_from(nodes)
    edges = [
        ("A", "B", 3),
        ("B", "C", 1),
        ("A", "D", 6),
        ("D", "C", 2),
        ("C", "E", 4),
        ("D", "E", 1),
    ]
    for u, v, w in edges:
        G.add_edge(u, v, weight=w)
    return G

if "G" not in st.session_state:
    st.session_state.G = init_default_graph()

if "disabled_nodes" not in st.session_state:
    st.session_state.disabled_nodes = set()

if "pos" not in st.session_state:
    st.session_state.pos = None

G = st.session_state.G

def refresh_layout():
    """描画時にノードの位置が固定されるようにレイアウト情報を保持"""
    current_nodes = set(G.nodes())
    if st.session_state.pos is None or set(st.session_state.pos.keys()) != current_nodes:
        st.session_state.pos = nx.spring_layout(G, seed=42, k=0.9)

refresh_layout()

# ============================================================
# グラフ描画共通関数
# ============================================================
def edge_in_path(u, v, path):
    """指定されたエッジ(u, v)が最短経路に含まれているか判定"""
    if not path or len(path) < 2:
        return False
    for i in range(len(path) - 1):
        if (path[i] == u and path[i + 1] == v) or (path[i] == v and path[i + 1] == u):
            return True
    return False

def draw_network(graph, pos, disabled_nodes=None, highlight_path=None):
    if disabled_nodes is None:
        disabled_nodes = set()
    
    fig, ax = plt.subplots(figsize=(7, 4.5))

    if len(graph.nodes) == 0:
        ax.text(0.5, 0.5, "ルータが存在しません", ha="center", va="center")
        ax.axis("off")
        return fig

    edges = list(graph.edges(data=True))
    weights = [d.get("weight", 1) for _, _, d in edges]
    w_min, w_max = (min(weights), max(weights)) if weights else (1, 1)

    # コストに応じて太さを可変設定
    def scale_width(w):
        if w_max == w_min:
            return 3.0
        return 1.5 + (w - w_min) / (w_max - w_min) * 4.5

    widths = [scale_width(d.get("weight", 1)) for _, _, d in edges]
    
    # 経路に含まれるエッジを赤色、通常を灰色
    edge_colors = [
        "#E74C3C" if edge_in_path(u, v, highlight_path) else "#BDC3C7"
        for u, v, _ in edges
    ]

    # 故障ノードはグレーアウト
    node_colors = [
        "#BDC3C7" if n in disabled_nodes else "#3498DB" for n in graph.nodes
    ]
    node_edge_colors = [
        "#E74C3C" if n in disabled_nodes else "#2980B9" for n in graph.nodes
    ]

    nx.draw_networkx_edges(graph, pos, width=widths, edge_color=edge_colors, ax=ax)
    nx.draw_networkx_nodes(
        graph,
        pos,
        node_color=node_colors,
        edgecolors=node_edge_colors,
        linewidths=2,
        node_size=1200,
        ax=ax,
    )

    # ノードラベル描画
    for n, (x, y) in pos.items():
        if n in graph.nodes:
            ax.text(
                x, y, n, ha="center", va="center",
                fontsize=11, fontweight="bold",
                color="#7F8C8D" if n in disabled_nodes else "white",
            )

    # エッジ（回線コスト）のラベル描画
    edge_labels = {(u, v): f"コスト:{d.get('weight', 1)}" for u, v, d in edges}
    nx.draw_networkx_edge_labels(
        graph, pos, edge_labels=edge_labels, font_size=8,
        font_color="#2C3E50", ax=ax,
        bbox=dict(boxstyle="round,pad=0.2", fc="white", ec="none", alpha=0.85),
    )

    # 故障ノードの警告表示
    for n in disabled_nodes:
        if n in pos:
            x, y = pos[n]
            ax.text(x, y - 0.15, "⚠️ 故障中", ha="center", va="center",
                    fontsize=9, color="#E74C3C", fontweight="bold")

    ax.axis("off")
    fig.tight_layout()
    return fig

# ============================================================
# サイドバーナビゲーション
# ============================================================
st.sidebar.title("🌐 ナビゲーション")
page = st.sidebar.radio(
    "学習項目を選択してください：",
    [
        "1. ルーティングの基本",
        "2. グラフとデータ表現",
        "3. 最短経路シミュレーション",
        "4. トラブルシューティング演習",
    ],
)

st.sidebar.divider()
if st.sidebar.button("🔄 ネットワーク構成をリセット", use_container_width=True):
    st.session_state.G = init_default_graph()
    st.session_state.disabled_nodes = set()
    st.session_state.pos = None
    st.rerun()


# ============================================================
# セクション 1: ルーティングの基本
# ============================================================
if page == "1. ルーティングの基本":
    st.title("1. ルーティングの基本")
    st.caption("情報Ⅰ：ネットワークの仕組みとデータ通信")

    st.markdown("""
    ### 💡 ルーティング（経路制御）とは？
    インターネットでWebページを見たり動画を再生したりするとき、データは**「パケット」**と呼ばれる小さなデータのかたまりに細分化されて送られます。
    
    このパケットが、広いネットワークの網目をくぐり抜けて目的地まで迷わずに届くよう、最適な道順を案内・中継する仕組みを**ルーティング（経路制御）**と呼びます。
    また、その中継を行う通信機器を**ルータ（Router）**と呼びます。
    """)

    st.info("""
    **💡 情報Ⅰで押さえる重要ポイント：**
    - **経由する数（ホップ数）が少ないルートが最善とは限らない：** ルータの数が少なくても、回線が細かったり混雑していたりすると時間がかかります。
    - **通信コスト（重み）：** 回線の速度や遅延などを総合して数値化したものを「コスト」と呼び、**合計コストが最小となるルート**を選んで送信します。
    """)

    col1, col2 = st.columns([1, 1])
    with col1:
        st.markdown("""
        #### 📐 ネットワークと数学の「グラフ理論」
        ネットワークの構造は、数学の**「グラフ理論」**を使って整理できます。
        - **ノード（頂点）：** ルータやPCなどの通信機器
        - **エッジ（辺）：** ノード同士を結ぶ通信回線
        - **重み（コスト）：** 通信の遅延・速度を表す数値
        """)
    with col2:
        fig = draw_network(G, st.session_state.pos)
        st.pyplot(fig)


# ============================================================
# セクション 2: グラフとデータ表現
# ============================================================
elif page == "2. グラフとデータ表現":
    st.title("2. グラフとデータ表現")
    st.markdown("""
    コンピュータは図形を人間のようには理解できません。そのため、ネットワークのつながりを**数字の表やリスト**に変換して記憶・計算しています。
    下のチェックボックスでルータ間の接続（エッジ）をON/OFFして、データ表現がどう変わるか見てみましょう！
    """)

    nodes = sorted(list(G.nodes()))

    st.subheader("⚙️ 回線（エッジ）の切り替え")
    st.write("ルータ同士の接続（エッジ）の有無を切り替えられます：")

    # エッジ切り替え用チェックボックス（3列で配置）
    cols = st.columns(3)
    all_possible_edges = [(nodes[i], nodes[j]) for i in range(len(nodes)) for j in range(i + 1, len(nodes))]

    # 初期描画用デフォルトコストマップ
    default_weights = {
        ("A", "B"): 3, ("B", "C"): 1, ("A", "D"): 6,
        ("D", "C"): 2, ("C", "E"): 4, ("D", "E"): 1
    }

    for idx, (u, v) in enumerate(all_possible_edges):
        col = cols[idx % 3]
        has_edge = G.has_edge(u, v)
        new_state = col.checkbox(f"接続 {u} - {v}", value=has_edge, key=f"edge_{u}_{v}")
        
        if new_state and not has_edge:
            w = default_weights.get((u, v), default_weights.get((v, u), 2))
            G.add_edge(u, v, weight=w)
            st.rerun()
        elif not new_state and has_edge:
            G.remove_edge(u, v)
            st.rerun()

    st.divider()

    col_left, col_right = st.columns([1, 1])

    with col_left:
        st.subheader("🌐 ネットワーク図")
        fig = draw_network(G, st.session_state.pos)
        st.pyplot(fig)

    with col_right:
        st.subheader("📊 隣接行列（Adjacency Matrix）とは？")
        st.markdown("行と列に各ノードを並べ、**接続している箇所のコスト**（繋がっていない場合は `0`）を入れた2次元の表です。")
        
        matrix_df = pd.DataFrame(0, index=nodes, columns=nodes)
        for u, v, d in G.edges(data=True):
            matrix_df.loc[u, v] = d.get("weight", 1)
            matrix_df.loc[v, u] = d.get("weight", 1)
        st.dataframe(matrix_df, use_container_width=True)

        st.subheader("📖 隣接リスト（Adjacency List）とは？")
        st.markdown("各ノードが「自分から直結しているノードとコスト」の一覧を持つ形式（Pythonの辞書構造）です。")
        adj_dict = {
            n: {nbr: G[n][nbr].get("weight", 1) for nbr in G.neighbors(n)}
            for n in nodes
        }
        st.code(repr(adj_dict), language="python")


# ============================================================
# セクション 3: 最短経路シミュレーション
# ============================================================
elif page == "3. 最短経路シミュレーション":
    st.title("3. 最短経路シミュレーション")
    st.markdown("""
    ルータは**「ダイクストラ法（Dijkstra's Algorithm）」**などのアルゴリズムを使って、スタートからゴールまでの**通信コストの合計が最小になる経路**を瞬時に計算します。
    スタートとゴールを選んで、実際に最小コストルートを計算させてみましょう！
    """)

    nodes = sorted(list(G.nodes()))
    if len(nodes) >= 2:
        c1, c2 = st.columns(2)
        start = c1.selectbox("スタート（送信元ルータ）", nodes, index=0)
        goal = c2.selectbox("ゴール（宛先ルータ）", nodes, index=len(nodes) - 1)

        path = None
        total_cost = None

        if start == goal:
            st.warning("スタートとゴールには異なるルータを選んでください。")
        else:
            try:
                # ダイクストラ法で最短経路・コストの計算
                path = nx.dijkstra_path(G, start, goal, weight="weight")
                total_cost = nx.dijkstra_path_length(G, start, goal, weight="weight")
                
                st.success(f"🎯 **算出された最短経路 (ダイクストラ法):** {' ➔ '.join(path)} （合計通信コスト: **{total_cost}**）")
            except nx.NetworkXNoPath:
                st.error("❌ 送信元から宛先へ到達できるルートが存在しません（回線が切断されています）。")

        fig = draw_network(G, st.session_state.pos, highlight_path=path)
        st.pyplot(fig)
    else:
        st.warning("ルータが少なすぎるため計算できません。")


# ============================================================
# セクション 4: トラブルシューティング演習
# ============================================================
elif page == "4. トラブルシューティング演習":
    st.title("4. トラブルシューティング演習")
    st.markdown("""
    実際のネットワーク環境では、雷や機器の老朽化などで特定のルータが突然故障することがあります。
    ネットワークは障害を検知すると、**自動的に迂回（バックアップ）ルートを再計算**して通信を維持します。
    """)

    st.subheader("🚨 故障シミュレーション")
    target_node = "C"

    is_c_disabled = target_node in st.session_state.disabled_nodes
    c_toggle = st.checkbox(
        f"🔴 ルータ {target_node} を故障（ネットワークから離脱）させる",
        value=is_c_disabled
    )

    if c_toggle and not is_c_disabled:
        st.session_state.disabled_nodes.add(target_node)
        st.rerun()
    elif not c_toggle and is_c_disabled:
        st.session_state.disabled_nodes.remove(target_node)
        st.rerun()

    # 故障ノードを除外した有効なグラフの複製
    active_G = G.copy()
    active_G.remove_nodes_from(st.session_state.disabled_nodes)
    nodes_active = sorted(list(active_G.nodes()))

    col1, col2 = st.columns([1, 1])

    with col1:
        disabled_str = ', '.join(sorted(st.session_state.disabled_nodes)) if st.session_state.disabled_nodes else 'なし'
        st.markdown(f"#### ネットワーク状態（故障中ルータ: `{disabled_str}`）")
        
        path = None
        if "A" in nodes_active and "E" in nodes_active:
            try:
                path = nx.dijkstra_path(active_G, "A", "E", weight="weight")
            except nx.NetworkXNoPath:
                path = None

        fig = draw_network(G, st.session_state.pos, disabled_nodes=st.session_state.disabled_nodes, highlight_path=path)
        st.pyplot(fig)

    with col2:
        st.markdown("#### 経路の変化の観察 (A ➔ E)")
        if "A" in nodes_active and "E" in nodes_active:
            if path:
                cost = nx.dijkstra_path_length(active_G, "A", "E", weight="weight")
                if "C" in st.session_state.disabled_nodes:
                    st.warning(f"⚠️ **ルータCが故障したため、迂回路が選ばれました：**\n\n**{' ➔ '.join(path)}** （合計コスト: {cost}）")
                else:
                    st.info(f"通常ルート：\n\n**{' ➔ '.join(path)}** （合計コスト: {cost}）")
            else:
                st.error("❌ 経路が断絶されました！ A から E に到達できません。")
        else:
            st.warning("送信元または宛先のルータが停止しているため通信できません。")

        st.markdown("""
        **🎓 演習のまとめ：**
        1. **通常時：** コストの低いルータCを経由する `A ➔ B ➔ C ➔ E` (合計コスト: 8) または `A ➔ D ➔ C ➔ E` (合計コスト: 12) が使われます。
        2. **ルータC故障時：** Cを通るルートが途絶えますが、自動的に迂回路 `A ➔ D ➔ E` (合計コスト: 7) に切り替わります。
        """)