import streamlit as st
import pandas as pd
import heapq

st.set_page_config(
    page_title="ネットワークのルーティングとグラフ理論 - 情報Ⅰ",
    page_icon="🌐",
    layout="wide",
)

# ============================================================
# 自作グラフクラス & ダイクストラ法アルゴリズム (networkx非使用)
# ============================================================
class CustomGraph:
    def __init__(self, nodes):
        self.nodes = list(nodes)
        self.edges = {}  # (u, v): weight

    def add_edge(self, u, v, weight):
        if u in self.nodes and v in self.nodes:
            self.edges[(u, v)] = weight
            self.edges[(v, u)] = weight

    def remove_edge(self, u, v):
        self.edges.pop((u, v), None)
        self.edges.pop((v, u), None)

    def has_edge(self, u, v):
        return (u, v) in self.edges

    def get_neighbors(self, node):
        neighbors = {}
        for (u, v), w in self.edges.items():
            if u == node:
                neighbors[v] = w
        return neighbors

def dijkstra(graph, start, goal, disabled_nodes=None):
    """自作ダイクストラ法による最短経路探索"""
    if disabled_nodes is None:
        disabled_nodes = set()

    if start in disabled_nodes or goal in disabled_nodes:
        return None, float('inf')

    distances = {node: float('inf') for node in graph.nodes if node not in disabled_nodes}
    distances[start] = 0
    previous_nodes = {node: None for node in graph.nodes if node not in disabled_nodes}
    pq = [(0, start)]

    while pq:
        current_distance, current_node = heapq.heappop(pq)

        if current_distance > distances[current_node]:
            continue

        if current_node == goal:
            break

        for neighbor, weight in graph.get_neighbors(current_node).items():
            if neighbor in disabled_nodes:
                continue

            distance = current_distance + weight
            if distance < distances[neighbor]:
                distances[neighbor] = distance
                previous_nodes[neighbor] = current_node
                heapq.heappush(pq, (distance, neighbor))

    # 経路の復元
    path = []
    curr = goal
    while curr is not None:
        path.append(curr)
        curr = previous_nodes.get(curr)

    path.reverse()

    if path and path[0] == start:
        return path, distances[goal]
    else:
        return None, float('inf')


# ============================================================
# セッション状態の初期化
# ============================================================
def init_default_graph():
    nodes = ["A", "B", "C", "D", "E"]
    G = CustomGraph(nodes)
    default_edges = [
        ("A", "B", 3),
        ("B", "C", 1),
        ("A", "D", 6),
        ("D", "C", 2),
        ("C", "E", 4),
        ("D", "E", 1),
    ]
    for u, v, w in default_edges:
        G.add_edge(u, v, w)
    return G

if "G" not in st.session_state:
    st.session_state.G = init_default_graph()

if "disabled_nodes" not in st.session_state:
    st.session_state.disabled_nodes = set()

G = st.session_state.G


# ============================================================
# Graphviz によるネットワーク描画関数 (matplotlib/networkx非使用)
# ============================================================
def edge_in_path(u, v, path):
    if not path or len(path) < 2:
        return False
    for i in range(len(path) - 1):
        if (path[i] == u and path[i + 1] == v) or (path[i] == v and path[i + 1] == u):
            return True
    return False

def generate_dot_graph(graph, disabled_nodes=None, highlight_path=None):
    """DOT言語形式でGraphviz用のグラフ定義を作成"""
    if disabled_nodes is None:
        disabled_nodes = set()

    dot_lines = [
        'graph G {',
        '  layout=neato;',
        '  overlap=false;',
        '  node [shape=circle, style=filled, fontname="sans-serif", fontcolor=white, width=0.8, fixedsize=true];',
        '  edge [fontname="sans-serif", fontsize=10, penwidth=2];'
    ]

    # 固定座標の配置定義（レイアウト崩れ防止）
    positions = {
        "A": "0,1!",
        "B": "1.5,2!",
        "C": "3,1!",
        "D": "1.5,0!",
        "E": "4.5,1!"
    }

    # 1. ノードの描画設定
    for node in graph.nodes:
        pos = positions.get(node, "")
        pos_attr = f'pos="{pos}"' if pos else ""

        if node in disabled_nodes:
            label = f"{node}\\n(故障中)"
            dot_lines.append(
                f'  "{node}" [label="{label}", fillcolor="#BDC3C7", color="#E74C3C", penwidth=3, fontcolor="#7F8C8D", {pos_attr}];'
            )
        else:
            dot_lines.append(
                f'  "{node}" [label="{node}", fillcolor="#3498DB", color="#2980B9", {pos_attr}];'
            )

    # 2. エッジ（回線）の描画設定
    drawn_edges = set()
    for (u, v), weight in graph.edges.items():
        if (v, u) in drawn_edges:
            continue
        drawn_edges.add((u, v))

        is_highlighted = edge_in_path(u, v, highlight_path)
        color = "#E74C3C" if is_highlighted else "#BDC3C7"
        penwidth = "4.5" if is_highlighted else "2.0"

        dot_lines.append(
            f'  "{u}" -- "{v}" [label="コスト:{weight}", color="{color}", penwidth={penwidth}];'
        )

    dot_lines.append('}')
    return "\n".join(dot_lines)


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
        dot_code = generate_dot_graph(G)
        st.graphviz_chart(dot_code, use_container_width=True)


# ============================================================
# セクション 2: グラフとデータ表現
# ============================================================
elif page == "2. グラフとデータ表現":
    st.title("2. グラフとデータ表現")
    st.markdown("""
    コンピュータは図形を人間のようには理解できません。そのため、ネットワークのつながりを**数字の表やリスト**に変換して記憶・計算しています。
    下のチェックボックスでルータ間の接続（エッジ）をON/OFFして、データ表現がどう変わるか見てみましょう！
    """)

    nodes = G.nodes

    st.subheader("⚙️ 回線（エッジ）の切り替え")
    st.write("ルータ同士の接続（エッジ）の有無を切り替えられます：")

    cols = st.columns(3)
    all_possible_edges = [(nodes[i], nodes[j]) for i in range(len(nodes)) for j in range(i + 1, len(nodes))]

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
            G.add_edge(u, v, w)
            st.rerun()
        elif not new_state and has_edge:
            G.remove_edge(u, v)
            st.rerun()

    st.divider()

    col_left, col_right = st.columns([1, 1])

    with col_left:
        st.subheader("🌐 ネットワーク図")
        dot_code = generate_dot_graph(G)
        st.graphviz_chart(dot_code, use_container_width=True)

    with col_right:
        st.subheader("📊 隣接行列（Adjacency Matrix）とは？")
        st.markdown("行と列に各ノードを並べ、**接続している箇所のコスト**（繋がっていない場合は `0`）を入れた2次元の表です。")

        matrix_df = pd.DataFrame(0, index=nodes, columns=nodes)
        for (u, v), w in G.edges.items():
            matrix_df.loc[u, v] = w
        st.dataframe(matrix_df, use_container_width=True)

        st.subheader("📖 隣接リスト（Adjacency List）とは？")
        st.markdown("各ノードが「自分から直結しているノードとコスト」の一覧を持つ形式（Pythonの辞書構造）です。")
        adj_dict = {
            n: G.get_neighbors(n) for n in nodes
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

    nodes = G.nodes
    c1, c2 = st.columns(2)
    start = c1.selectbox("スタート（送信元ルータ）", nodes, index=0)
    goal = c2.selectbox("ゴール（宛先ルータ）", nodes, index=len(nodes) - 1)

    path = None
    total_cost = float('inf')

    if start == goal:
        st.warning("スタートとゴールには異なるルータを選んでください。")
    else:
        path, total_cost = dijkstra(G, start, goal)
        if path:
            st.success(f"🎯 **算出された最短経路 (ダイクストラ法):** {' ➔ '.join(path)} （合計通信コスト: **{total_cost}**）")
        else:
            st.error("❌ 送信元から宛先へ到達できるルートが存在しません（回線が切断されています）。")

    dot_code = generate_dot_graph(G, highlight_path=path)
    st.graphviz_chart(dot_code, use_container_width=True)


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

    col1, col2 = st.columns([1, 1])

    with col1:
        disabled_str = ', '.join(sorted(st.session_state.disabled_nodes)) if st.session_state.disabled_nodes else 'なし'
        st.markdown(f"#### ネットワーク状態（故障中ルータ: `{disabled_str}`）")

        path, cost = dijkstra(G, "A", "E", disabled_nodes=st.session_state.disabled_nodes)

        dot_code = generate_dot_graph(G, disabled_nodes=st.session_state.disabled_nodes, highlight_path=path)
        st.graphviz_chart(dot_code, use_container_width=True)

    with col2:
        st.markdown("#### 経路の変化の観察 (A ➔ E)")
        if "A" not in st.session_state.disabled_nodes and "E" not in st.session_state.disabled_nodes:
            if path:
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