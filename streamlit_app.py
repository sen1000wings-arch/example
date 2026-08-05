import streamlit as st
import pandas as pd
import heapq
import random
import time

st.set_page_config(
    page_title="ルーティングテーブル - 高校「情報Ⅰ」学習アプリ",
    page_icon="🌐",
    layout="wide",
)

# ============================================================
# 自作グラフクラス & アルゴリズム (networkx/matplotlib非使用)
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
    """ダイクストラ法による最小コスト経路探索"""
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
    """ホップ数（通過ルータ数）最小経路探索"""
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

def generate_routing_table(graph, node, disabled_nodes=None):
    """特定のルータが保持するルーティングテーブル（転送表）の生成"""
    table = []
    for dest in sorted(graph.nodes):
        if dest == node:
            continue
        path, cost = dijkstra(graph, node, dest, disabled_nodes)
        if path and len(path) >= 2:
            next_hop = path[1]
            table.append({"宛先ルータ": dest, "ネクストホップ (次に渡すルータ)": next_hop, "合計通信コスト": cost})
        else:
            table.append({"宛先ルータ": dest, "ネクストホップ (次に渡すルータ)": "到達不可", "合計通信コスト": "∞"})
    return pd.DataFrame(table)


# ============================================================
# セッション状態の初期化と 5. ランダム生成ロジック
# ============================================================
def init_default_graph():
    G = CustomGraph()
    for n in ["R1", "R2", "R3", "R4", "R5"]:
        G.add_node(n)
    default_edges = [
        ("R1", "R2", 3),
        ("R2", "R3", 2),
        ("R1", "R4", 5),
        ("R4", "R3", 2),
        ("R3", "R5", 4),
    ]
    for u, v, w in default_edges:
        G.add_edge(u, v, w)
    return G

def generate_random_network():
    """
    要件5:
    - ノード: 4箇所以上8箇所以下
    - エッジ: 1本以上4本以下
    - 通信コスト: 2以上5以下
    - 故障ルータ: 1箇所以下
    """
    G = CustomGraph()
    
    # 1. ノード数（4〜8箇所）
    node_count = random.randint(4, 8)
    nodes = [f"R{i+1}" for i in range(node_count)]
    for n in nodes:
        G.add_node(n)
    
    # 2. エッジ数（1〜4本）
    edge_count = random.randint(1, 4)
    
    # 選択可能な全ペアからランダムに指定本数だけ選択
    all_possible_pairs = []
    for i in range(node_count):
        for j in range(i + 1, node_count):
            all_possible_pairs.append((nodes[i], nodes[j]))
            
    chosen_pairs = random.sample(all_possible_pairs, min(edge_count, len(all_possible_pairs)))
    
    # 3. 各エッジに通信コスト（2〜5）を設定
    for u, v in chosen_pairs:
        cost = random.randint(2, 5)
        G.add_edge(u, v, cost)
        
    # 4. 故障ルータ（1箇所以下：0箇所または1箇所）
    disabled = set()
    if random.choice([True, False]):  # 50%の確率で1箇所故障
        disabled = {random.choice(nodes)}
        
    return G, disabled

if "G" not in st.session_state:
    st.session_state.G = init_default_graph()

if "disabled" not in st.session_state:
    st.session_state.disabled = set()

if "last_path" not in st.session_state:
    st.session_state.last_path = None

G = st.session_state.G


# ============================================================
# Graphviz による描画 (要件: ノード直径約1cm & エッジの太さ可変化)
# ============================================================
def edge_in_path(u, v, path):
    if not path or len(path) < 2:
        return False
    for i in range(len(path) - 1):
        if (path[i] == u and path[i + 1] == v) or (path[i] == v and path[i + 1] == u):
            return True
    return False

def generate_dot_graph(graph, disabled_nodes=None, highlight_path=None, active_node=None):
    if disabled_nodes is None:
        disabled_nodes = set()

    # width=0.4in (約1cm相当) でノードを描画
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
        elif node == active_node:
            label = f"📦\\n{node}"
            dot_lines.append(
                f'  "{node}" [label="{label}", fillcolor="#F1C40F", color="#D35400", penwidth=3, fontcolor="#2C3E50"];'
            )
        else:
            dot_lines.append(
                f'  "{node}" [label="{node}", fillcolor="#3E6FA8", color="#2C4C70"];'
            )

    # エッジ設定（コストに応じて太さを動的変化）
    drawn_edges = set()
    weights = list(graph.edges.values())
    w_min = min(weights) if weights else 1
    w_max = max(weights) if weights else 1

    for (u, v), weight in graph.edges.items():
        if (v, u) in drawn_edges:
            continue
        drawn_edges.add((u, v))

        is_highlighted = edge_in_path(u, v, highlight_path)
        
        # コストに応じた線幅の動的計算
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
# サイドバー：1. ネットワークの動的設計 & 5. ランダム生成
# ============================================================
st.sidebar.title("🛠️ ネットワーク設計")

# 機能5. ランダム生成機能
st.sidebar.header("🎲 ランダム構成生成")
if st.sidebar.button("🎲 ランダムに生成する", use_container_width=True, type="primary"):
    st.session_state.G, st.session_state.disabled = generate_random_network()
    st.session_state.last_path = None
    st.rerun()
st.sidebar.caption("※ノード:4〜8箇所 / エッジ:1〜4本 / コスト:2〜5 / 故障:1箇私以下")

st.sidebar.divider()

# 機能1. ノード追加・削除
st.sidebar.header("① ルータ（ノード）の管理")
new_node = st.sidebar.text_input("追加するルータ名", placeholder="例: R6")
if st.sidebar.button("➕ ルータを追加", use_container_width=True):
    if not new_node:
        st.sidebar.warning("ルータ名を入力してください。")
    elif new_node in G.nodes:
        st.sidebar.warning("同じ名前のルータがすでに存在します。")
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

# 機能1. エッジ設定（マルチセレクト＆コスト数値入力）
st.sidebar.header("② 回線（エッジ）と通信コストの設定")
if len(G.nodes) >= 2:
    sorted_nodes = sorted(list(G.nodes))
    nodes_selected = st.sidebar.multiselect(
        "接続する2つのルータを選択", options=sorted_nodes, max_selections=2, key="multiselect_nodes"
    )
    cost = st.sidebar.number_input(
        "通信コスト（重み・混雑度）", min_value=1, max_value=100, value=2, step=1
    )
    if st.sidebar.button("🔗 回線を接続・更新", use_container_width=True):
        if len(nodes_selected) == 2:
            u, v = nodes_selected[0], nodes_selected[1]
            G.add_edge(u, v, int(cost))
            st.rerun()
        else:
            st.sidebar.error("ルータをちょうど2つ選択してください。")

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

st.sidebar.divider()

# 機能4 (設定部): 故障ルータの設定
st.sidebar.header("③ 故障シミュレーション（無効化）")
faulty = st.sidebar.multiselect(
    "一時的に無効化（故障）させるルータ",
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
st.title("🌐 ルーティングテーブル・ラボ")
st.caption("高校「情報Ⅰ」学習コンテンツ：グラフ理論とルーティングの論理")

tab1, tab2, tab3 = st.tabs([
    "📊 1. データの可視化セクション",
    "🧭 2. ルーティング・シミュレーション",
    "🚨 3. トラブルシューティング実習"
])


# ============================================================
# 機能2: データの可視化セクション
# ============================================================
with tab1:
    st.header("1. グラフ描画と内部データ構造")
    
    col_graph, col_rt = st.columns([1.2, 1])
    
    with col_graph:
        st.subheader("🌐 ネットワーク構成図")
        dot_code = generate_dot_graph(G, st.session_state.disabled, st.session_state.last_path)
        st.graphviz_chart(dot_code, use_container_width=True)
        st.caption("※丸（頂点/ノード）は直径約1cm相当。線の太さは通信コスト（重み）の大きさを視覚化しています。")

    with col_rt:
        st.subheader("📋 ルーティングテーブル（転送表）")
        st.markdown("各ルータが保持する「宛先に対して次にどのルータへ渡すべきか」を記した内部データです。")
        active_nodes = sorted([n for n in G.nodes if n not in st.session_state.disabled])
        if active_nodes:
            selected_r = st.selectbox("観察するルータを選択:", active_nodes, index=0)
            rt_df = generate_routing_table(G, selected_r, st.session_state.disabled)
            st.dataframe(rt_df, use_container_width=True, hide_index=True)
        else:
            st.warning("現在、稼働しているルータがありません。")

    st.divider()
    
    col_matrix, col_list = st.columns(2)
    nodes_sorted = sorted(list(G.nodes))
    
    with col_matrix:
        st.subheader("隣接行列（Adjacency Matrix）")
        st.markdown("接続状況を表形式（2次元配列）で表示。つながっていれば通信コスト（重み）、つながっていなければ 0 で示されます。")
        if nodes_sorted:
            matrix = pd.DataFrame(0, index=nodes_sorted, columns=nodes_sorted)
            for (u, v), w in G.edges.items():
                matrix.loc[u, v] = w
            st.dataframe(matrix, use_container_width=True)

    with col_list:
        st.subheader("隣接リスト（Python辞書形式）")
        st.markdown("「どのルータがどこに繋がっているか」をキー・バリュー形式で表示。これがコンピュータが読み取る**『地図』の正体**です。")
        adjacency_dict = {n: G.get_neighbors(n) for n in nodes_sorted}
        st.code(repr(adjacency_dict), language="python")


# ============================================================
# 機能3: ルーティング・シミュレーション
# ============================================================
with tab2:
    st.header("2. ダイクストラ法による最小コスト経路の計算")
    st.markdown(
        """
        パケット（データ）を送る際、ルータは **「通信コスト（速度や混雑度など）の合計が最小になる経路」** をアルゴリズムで選択します。
        これを **ルーティング（経路制御）** と呼びます。
        """
    )

    active_nodes = sorted([n for n in G.nodes if n not in st.session_state.disabled])
    if len(active_nodes) >= 2:
        c1, c2 = st.columns(2)
        start = c1.selectbox("スタート（送信元ルータ）", active_nodes, key="sim_start")
        goal_default_idx = len(active_nodes) - 1
        goal = c2.selectbox("ゴール（宛先ルータ）", active_nodes, index=goal_default_idx, key="sim_goal")

        if start == goal:
            st.warning("スタートとゴールには異なるルータを選択してください。")
        else:
            path, cost = dijkstra(G, start, goal, disabled_nodes=st.session_state.disabled)
            
            if path:
                st.session_state.last_path = path
                st.success(f"🎯 **ダイクストラ法で算出された最適ルート:** {' ➔ '.join(path)} （合計通信コスト: **{cost}**）")

                # アニメーション再生機能
                if st.button("▶️ パケット（📦）の配送を再現する", type="primary"):
                    placeholder = st.empty()
                    for step_idx, current_node in enumerate(path):
                        dot_anim = generate_dot_graph(
                            G, st.session_state.disabled, highlight_path=path, active_node=current_node
                        )
                        with placeholder.container():
                            st.subheader(f"ステップ {step_idx+1}/{len(path)}: 現在【 ルータ {current_node} 】を通過中")
                            st.graphviz_chart(dot_anim, use_container_width=True)
                        time.sleep(0.8)
                    st.toast("🎉 パケットが無事に目的地へ到達しました！", icon="📦")

                # 最短経路（ルータ数）と最小コスト経路の違いに関する解説
                hop_path = bfs_shortest_hops(G, start, goal, disabled_nodes=st.session_state.disabled)
                if hop_path and hop_path != path:
                    hop_cost = sum(G.edges[(hop_path[i], hop_path[i+1])] for i in range(len(hop_path)-1))
                    st.info(
                        f"💡 **教科書（情報Ⅰ）解説：** 通過するルータの数（ホップ数）だけで見ると "
                        f"`{' ➔ '.join(hop_path)}` （合計コスト: {hop_cost}）が最少です。\n\n"
                        f"しかしルーティングでは、**『最短経路＝ルータの数が少ない』とは限らず、コスト（通信速度や混雑度）の合計が最小になる道**（`{' ➔ '.join(path)}`）が選ばれます。"
                    )
                else:
                    st.info("💡 **教科書（情報Ⅰ）解説：** 「最短経路＝ルータの数が少ない」とは限らず、「コスト（通信速度や混雑度）の合計が最小」になる道を選ぶのがルーティングの基本原則です。")
            else:
                st.error("❌ 経路が存在しません。回線が繋がっていないか、故障ルータにより遮断されています。")
                st.session_state.last_path = None
    else:
        st.warning("計算を行うには、正常に稼働しているルータが2つ以上必要です。")


# ============================================================
# 機能4: トラブルシューティング実習
# ============================================================
with tab3:
    st.header("3. 故障発生時の自動再計算（セルフヒーリング）")
    st.markdown(
        """
        特定のルータを一時的に「無効化（故障）」させた際、隣接リスト（地図）がどう書き換わり、
        通信経路がどのように自動再計算（迂回）されるかを観察・検証します。
        """
    )

    if st.session_state.disabled:
        st.error(f"🚨 **現在「無効化（故障中）」のルータ:** {', '.join(sorted(list(st.session_state.disabled)))}")

        colA, colB = st.columns(2)
        with colA:
            st.markdown("**【故障前】ネットワーク全体の隣接リスト**")
            st.code(repr({n: G.get_neighbors(n) for n in G.nodes}), language="python")

        with colB:
            st.markdown("**【故障後】通信に使用可能な隣接リスト**")
            active_adj = {n: G.get_neighbors(n) for n in active_nodes}
            st.code(repr(active_adj), language="python")

        st.success(
            "💡 **実習解説:** 故障したルータが無効化されたことで、隣接リストから対象ノードが即座に除外されました。"
            "各ルータは新しい隣接リストをもとにダイクストラ法を再実行し、自動的に障害箇所を避ける「迂回路」を決定します。"
        )
    else:
        st.info("現在、無効化されたルータはありません。サイドバーの **「③ 故障シミュレーション」** でルータを選択して無効化してみてください。")

st.divider()

# 教科書用語集
with st.expander("📘 高校「情報Ⅰ」重要用語解説"):
    st.markdown(
        """
        - **頂点（ノード）**：ネットワークに接続されたルータや端末。
        - **辺（エッジ）**：ノード同士を結ぶ通信回線。
        - **重み（通信コスト）**：回線の通信速度、帯域幅、混雑度、遅延時間などを総合的に数値化した指標。
        - **隣接行列**：2次元配列（表）を用いて全ノード間の接続関係と重みを一覧管理するデータ構造。
        - **隣接リスト**：各ノードが直結している隣接相手とコストを対応付けたデータ構造（Pythonの辞書形式など）。
        - **ダイクストラ法**：スタートから目的地までの合計通信コストが最小となるルート（最短経路）を効率よく解くアルゴリズム。
        - **ルーティングテーブル（転送表）**：各ルータが宛先アドレスと「ネクストホップ（次に転送すべき隣のルータ）」の組を記録した表。
        """
    )