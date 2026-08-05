import streamlit as st
import pandas as pd
import heapq

st.set_page_config(
    page_title="ルーティングテーブル - 高校「情報Ⅰ」学習アプリ",
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
            # 関連するエッジを削除
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

def bfs_shortest_hops(graph, start, goal, disabled_nodes=None):
    """比較解説用：ホップ数（通過ルータ数）最小経路探索"""
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
# Graphviz による描画処理 (1cm相当ノード & 動的エッジ太さ)
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

    # width=0.4in ≒ 約1cm (72pt * 0.3937in ≒ 28pt ≒ 1cm)
    dot_lines = [
        'graph G {',
        '  layout=neato;',
        '  overlap=false;',
        '  node [shape=circle, style=filled, fontname="sans-serif", fontcolor=white, width=0.4, fixedsize=true, fontsize=10];',
        '  edge [fontname="sans-serif", fontsize=9];'
    ]

    # ノード設定
    for node in sorted(graph.nodes):
        if node in disabled_nodes:
            label = f"{node}\\n(故障)"
            dot_lines.append(
                f'  "{node}" [label="{label}", fillcolor="#BDC3C7", color="#C0392B", penwidth=2, fontcolor="#7F8C8D"];'
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
            penwidth = 1.2 + (weight - w_min) / (w_max - w_min) * 4.0

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
st.sidebar.title("🛠️ ネットワーク設計")

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
st.title("🌐 ルーティングテーブル")
st.caption("高校「情報Ⅰ」学習コンテンツ：グラフ理論とネットワークの論理")

st.markdown(
    """
    ネットワーク構造は、数学的には **「グラフ」** というモデルで表現されます。
    通信機器（ルータ）は **頂点（ノード）**、通信回線は **辺（エッジ）**、回線の混雑度や遅延は **重み（通信コスト）** に対応します。
    サイドバーでネットワークを自由に設計し、ルータが内部で保持するデータ表現と経路決定の仕組みを体験しましょう。
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
        - **丸（ノード）**：ルータ（通信機器・直径約1cm）
        - **線（エッジ）**：通信回線（太さはコストに比例）
        - **数値**：通信コスト（重み）
        - **灰色の丸**：故障中のルータ
        - **赤色の線**：ダイクストラ法で導出された最小コスト経路
        """
    )

nodes_sorted = sorted(list(G.nodes))
col_matrix, col_list = st.columns(2)

with col_matrix:
    st.subheader("隣接行列（Adjacency Matrix）")
    st.markdown("すべてのルータ対の接続とコストを表形式で保持します。（`0` は非接続を示します）")
    if nodes_sorted:
        matrix = pd.DataFrame(0, index=nodes_sorted, columns=nodes_sorted)
        for (u, v), w in G.edges.items():
            matrix.loc[u, v] = w
        st.dataframe(matrix, use_container_width=True)
    else:
        st.info("ルータが存在しません。")

with col_list:
    st.subheader("隣接リスト（Python辞書形式）")
    st.markdown("各ルータが「自分と直接繋がっている接続先とコスト」のペアとして記憶する『地図』の実体です。")
    adjacency_dict = {
        n: G.get_neighbors(n) for n in nodes_sorted
    }
    st.code(repr(adjacency_dict), language="python")

st.divider()

# --- 機能3: ルーティング・シミュレーション ---
st.header("2. ルーティング・シミュレーション（ダイクストラ法）")
st.markdown(
    """
    パケット（データのかたまり）を目的地まで送る際、ルータは **通信コストの合計が最小になる経路** を計算して転送します。
    これを **ルーティング（経路制御）** と呼びます。
    """
)

active_nodes = sorted([n for n in G.nodes if n not in st.session_state.disabled])
if len(active_nodes) >= 2:
    c1, c2, c3 = st.columns([1, 1, 1])
    start = c1.selectbox("スタート（送信元ルータ）", active_nodes, key="start_node")
    goal_default_idx = 1 if len(active_nodes) > 1 else 0
    goal = c2.selectbox("ゴール（宛先ルータ）", active_nodes, index=goal_default_idx, key="goal_node")
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
                        f"💡 **学習ポイント：** 通過するルータの数（ホップ数）だけで選ぶと "
                        f"`{' ➔ '.join(hop_path)}` （合計コスト: {hop_cost}）となりますが、"
                        f"ルーティングでは通信速度や遅延を考慮した**「合計コスト最小経路」**（`{' ➔ '.join(path)}`）が選ばれます。"
                    )
                else:
                    st.info("💡 **学習ポイント：** 「通過ルータ数が最も少ない経路」と「合計コストが最小の経路」が一致しています。")
            else:
                st.error("❌ 経路が見つかりません。回線が切断されているか、故障中のルータにより遮断されています。")
                st.session_state.last_path = None
    st.caption("※計算された最短経路は、画面上部の「ネットワーク構成図」上に赤色の太線で表示されます。")
else:
    st.warning("経路計算を行うには、故障していないルータが2つ以上必要です。")

st.divider()

# --- 機能4: トラブルシューティング実習 ---
st.header("3. トラブルシューティング実習（故障と自動迂回）")
st.markdown(
    """
    サイドバーの「③ 故障シミュレーション」でルータを選択すると、その機器が故障停止した状態を模倣できます。
    障害発生によって **隣接リスト（地図）がどのように自動更新され、迂回路が選ばれるか** を確認しましょう。
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
        "故障したルータとそれに繋がる回線が地図（隣接リスト）から即座に排除され、"
        "ルーティングプロトコルが自動的に新しい地図をもとにバックアップルートを導き出します。"
    )
else:
    st.info("現在、故障中のルータはありません。サイドバーの「③ 故障シミュレーション」からルータを故障させてみてください。")

st.divider()

# 情報Ⅰ 教科書用語集
with st.expander("📘 高校「情報Ⅰ」重要用語解説"):
    st.markdown(
        """
        - **頂点（ノード）**：ネットワークに接続されたルータや端末などの通信機器。
        - **辺（エッジ）**：ノード同士をつなぐ通信回線。
        - **重み（通信コスト）**：回線の遅延時間、帯域幅（通信速度）、混雑状況などを数値化したもの。
        - **隣接行列**：2次元配列（表）を用いて、全ノード間の接続関係とコストを一括管理するデータ構造。
        - **隣接リスト**：各ノードが直結する隣のノードとコストの一覧（辞書構造）で保持するデータ構造。
        - **ダイクストラ法**：スタート地点から目的地までの合計通信コストが最小になる経路を効率よく探すアルゴリズム。
        - **ルーティング（経路制御）**：パケットを最適なルートへと中継・転送する制御のこと。
        """
    )