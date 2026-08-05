import streamlit as st
import pandas as pd
import heapq
import time

st.set_page_config(
    page_title="ルーティングテーブル - 体験型「情報Ⅰ」学習アプリ",
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
            table.append({"宛先": dest, "ネクストホップ (次に送るルータ)": next_hop, "総コスト": cost})
        else:
            table.append({"宛先": dest, "ネクストホップ (次に送るルータ)": "到達不可", "総コスト": "∞"})
    return pd.DataFrame(table)


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

if "current_packet_step" not in st.session_state:
    st.session_state.current_packet_step = 0

G = st.session_state.G


# ============================================================
# Graphviz による描画処理
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

    dot_lines = [
        'graph G {',
        '  layout=neato;',
        '  overlap=false;',
        '  node [shape=circle, style=filled, fontname="sans-serif", fontcolor=white, width=0.45, fixedsize=true, fontsize=10];',
        '  edge [fontname="sans-serif", fontsize=9];'
    ]

    # ノード描画
    for node in sorted(graph.nodes):
        if node in disabled_nodes:
            label = f"{node}\\n(故障)"
            dot_lines.append(
                f'  "{node}" [label="{label}", fillcolor="#BDC3C7", color="#C0392B", penwidth=2, fontcolor="#7F8C8D"];'
            )
        elif node == active_node:
            # パケット現在地を黄色に点灯
            label = f"📦 {node}"
            dot_lines.append(
                f'  "{node}" [label="{label}", fillcolor="#F1C40F", color="#D35400", penwidth=3, fontcolor="#2C3E50"];'
            )
        else:
            dot_lines.append(
                f'  "{node}" [label="{node}", fillcolor="#3E6FA8", color="#2C4C70"];'
            )

    # エッジ描画
    drawn_edges = set()
    weights = list(graph.edges.values())
    w_min = min(weights) if weights else 1
    w_max = max(weights) if weights else 1

    for (u, v), weight in graph.edges.items():
        if (v, u) in drawn_edges:
            continue
        drawn_edges.add((u, v))

        is_highlighted = edge_in_path(u, v, highlight_path)
        
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
# サイドバー：ネットワークの動的設計
# ============================================================
st.sidebar.title("🛠️ ネットワーク設計")

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

st.sidebar.divider()

st.sidebar.header("③ 故障シミュレーション")
faulty = st.sidebar.multiselect(
    "一時的に故障させるルータ",
    options=sorted(list(G.nodes)),
    default=sorted(list(st.session_state.disabled & set(G.nodes))),
)
st.session_state.disabled = set(faulty)

st.sidebar.divider()
if st.sidebar.button("🔄 初期構成にリセット", use_container_width=True):
    st.session_state.G = init_default_graph()
    st.session_state.disabled = set()
    st.session_state.last_path = None
    st.session_state.current_packet_step = 0
    st.rerun()


# ============================================================
# メイン画面表示
# ============================================================
st.title("🌐 ルーティングテーブル・ラボ")
st.caption("高校「情報Ⅰ」体験型学習コンテンツ：グラフ理論とネットワークの論理")

# --- タブ構成による体験重視のデザイン ---
tab1, tab2, tab3, tab4 = st.tabs([
    "🎨 1. ネットワーク可視化 & データ",
    "📦 2. パケット配送アニメーション",
    "🕹️ 3. 最短ルート発見ゲーム",
    "🚨 4. トラブルシューティング"
])


# ============================================================
# タブ 1: ネットワーク可視化 & 内部データ
# ============================================================
with tab1:
    st.header("ネットワーク構成とルータ内部の記憶")
    
    col_graph, col_rt = st.columns([1.2, 1])
    
    with col_graph:
        st.subheader("🌐 ネットワーク構成図")
        dot_code = generate_dot_graph(G, st.session_state.disabled, st.session_state.last_path)
        st.graphviz_chart(dot_code, use_container_width=True)
        st.caption("※丸はルータ（直径約1cm相当）、線の太さは通信コスト（混雑度や遅延）を表します。")

    with col_rt:
        st.subheader("📋 ルータの「記憶」（ルーティングテーブル）")
        st.markdown("選んだルータが**『どの目的地に届けるには、次にどこへ転送すべきか』**を示した表です。")
        active_nodes = sorted([n for n in G.nodes if n not in st.session_state.disabled])
        if active_nodes:
            selected_r = st.selectbox("観察するルータを選択:", active_nodes, index=0)
            rt_df = generate_routing_table(G, selected_r, st.session_state.disabled)
            st.dataframe(rt_df, use_container_width=True, hide_index=True)
        else:
            st.warning("稼働中のルータがありません。")

    st.divider()
    
    col_matrix, col_list = st.columns(2)
    nodes_sorted = sorted(list(G.nodes))
    
    with col_matrix:
        st.subheader("📊 隣接行列（Adjacency Matrix）")
        st.markdown("プログラムが全対の繋がりを一括把握する2次元データ（0は非接続）。")
        if nodes_sorted:
            matrix = pd.DataFrame(0, index=nodes_sorted, columns=nodes_sorted)
            for (u, v), w in G.edges.items():
                matrix.loc[u, v] = w
            st.dataframe(matrix, use_container_width=True)

    with col_list:
        st.subheader("📖 隣接リスト（Python辞書形式）")
        st.markdown("各ルータが直接つながっている隣接機器とコストのリスト。")
        adjacency_dict = {n: G.get_neighbors(n) for n in nodes_sorted}
        st.code(repr(adjacency_dict), language="python")


# ============================================================
# タブ 2: パケット配送アニメーション
# ============================================================
with tab2:
    st.header("📦 データパケットの旅（配送シミュレーション）")
    st.markdown("送信元から宛先へ、ダイクストラ法で導かれた最小コスト経路を**パケット（📦）がどう通過していくか**体験できます。")

    active_nodes = sorted([n for n in G.nodes if n not in st.session_state.disabled])
    
    if len(active_nodes) >= 2:
        c1, c2 = st.columns(2)
        sim_start = c1.selectbox("送信元ルータ", active_nodes, key="sim_start")
        sim_goal = c2.selectbox("宛先ルータ", active_nodes, index=len(active_nodes)-1, key="sim_goal")

        if sim_start == sim_goal:
            st.warning("送信元と宛先には異なるルータを選択してください。")
        else:
            sim_path, sim_cost = dijkstra(G, sim_start, sim_goal, disabled_nodes=st.session_state.disabled)
            
            if sim_path:
                st.success(f"🎯 計算された最適ルート: **{' ➔ '.join(sim_path)}** （総通信コスト: **{sim_cost}**）")

                col_btn1, col_btn2, col_info = st.columns([1, 1, 2])
                
                # 自動アニメーション再生ボタン
                if col_btn1.button("▶️ 自動配送アニメーション再生", use_container_width=True):
                    placeholder = st.empty()
                    for step_idx, current_node in enumerate(sim_path):
                        dot_anim = generate_dot_graph(
                            G, st.session_state.disabled, highlight_path=sim_path, active_node=current_node
                        )
                        with placeholder.container():
                            st.subheader(f"ステップ {step_idx+1}/{len(sim_path)}: 現在地【 ルータ {current_node} 】")
                            st.graphviz_chart(dot_anim, use_container_width=True)
                        time.sleep(1.0)
                    st.toast("🎉 パケットが無事に目的地へ届きました！", icon="📦")

            else:
                st.error("❌ 途中の回線が断絶しているため、パケットを配送できません。")
    else:
        st.warning("シミュレーションを行うには2つ以上の稼働中ルータが必要です。")


# ============================================================
# タブ 3: 最短ルート発見ゲーム
# ============================================================
with tab3:
    st.header("🕹️ チャレンジ！人間 vs アルゴリズム")
    st.markdown("コンピューター（ダイクストラ法）に頼らず、**あなた自身の暗算で「最小コスト」のルート**を見つけ出してみよう！")

    active_nodes = sorted([n for n in G.nodes if n not in st.session_state.disabled])
    if len(active_nodes) >= 3:
        p_start = active_nodes[0]
        p_goal = active_nodes[-1]

        st.info(f"🚩 **お題:** ルータ **{p_start}** から ルータ **{p_goal}** までの最適ルートと最小コストを予想してください！")

        correct_path, correct_cost = dijkstra(G, p_start, p_goal, disabled_nodes=st.session_state.disabled)

        c_quiz1, c_quiz2 = st.columns(2)
        user_cost_guess = c_quiz1.number_input("あなたが予想する合計コストは？", min_value=1, max_value=200, value=5)
        
        if st.button("🔍 答え合わせをする", type="primary", use_container_width=True):
            if user_cost_guess == correct_cost:
                st.balloons()
                st.success(f"🎊 **大正解！** 正解の最小コストは **{correct_cost}** です！")
                st.markdown(f"正解の経路: **{' ➔ '.join(correct_path)}**")
            else:
                st.error(f"❌ 残念！あなたの予想: {user_cost_guess} / 正解の最小コスト: **{correct_cost}**")
                st.markdown(f"💡 正解の経路は **{' ➔ '.join(correct_path)}** でした。計算し直してみよう！")

        # ホップ数 vs コストの学びポイント
        hop_path = bfs_shortest_hops(G, p_start, p_goal, disabled_nodes=st.session_state.disabled)
        if hop_path and hop_path != correct_path:
            st.warning(
                f"👁️ **直感のトラップ：** 通過するルータ数（ホップ数）だけで見ると "
                f"`{' ➔ '.join(hop_path)}` が最少ですが、コストを合計すると"
                f"迂回ルート `{' ➔ '.join(correct_path)}` の方が早くなります！"
            )
    else:
        st.info("ゲームを行うには3つ以上のルータが必要です。")


# ============================================================
# タブ 4: トラブルシューティング実習
# ============================================================
with tab4:
    st.header("🚨 障害検知と自動迂回（セルフヒーリング）")
    st.markdown("サイドバーでルータを故障させると、ネットワークがどう変化するかを観察できます。")

    if st.session_state.disabled:
        st.error(f"🚨 **現在停止中の故障ルータ:** {', '.join(sorted(list(st.session_state.disabled)))}")

        col1, col2 = st.columns(2)
        with col1:
            st.subheader("故障前の正常な接続リスト")
            st.code(repr({n: G.get_neighbors(n) for n in G.nodes}), language="python")

        with col2:
            st.subheader("故障発生後の新しい接続リスト")
            active_adj = {n: G.get_neighbors(n) for n in active_nodes}
            st.code(repr(active_adj), language="python")

        st.success(
            "💡 **学びのポイント:** ルータが故障すると、即座にマップ（接続リスト）から排除され、"
            "各ルータは自動的に別のルート（迂回路）を再計算して通信を継続します。"
        )
    else:
        st.info("👈 左側のサイドバーにある **「③ 故障シミュレーション」** からルータを選択して故障させてみてください！")

st.divider()

# 教科書用語集
with st.expander("📘 高校「情報Ⅰ」重要用語解説"):
    st.markdown(
        """
        - **ノード（頂点）**：ネットワーク上のルータや機器。
        - **エッジ（辺）**：機器同士を結ぶ通信回線。
        - **コスト（重み）**：通信速度や遅延・混雑度を考慮した数値。
        - **ルーティングテーブル**：パケットをどの目的地へ送るために「次にどのルータ（ネクストホップ）へ渡すか」を記録した転送表。
        - **ダイクストラ法**：スタートから各ノードまでの最小コスト経路を効率よく求めるアルゴリズム。
        """