import streamlit as st
import pandas as pd
import heapq

st.set_page_config(
    page_title="マイ・ネットワーク・デザイナー",
    page_icon="🌐",
    layout="wide",
)

# ============================================================
# 自作グラフクラス & ダイクストラ法アルゴリズム (networkx非使用)
# ============================================================
class CustomGraph:
    def __init__(self):
        self.nodes = []
        self.edges = {}  # (u, v): weight

    def add_node(self, node):
        if node not in self.nodes:
            self.nodes.append(node)

    def remove_node(self, node):
        if node in self.nodes:
            self.nodes.remove(node)
            # ノードに関連するエッジを削除
            keys_to_remove = [k for k in self.edges if k[0] == node or k[1] == node]
            for k in keys_to_remove:
                del self.edges[k]

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
    """自作ダイクストラ法による最小コスト経路探索"""
    if disabled_nodes is None:
        disabled_nodes = set()

    if start in disabled_nodes or goal in disabled_nodes:
        return None, float('inf')

    active_nodes = [n for n in graph.nodes if n not in disabled_nodes]
    if start not in active_nodes or goal not in active_nodes:
        return None, float('inf')

    distances = {node: float('inf') for node in active_nodes}
    distances[start] = 0
    previous_nodes = {node: None for node in active_nodes}
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

    # 経路復元
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


def bfs_shortest_hops(graph, start, goal, disabled_nodes=None):
    """比較解説用：ホップ数（通過ルータ数）最小経路探索（BFS）"""
    if disabled_nodes is None:
        disabled_nodes = set()

    if start in disabled_nodes or goal in disabled_nodes:
        return None

    queue = [[start]]
    visited = {start}

    while queue:
        path = queue.pop(0)
        node = path[-1]

        if node == goal:
            return path

        for neighbor in graph.get_neighbors(node):
            if neighbor not in visited and neighbor not in disabled_nodes:
                visited.add(neighbor)
                new_path = list(path)
                new_path.append(neighbor)
                queue.append(new_path)
    return None


# ============================================================
# セッション状態の初期化
# ============================================================
def init_default_graph():
    G = CustomGraph()
    for n in ["R1", "R2", "R3", "R4", "R5"]:
        G.add_node(n)
    default_edges = [
        ("R1", "R2", 3),
        ("R2", "R3", 1),
        ("R1", "R4", 6),
        ("R4", "R3", 2),
        ("R3", "R5", 4),
        ("R4", "R5", 1),
    ]
    for u, v, w in default_edges:
        G.add_edge(u, v, w)
    return G

if "G" not in st.session_state:
    st.session_state.G = init_default_graph()

if "disabled" not in st.session_state:
    st.session_state.disabled = set()

if "last_path" not in st.session_state:
    st.session_state.last_path = None

G = st.session_state.G


# ============================================================
# Graphviz による描画処理 (matplotlib/networkx非使用)
# ============================================================
def edge_in_path(u, v, path):
    if not path or len(path) < 2:
        return False
    for i in range(len(path) - 1):
        if (path[i] == u and path[i + 1] == v) or (path[i] == v and path[i + 1] == u):
            return True
    return False

def generate_dot_graph(graph, disabled_nodes=None, highlight_path=None):
    if disabled_nodes is None:
        disabled_nodes = set()

    dot_lines = [
        'graph G {',
        '  layout=neato;',
        '  overlap=false;',
        '  node [shape=circle, style=filled, fontname="sans-serif", fontcolor=white, width=0.9, fixedsize=true];',
        '  edge [fontname="sans-serif", fontsize=10];'
    ]

    # ノード設定
    for node in sorted(graph.nodes):
        if node in disabled_nodes:
            label = f"{node}\\n(故障)"
            dot_lines.append(
                f'  "{node}" [label="{label}", fillcolor="#BDC3C7", color="#C0392B", penwidth=3, fontcolor="#7F8C8D"];'
            )
        else:
            dot_lines.append(
                f'  "{node}" [label="{node}", fillcolor="#3E6FA8", color="#2C4C70"];'
            )

    # エッジ設定（コストに応じて太さを可変）
    drawn_edges = set()
    weights = list(graph.edges.values())
    w_min = min(weights) if weights else 1
    w_max = max(weights) if weights else 1

    for (u, v), weight in graph.edges.items():
        if (v, u) in drawn_edges:
            continue
        drawn_edges.add((u, v))

        is_highlighted = edge_in_path(u, v, highlight_path)
        
        # コストに応じた線幅計算
        if w_max == w_min:
            penwidth = 2.5
        else:
            penwidth = 1.5 + (weight - w_min) / (w_max - w_min) * 4.5

        if is_highlighted:
            color = "#C0392B"
            penwidth = max(penwidth, 4.5)
        else:
            color = "#B0B0B0"

        dot_lines.append(
            f'  "{u}" -- "{v}" [label="コスト:{weight}", color="{color}", penwidth={penwidth}];'
        )

    dot_lines.append('}')
    return "\n".join(dot_lines)


# ============================================================
# 機能1: ネットワークの動的設計（サイドバー）
# ============================================================
st.sidebar.title("🛠️ ネットワーク設計パネル")

# ① ノード管理
st.sidebar.header("① ルータ（ノード）管理")
new_node = st.sidebar.text_input("新しいルータ名を入力", placeholder="例: R6")
if st.sidebar.button("➕ ルータを追加", use_container_width=True):
    if not new_node:
        st.sidebar.warning("ルータ名を入力してください。")
    elif new_node in G.nodes:
        st.sidebar.warning("同名のルータが既に存在します。")
    else:
        G.add_node(new_node)
        st.rerun()

if len(G.nodes) > 0:
    node_to_remove = st.sidebar.selectbox(
        "削除するルータを選択", options=["(選択なし)"] + sorted(list(G.nodes))
    )
    if st.sidebar.button("🗑️ ルータを削除", use_container_width=True):
        if node_to_remove != "(選択なし)":
            G.remove_node(node_to_remove)
            st.session_state.disabled.discard(node_to_remove)
            st.session_state.last_path = None
            st.rerun()

st.sidebar.divider()

# ② エッジ管理
st.sidebar.header("② 回線（エッジ）設定")
if len(G.nodes) >= 2:
    sorted_nodes = sorted(list(G.nodes))
    node_a = st.sidebar.selectbox("ルータA", options=sorted_nodes, key="edge_a")
    node_b = st.sidebar.selectbox("ルータB", options=sorted_nodes, key="edge_b")
    cost = st.sidebar.number_input(
        "通信コスト（重み）", min_value=1, max_value=100, value=1, step=1
    )
    if st.sidebar.button("🔗 接続を追加・更新", use_container_width=True):
        if node_a == node_b:
            st.sidebar.error("同じルータ同士は接続できません。")
        else:
            G.add_edge(node_a, node_b, int(cost))
            st.rerun()

    if len(G.edges) > 0:
        unique_edges = []
        visited_e = set()
        for (u, v), w in G.edges.items():
            if (v, u) not in visited_e:
                visited_e.add((u, v))
                unique_edges.append((u, v, w))

        edge_options = [f"{u} - {v} (コスト:{w})" for u, v, w in unique_edges]
        edge_to_remove = st.sidebar.selectbox(
            "切断する回線を選択", options=["(選択なし)"] + edge_options
        )
        if st.sidebar.button("✂️ 回線を切断", use_container_width=True):
            if edge_to_remove != "(選択なし)":
                u_v_part = edge_to_remove.split(" (")[0]
                u, v = u_v_part.split(" - ")
                G.remove_edge(u, v)
                st.session_state.last_path = None
                st.rerun()
else:
    st.sidebar.info("ルータを2つ以上追加すると回線を設定できます。")

st.sidebar.divider()

# ③ 故障設定
st.sidebar.header("③ 故障シミュレーション")
faulty = st.sidebar.multiselect(
    "一時的に故障（無効化）させるルータ",
    options=sorted(list(G.nodes)),
    default=sorted(list(st.session_state.disabled & set(G.nodes))),
)
st.session_state.disabled = set(faulty)

st.sidebar.divider()
if st.sidebar.button("🔄 初期構成にリセット", use_container_width=True):
    st.session_state.G = init_default_graph()
    st.session_state.disabled = set()
    st.session_state.last_path = None
    st.rerun()


# ============================================================
# メイン画面表示
# ============================================================
st.title("🌐 マイ・ネットワーク・デザイナー")
st.caption("高校「情報Ⅰ」学習コンテンツ：グラフ理論とルーティングの論理")

st.markdown(
    """
    ネットワークは、数学的には **「グラフ」** と呼ばれる構造で表されます。
    ルータやコンピュータなどの機器は **頂点（ノード）**、通信回線は **辺（エッジ）**、回線の混雑度や遅延は **重み（通信コスト）** に対応します。
    サイドバーでネットワークを自由に設計しながら、コンピュータ内部のデータ形式と経路選択の仕組みを学びましょう。
    """
)

st.divider()

# --- 機能2: 可視化セクション ---
st.header("1. ネットワーク構成図と内部データ表現")

col_graph, col_note = st.columns([2, 1])
with col_graph:
    dot_code = generate_dot_graph(G, st.session_state.disabled, st.session_state.last_path)
    st.graphviz_chart(dot_code, use_container_width=True)

with col_note:
    st.markdown("**図の見方**")
    st.markdown(
        """
        - **丸（ノード）**：ルータ（通信機器）
        - **線（エッジ）**：通信回線
        - **線の太さ・数値**：通信コスト（太いほどコスト大）
        - **灰色の丸**：故障中のルータ
        - **赤色の線**：シミュレーションされた最小コスト経路
        """
    )

nodes_sorted = sorted(list(G.nodes))
col_matrix, col_list = st.columns(2)

with col_matrix:
    st.subheader("隣接行列（Adjacency Matrix）")
    st.markdown("行と列の交わるマスに、2つのルータ間の通信コストを記録した表です。（`0` は直結していないことを示します）")
    if nodes_sorted:
        matrix = pd.DataFrame(0, index=nodes_sorted, columns=nodes_sorted)
        for (u, v), w in G.edges.items():
            matrix.loc[u, v] = w
        st.dataframe(matrix, use_container_width=True)
    else:
        st.info("ルータが存在しません。")

with col_list:
    st.subheader("隣接リスト（Python辞書形式）")
    st.markdown("コンピュータが記憶する「地図」の実体です。「キー：自分のルータ名」「値：接続先とコスト」の構造で保持されます。")
    adjacency_dict = {
        n: G.get_neighbors(n) for n in nodes_sorted
    }
    st.code(repr(adjacency_dict), language="python")

st.divider()

# --- 機能3: ルーティング・シミュレーション ---
st.header("2. ルーティング・シミュレーション（ダイクストラ法）")
st.markdown(
    """
    ルーティングとは、データを目的地まで届けるために **合計コストが最小となる最適な経路** を決定することです。
    経由するルータの数が少なくても、回線コストが高い場合は遠回りの方が早く届くことがあります。
    """
)

active_nodes = sorted([n for n in G.nodes if n not in st.session_state.disabled])
if len(active_nodes) >= 2:
    c1, c2, c3 = st.columns([1, 1, 1])
    start = c1.selectbox("スタート（送信元）", active_nodes, key="start_node")
    goal_default_idx = 1 if len(active_nodes) > 1 else 0
    goal = c2.selectbox("ゴール（宛先）", active_nodes, index=goal_default_idx, key="goal_node")
    calc = c3.button("🧭 最小コスト経路を計算", type="primary", use_container_width=True)

    if calc:
        if start == goal:
            st.warning("スタートとゴールには異なるルータを選択してください。")
            st.session_state.last_path = None
        else:
            path, cost = dijkstra(G, start, goal, disabled_nodes=st.session_state.disabled)
            if path:
                st.session_state.last_path = path
                st.success(f"🎯 **最小コスト経路 (ダイクストラ法):** {' ➔ '.join(path)} （合計コスト: **{cost}**）")

                # ホップ数（通過ルータ数）最小経路との比較
                hop_path = bfs_shortest_hops(G, start, goal, disabled_nodes=st.session_state.disabled)
                if hop_path and hop_path != path:
                    hop_cost = sum(G.edges[(hop_path[i], hop_path[i+1])] for i in range(len(hop_path)-1))
                    st.info(
                        f"💡 **解説：** 経由するルータ数（ホップ数）だけで選ぶと "
                        f"`{' ➔ '.join(hop_path)}` （合計コスト: {hop_cost}）となりますが、"
                        f"ダイクストラ法では各回線の遅延や混雑度を考慮した最小コスト経路が選ばれます。"
                    )
                else:
                    st.info("💡 **解説：** この構成では「ルータ数が最も少ない経路」と「合計コストが最小の経路」が一致しています。")
            else:
                st.error("❌ 経路が見つかりません。回線が途絶しているか、故障中のルータが経路を遮断しています。")
                st.session_state.last_path = None
    st.caption("※計算結果は上の「ネットワーク構成図」に赤色で表示されます。")
else:
    st.warning("経路計算を行うには、故障していないルータが2つ以上必要です。")

st.divider()

# --- 機能4: トラブルシューティング実習 ---
st.header("3. トラブルシューティング実習（故障と自動迂回）")
st.markdown(
    """
    サイドバーの「③ 故障シミュレーション」でルータを選択すると、その機器が障害停止した状態を再現できます。
    障害発生時に **隣接リスト（地図）がどう更新され、迂回路（バックアップルート）がどう自動選択されるか** を観察しましょう。
    """
)

if st.session_state.disabled:
    st.error(f"🚨 現在「故障中」のルータ： **{', '.join(sorted(list(st.session_state.disabled)))}**")

    active_adjacency = {
        n: G.get_neighbors(n) for n in active_nodes
    }

    colA, colB = st.columns(2)
    with colA:
        st.markdown("**故障前の全体隣接リスト**")
        st.code(repr(adjacency_dict), language="python")
    with colB:
        st.markdown("**故障後の有効な隣接リスト**")
        st.code(repr(active_adjacency), language="python")

    st.caption(
        "故障したルータとそれに接続されていた回線がリストから消去されています。"
        "ルーティングプロトコルは、この新しい隣接リストをもとに自動で再計算を行い、迂回路を発見します。"
    )
else:
    st.info("現在、故障中のルータはありません。サイドバーの「③ 故障シミュレーション」でルータを選択してください。")

st.divider()

# まとめ用語集
with st.expander("📘 情報Ⅰ 用語集"):
    st.markdown(
        """
        - **頂点（ノード）**：ネットワーク上の端末や機器（ここではルータ）。
        - **辺（エッジ）**：ノード同士を結ぶ通信回線。
        - **重み（コスト）**：通信速度、帯域幅、遅延時間などを表す数値。小さいほど好ましい。
        - **隣接行列**：すべてのノード対の接続状態とコストを表形式（2次元配列）で保持する構造。
        - **隣接リスト**：各ノードに直結している相手とコストのペアの一覧（辞書構造など）で保持する構造。
        - **ダイクストラ法**：重み付きグラフにおいて、指定した開始ノードから他のノードへの最小コスト経路を求めるアルゴリズム。
        - **ルーティング**：パケット（データ）を目的地まで最適な経路を選んで転送する処理。
        """
    )