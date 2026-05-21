"""
Coletti OS — Money Flow Network Engine
Builds interactive network graphs of account-to-entity transaction flows.
Uses PyVis + NetworkX for court-ready visual evidence.
"""

import pandas as pd

try:
    import networkx as nx
    NETWORKX_AVAILABLE = True
except ImportError:
    NETWORKX_AVAILABLE = False

try:
    from pyvis.network import Network
    PYVIS_AVAILABLE = True
except ImportError:
    PYVIS_AVAILABLE = False


# Node color palette
NODE_COLORS = {
    'account':   '#1a73e8',   # blue — bank accounts
    'entity':    '#c0392b',   # red — named individuals
    'platform':  '#e67e22',   # orange — P2P platforms
    'unknown':   '#7f8c8d',   # gray — unidentified
}

P2P_KEYWORDS = ['venmo', 'cashapp', 'zelle', 'paypal', 'cash app', 'apple pay']


def _node_type(name: str) -> str:
    nl = name.lower()
    if any(k in nl for k in P2P_KEYWORDS):
        return 'platform'
    return 'entity'


def build_flow_graph(df: pd.DataFrame, source_account: str = "First Florida ×0094",
                     entity_config: dict = None) -> str:
    """
    Build an interactive PyVis network graph of money flows.
    Nodes: source account, entities, P2P platforms.
    Edges: transaction flows with dollar totals as weights.
    Returns HTML string.
    """
    if not NETWORKX_AVAILABLE or not PYVIS_AVAILABLE:
        missing = []
        if not NETWORKX_AVAILABLE:
            missing.append("networkx")
        if not PYVIS_AVAILABLE:
            missing.append("pyvis")
        return f"<p>Missing libraries: {', '.join(missing)}. Run: pip install {' '.join(missing)}</p>"

    G = nx.DiGraph()

    # Source node (the marital account being analyzed)
    G.add_node(source_account, node_type='account', total=0.0)

    # Tally flows: source_account → destination_node
    flows: dict[str, float] = {}
    flow_counts: dict[str, int] = {}

    for _, row in df.iterrows():
        amount = float(row.get('Amount') or 0)
        desc = str(row.get('Description', ''))
        entity = row.get('Entity')
        category = row.get('Category', '')

        # Determine destination node
        if entity:
            dest = entity
        elif any(k in desc.lower() for k in P2P_KEYWORDS):
            # Extract P2P platform name
            for k in P2P_KEYWORDS:
                if k in desc.lower():
                    dest = k.title().replace(' ', '')
                    break
        elif category in ('CASH_WITHDRAWAL', 'INTERNAL_THEFT'):
            dest = 'Cash (Untraced)'
        elif category == 'TRANSFER':
            dest = 'External Transfer'
        elif category == 'CRYPTO_CONVERSION':
            dest = 'Cryptocurrency'
        elif category == 'INVESTMENT':
            dest = 'Investment Account'
        elif category == 'GAMBLING':
            dest = 'Gambling Platform'
        else:
            continue  # skip unclassified

        flows[dest] = flows.get(dest, 0.0) + amount
        flow_counts[dest] = flow_counts.get(dest, 0) + 1

    total_out = sum(flows.values())

    # Add destination nodes + edges
    for dest, total in flows.items():
        ntype = _node_type(dest)
        G.add_node(dest, node_type=ntype, total=total)
        G.add_edge(source_account, dest, weight=total, count=flow_counts[dest])

    # Build PyVis network
    net = Network(height='550px', width='100%', directed=True,
                  bgcolor='#0d1117', font_color='#c9d1d9')
    net.barnes_hut(gravity=-8000, central_gravity=0.3, spring_length=150)

    for node, data in G.nodes(data=True):
        ntype = data.get('node_type', 'unknown')
        color = NODE_COLORS.get(ntype, NODE_COLORS['unknown'])
        total = data.get('total', 0)
        size = 25 if node == source_account else max(15, min(50, total / 500))
        label = f"{node}\n${total:,.0f}" if total else node
        net.add_node(node, label=label, color=color, size=size,
                     title=f"<b>{node}</b><br>Total: ${total:,.2f}")

    for u, v, data in G.edges(data=True):
        weight = data['weight']
        count = data['count']
        pct = (weight / total_out * 100) if total_out else 0
        width = max(1, min(12, weight / 1000))
        net.add_edge(u, v, value=width, width=width, color='#f85149',
                     title=f"${weight:,.2f} ({pct:.1f}%) — {count} txn{'s' if count != 1 else ''}")

    # Inline options for dark theme
    net.set_options("""
    {
      "edges": {"arrows": {"to": {"enabled": true, "scaleFactor": 0.8}},
                "smooth": {"type": "curvedCW", "roundness": 0.2}},
      "physics": {"enabled": true},
      "interaction": {"hover": true, "tooltipDelay": 100}
    }
    """)

    return net.generate_html()
