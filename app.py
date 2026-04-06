"""
╔══════════════════════════════════════════════════════════════╗
║   Reagent Supply Chain AI Planner                           ║
║   MCTS · CVaR Risk Scoring · Stochastic Demand Forecasting  ║
╚══════════════════════════════════════════════════════════════╝

Drop-in replacement for the original app.py.
No Azure OpenAI required — uses Anthropic Claude via standard API.

Run:
    pip install -r requirements.txt
    export ANTHROPIC_API_KEY=sk-ant-...   # optional for AI tab
    streamlit run app.py
"""

# ── stdlib ────────────────────────────────────────────────────────────────────
import json
import os
import sys
from datetime import datetime, timedelta
from typing import Optional

# ── third-party ───────────────────────────────────────────────────────────────
import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

# ── local src package ─────────────────────────────────────────────────────────
sys.path.insert(0, os.path.dirname(__file__))

from src.core.action import DoNothingAction, ExpireAction, ProcurementAction, TransferAction
from src.core.state import MarketEvent, SystemState
from src.core.transition import apply_action
from src.demand.scenario_generator import ScenarioGenerator
from src.planning.action_generator import ActionGenerator
from src.planning.mcts import MCTS
from src.simulation.environment import step_environment
from src.utils.db_loader import load_state_from_db

# ══════════════════════════════════════════════════════════════════════════════
#  PAGE CONFIG & GLOBAL STYLES
# ══════════════════════════════════════════════════════════════════════════════

st.set_page_config(
    page_title="Reagent Supply Chain AI",
    page_icon="🧪",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&family=JetBrains+Mono:wght@400;600&display=swap');

html, body, [class*="css"] { font-family: 'Inter', sans-serif; }

/* sidebar */
[data-testid="stSidebar"] { background: #0a0f1e; }
[data-testid="stSidebar"] * { color: #b0bec5 !important; }
[data-testid="stSidebar"] .stButton > button {
    background: #1a2744; border: 1px solid #2d3f6b;
    color: #90caf9 !important; width: 100%;
}

/* metric cards */
[data-testid="metric-container"] {
    background: linear-gradient(135deg, #0d1b2a 0%, #1a2744 100%);
    border: 1px solid #2d3f6b; border-radius: 12px; padding: 20px 24px;
}
[data-testid="stMetricValue"] {
    font-family: 'JetBrains Mono', monospace !important;
    font-size: 1.85rem !important; font-weight: 600 !important;
}
[data-testid="stMetricLabel"] {
    font-size: 0.75rem !important; letter-spacing: 0.07em;
    text-transform: uppercase; opacity: 0.65;
}

/* tabs */
[data-baseweb="tab-list"] { gap: 4px; border-bottom: 1px solid #2d3f6b; }
[data-baseweb="tab"] {
    border-radius: 8px 8px 0 0; font-weight: 600;
    font-size: 0.84rem; padding: 8px 18px;
}

/* alert boxes */
.alert { padding: 14px 18px; border-radius: 0 10px 10px 0; margin: 10px 0; font-size: 0.88rem; line-height: 1.6; }
.alert-red    { background: rgba(239,68,68,.1);  border-left: 4px solid #ef4444; }
.alert-amber  { background: rgba(245,158,11,.1); border-left: 4px solid #f59e0b; }
.alert-green  { background: rgba(34,197,94,.1);  border-left: 4px solid #22c55e; }
.alert-blue   { background: rgba(59,130,246,.1); border-left: 4px solid #3b82f6; }

/* recommended action card */
.action-card {
    background: linear-gradient(135deg, #052e16 0%, #0a3d2b 100%);
    border: 1px solid #166534; border-radius: 12px;
    padding: 20px 24px; margin: 12px 0;
}
.action-card h3 { margin: 0 0 8px 0; font-size: 1.05rem; color: #86efac; }
.action-card p  { margin: 0; font-size: 0.86rem; color: #bbf7d0; opacity: 0.9; line-height: 1.6; }

/* small section headers */
.sec { font-size: 0.7rem; font-weight: 700; letter-spacing: 0.12em;
       text-transform: uppercase; color: #475569; margin: 22px 0 8px 0;
       padding-bottom: 5px; border-bottom: 1px solid #1e293b; }
</style>
""", unsafe_allow_html=True)


# ══════════════════════════════════════════════════════════════════════════════
#  SHARED HELPERS
# ══════════════════════════════════════════════════════════════════════════════

def fmt_usd(v: float) -> str:  return f"${v:,.0f}"
def fmt_pct(v: float) -> str:  return f"{v:.1%}"
def sec(label: str):           st.markdown(f'<p class="sec">{label}</p>', unsafe_allow_html=True)

CHART = dict(           # shared dark-theme plotly layout kwargs
    plot_bgcolor  = "#0d1b2a",
    paper_bgcolor = "#0d1b2a",
    font          = dict(color="#94a3b8", size=11),
    margin        = dict(t=46, b=28, l=8, r=8),
    legend        = dict(orientation="h", yanchor="bottom", y=1.02, font=dict(size=10)),
)
GRID = dict(gridcolor="#1e293b", zeroline=False)

def chart_layout(title: str, height: int = 320, **extra) -> dict:
    base = dict(**CHART,
                title=dict(text=title, font=dict(size=13, color="#e2e8f0")),
                height=height, xaxis=GRID, yaxis=dict(**GRID))
    base.update(extra)
    return base


def expiring_soon(state: SystemState, days: int = 7) -> float:
    return sum(
        item.quantity for items in state.inventory.values()
        for item in items
        if item.expiry_days is not None and 0 < item.expiry_days <= days
    )

def service_level(state: SystemState) -> float:
    vals = []
    for mid in state.inventory:
        d = sum(state.window_demand.get(mid, []))
        f = sum(state.window_fulfilled.get(mid, []))
        vals.append(f / d if d > 0 else 1.0)
    return float(np.mean(vals)) if vals else 1.0

def inv_value(state: SystemState) -> float:
    return sum(
        item.quantity * state.catalog[mid].unit_price
        for mid, items in state.inventory.items()
        for item in items if mid in state.catalog
    )

def action_reason(state: SystemState, action) -> str:
    if isinstance(action, ProcurementAction):
        mid    = action.material_id
        stock  = sum(i.quantity for i in state.inventory.get(mid, []))
        safety = sum(i.safety_stock for i in state.inventory.get(mid, []))
        pen    = state.catalog.get(mid, type("", (), {"stockout_penalty": 0})()).stockout_penalty
        return (
            f"On-hand ({stock:,.0f} units) is "
            f"{'below' if stock < safety else 'approaching'} safety ({safety:,.0f} units). "
            f"Ordering {action.quantity:,.0f} units from **{action.supplier_id}** costs "
            f"{fmt_usd(action.cost)} and avoids a stockout penalty of {fmt_usd(pen)}/unit."
        )
    if isinstance(action, TransferAction):
        return (
            f"**{action.from_location}** has surplus stock while **{action.to_location}** is "
            f"below safety. Transferring {action.quantity:,.0f} units internally costs only "
            f"{fmt_usd(action.cost)} — far cheaper than a new procurement order."
        )
    if isinstance(action, ExpireAction):
        mid = action.material_id
        pen = state.catalog.get(mid, type("", (), {"expiry_penalty": 0})()).expiry_penalty
        return (
            f"The lot at **{action.location}** expires in ≤3 days. Disposing of "
            f"{action.quantity:,.0f} units now avoids an automatic write-off penalty "
            f"of {fmt_usd(pen)}/unit."
        )
    return (
        "All materials are within acceptable stock bands. No procurement or transfer is "
        "cost-effective today — Do Nothing scored highest across all simulated futures."
    )


# ══════════════════════════════════════════════════════════════════════════════
#  CLAUDE AI  (no Azure — standard Anthropic API)
# ══════════════════════════════════════════════════════════════════════════════

# ── Azure OpenAI configuration ───────────────────────────────────────────────
AZURE_ENDPOINT   = "https://bu24-demo.openai.azure.com/openai/deployments/gpt-4o-mini/chat/completions"
AZURE_API_KEY    = "8pyt1c5txcgWu"
AZURE_API_VERSION = "2025-01-01-preview"

def call_claude(context: dict) -> str:
    """Call Azure OpenAI gpt-4o-mini for supply chain analysis."""
    import urllib.request
    prompt = f"""You are a senior supply chain advisor for a biotech laboratory.

Write a concise business briefing (3 short paragraphs, max 180 words) based on this MCTS planner output:

Paragraph 1 - Decision: Why was this specific action chosen over the alternatives?
Paragraph 2 - Risks: What expiry, stockout, or supplier-delay risks are present right now?
Paragraph 3 - Watch-out: What could go wrong in worst-case scenarios, and what to monitor?

Be specific with numbers. Write for a supply chain manager, not a data scientist.

PLANNER OUTPUT:
{json.dumps(context, indent=2)}
"""
    url = f"{AZURE_ENDPOINT}?api-version={AZURE_API_VERSION}"
    payload = json.dumps({
        "messages": [{"role": "user", "content": prompt}],
        "max_tokens": 500,
        "temperature": 0.3,
    }).encode()
    req = urllib.request.Request(
        url,
        data=payload,
        headers={
            "Content-Type": "application/json",
            "api-key": AZURE_API_KEY,
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            data = json.loads(r.read())
            return data["choices"][0]["message"]["content"].strip()
    except Exception as exc:
        return f"⚠️ Azure OpenAI error: {exc}"


def llm_context(state: SystemState, best_action, top_paths: list) -> dict:
    return {
        "recommended_action":  str(best_action),
        "budget_remaining":    round(state.budget_remaining, 2),
        "service_level_30d":   round(service_level(state), 3),
        "expiring_soon_units": expiring_soon(state),
        "inventory_summary": {
            mid: {
                "on_hand":       round(sum(i.quantity for i in items), 0),
                "safety_stock":  round(sum(i.safety_stock for i in items), 0),
                "expiring_le7d": round(sum(
                    i.quantity for i in items
                    if i.expiry_days is not None and 0 < i.expiry_days <= 7
                ), 0),
            }
            for mid, items in state.inventory.items()
        },
        "top_decision_paths": [
            {"action": p["path"], "mean_reward": p["mean"],
             "cvar": p["cvar"], "risk_score": p["score"], "visits": p["visits"]}
            for p in top_paths[:3]
        ],
    }


# ══════════════════════════════════════════════════════════════════════════════
#  SESSION STATE BOOTSTRAP
# ══════════════════════════════════════════════════════════════════════════════

@st.cache_resource(show_spinner="Loading inventory database…")
def _load() -> SystemState:
    return load_state_from_db()

for _k, _v in [("state", None), ("last_plan", None),
               ("last_scenarios", None), ("sim_log", []), ("ai_text", None)]:
    if _k not in st.session_state:
        st.session_state[_k] = _v

if st.session_state.state is None:
    st.session_state.state = _load()

state: SystemState = st.session_state.state

# ── Backward-compat: older pickled/cached states may be missing these fields ──
if not hasattr(state, "current_day"):
    object.__setattr__(state, "current_day", 0)
if not hasattr(state, "budget_remaining"):
    object.__setattr__(state, "budget_remaining", 100_000.0)
if not hasattr(state, "window_demand"):
    object.__setattr__(state, "window_demand", {})
if not hasattr(state, "window_fulfilled"):
    object.__setattr__(state, "window_fulfilled", {})


# ══════════════════════════════════════════════════════════════════════════════
#  SIDEBAR
# ══════════════════════════════════════════════════════════════════════════════

with st.sidebar:
    st.markdown("## 🧪 Supply Chain AI")
    st.caption(f"Day **{state.current_day}** · Budget **{fmt_usd(state.budget_remaining)}**")
    st.markdown("---")

    sec("Planner Settings")
    horizon     = st.slider("Planning horizon (days)", 3, 14, 7)
    simulations = st.slider("MCTS simulations", 20, 300, 100, step=10,
                             help="More = better quality, but slower.")
    cvar_pct    = st.slider("CVaR tail risk %", 5, 40, 20, step=5,
                             help="Worst N% of scenarios used to penalise risky actions.")

    st.markdown("---")
    sec("Inject Market Event")
    ev_mat  = st.selectbox("Material",   list(state.inventory.keys()), key="ev_mat")
    ev_type = st.selectbox("Event type",
                            ["supply_disruption", "demand_spike", "weather_delay",
                             "promotion", "holiday_slowdown"])
    ev_mult = st.slider("Demand multiplier", 0.0, 2.5, 1.0, step=0.05,
                        help="0 = zero supply  |  1.5 = +50% demand surge")
    ev_dur  = st.slider("Duration (days)", 1, 14, 5)

    if st.button("➕ Add Event"):
        s = state.deep_clone()
        s.market_events = list(s.market_events) + [
            MarketEvent(material_id=ev_mat, multiplier=ev_mult,
                        duration_days=ev_dur, event_type=ev_type)
        ]
        st.session_state.state = s
        st.success(f"Event added for {ev_mat}")
        st.rerun()

    st.markdown("---")
    if st.button("🔄 Reset to Initial State"):
        st.cache_resource.clear()
        for k in ["state", "last_plan", "last_scenarios", "sim_log", "ai_text"]:
            st.session_state.pop(k, None)
        st.rerun()


# ══════════════════════════════════════════════════════════════════════════════
#  HEADER + GLOBAL ALERTS
# ══════════════════════════════════════════════════════════════════════════════

st.markdown("# 🧪 Reagent Supply Chain AI Planner")
st.markdown(
    "*Monte Carlo Tree Search · CVaR Risk Adjustment · "
    "Self-Learning Demand Forecasting · Claude AI Explanations*"
)

_exp = expiring_soon(state)
if _exp > 0:
    st.markdown(
        f'<div class="alert alert-red">⚠️ <strong>Expiry Alert:</strong> {_exp:,.0f} units '
        f'expire within 7 days. Run the planner to evaluate disposal vs. holding.</div>',
        unsafe_allow_html=True,
    )
if state.market_events:
    _evl = ", ".join(sorted({e.event_type for e in state.market_events}))
    st.markdown(
        f'<div class="alert alert-amber">🌩️ <strong>Market Events Active:</strong> {_evl} '
        f'— {len(state.market_events)} event(s) are influencing demand scenarios.</div>',
        unsafe_allow_html=True,
    )
st.markdown("---")


# ══════════════════════════════════════════════════════════════════════════════
#  KPI ROW
# ══════════════════════════════════════════════════════════════════════════════

_sl  = service_level(state)
_val = inv_value(state)
k1, k2, k3, k4, k5 = st.columns(5)
k1.metric("💰 Budget Remaining",    fmt_usd(state.budget_remaining))
k2.metric("📦 Inventory Value",     fmt_usd(_val))
k3.metric("📈 Service Level (30d)", fmt_pct(_sl),
          delta="⚠️ Below target" if _sl < 0.90 else "✅ On target",
          delta_color="inverse" if _sl < 0.90 else "normal")
k4.metric("⏳ Expiring ≤7d",        f"{_exp:,.0f} units",
          delta="Action required" if _exp > 0 else None,
          delta_color="inverse" if _exp > 0 else "normal")
k5.metric("📅 Simulation Day",      state.current_day)

st.markdown("---")


# ══════════════════════════════════════════════════════════════════════════════
#  TABS
# ══════════════════════════════════════════════════════════════════════════════

tab_plan, tab_inv, tab_dem, tab_sup, tab_log = st.tabs([
    "🚀 AI Planner",
    "📦 Inventory",
    "📈 Demand Forecast",
    "🏭 Suppliers",
    "🔄 Simulation Log",
])


# ─────────────────────────────────────────────────────────────────────────────
#  TAB 1 — AI PLANNER
# ─────────────────────────────────────────────────────────────────────────────
with tab_plan:
    left, right = st.columns([1, 2], gap="large")

    # ── Left: material selector + quick stats ─────────────────────────────
    with left:
        sec("Select Material")
        selected = st.selectbox("Material", list(state.inventory.keys()),
                                label_visibility="collapsed")
        items      = state.inventory.get(selected, [])
        total_qty  = sum(i.quantity for i in items)
        total_safe = sum(i.safety_stock for i in items)
        cat        = state.catalog.get(selected)
        cover      = total_qty / max(total_safe, 1)

        _col = "alert-red" if cover < 0.8 else "alert-amber" if cover < 1.0 else "alert-green"
        _lbl = "⚠️ Critical" if cover < 0.8 else "⚡ Low" if cover < 1.0 else "✅ Healthy"
        st.markdown(
            f'<div class="alert {_col}"><strong>{_lbl}</strong>'
            f' — {cover:.1f}× safety stock coverage</div>',
            unsafe_allow_html=True,
        )
        st.markdown(f"""
| | |
|---|---|
| On-hand qty | `{total_qty:,.0f}` |
| Safety stock | `{total_safe:,.0f}` |
| Stockout penalty | `{fmt_usd(cat.stockout_penalty)}/unit` |
| Holding cost | `{fmt_usd(cat.holding_cost_rate)}/unit/day` |
| Expiry penalty | `{fmt_usd(cat.expiry_penalty)}/unit` |
""")
        run_btn = st.button("🚀 Run AI Planner", type="primary", use_container_width=True)

    # ── Right: forecast fan chart ─────────────────────────────────────────
    with right:
        sec("Demand Forecast (Monte Carlo)")
        sg        = ScenarioGenerator(horizon=horizon, n_scenarios=50)
        _scens    = sg.generate(state)
        _summary  = sg.summary(_scens, selected)
        st.session_state.last_scenarios = _scens

        fig_fc = go.Figure()
        for _sc in _scens[:20]:
            fig_fc.add_trace(go.Scatter(
                x=_summary["days"],
                y=[_sc[t].get(selected, 0) for t in range(horizon)],
                mode="lines", line=dict(color="#3b82f6", width=1),
                opacity=0.08, showlegend=False,
            ))
        fig_fc.add_trace(go.Scatter(x=_summary["days"], y=_summary["upper"],
                                    mode="lines", line=dict(width=0), showlegend=False))
        fig_fc.add_trace(go.Scatter(
            x=_summary["days"], y=_summary["lower"],
            mode="lines", fill="tonexty", fillcolor="rgba(59,130,246,0.18)",
            line=dict(width=0), name="±1σ band",
        ))
        fig_fc.add_trace(go.Scatter(
            x=_summary["days"], y=_summary["mean"],
            mode="lines+markers", name="Mean forecast",
            line=dict(color="#3b82f6", width=2.5), marker=dict(size=5),
        ))
        fig_fc.add_hline(
            y=total_qty / max(len(items), 1) / 2.5,
            line_dash="dot", line_color="#ef4444",
            annotation_text="reorder trigger",
            annotation_position="bottom right",
        )
        fig_fc.update_layout(**chart_layout(
            f"{selected} — {horizon}-day forecast", height=310,
        ))
        st.plotly_chart(fig_fc, use_container_width=True)

    # ── Run MCTS ──────────────────────────────────────────────────────────
    if run_btn:
        with st.spinner("Running MCTS search across all demand scenarios…"):
            planner = MCTS(
                ActionGenerator(), _scens,
                simulations=simulations,
                horizon=min(horizon, 5),
                cvar_alpha=cvar_pct / 100,
            )
            best_action, top_paths = planner.search(state)
            st.session_state.last_plan = {"best_action": best_action, "top_paths": top_paths}
            st.session_state.ai_text   = None

    # ── Results ───────────────────────────────────────────────────────────
    if st.session_state.last_plan:
        best  = st.session_state.last_plan["best_action"]
        paths = st.session_state.last_plan["top_paths"]

        st.markdown("---")
        sec("Recommended Action")

        icons = {ProcurementAction: "🛒", TransferAction: "🔀",
                 ExpireAction: "🗑️", DoNothingAction: "✅"}
        icon = icons.get(type(best), "❓")

        st.markdown(
            f'<div class="action-card">'
            f'<h3>{icon} {best}</h3>'
            f'<p>{action_reason(state, best)}</p>'
            f'</div>',
            unsafe_allow_html=True,
        )

        # ── Decision paths scatter ──────────────────────────────────────
        sec("Top Decision Paths Explored by MCTS")
        if paths:
            path_df = pd.DataFrame(paths)
            pc, pt  = st.columns([3, 2], gap="large")

            with pc:
                fig_p = go.Figure(go.Scatter(
                    x=path_df["mean"], y=path_df["cvar"],
                    mode="markers+text",
                    text=path_df["path"].str[:32] + "…",
                    textposition="top center",
                    textfont=dict(size=9, color="#94a3b8"),
                    marker=dict(
                        size=path_df["visits"].clip(6, 55),
                        color=path_df["score"],
                        colorscale="RdYlGn", showscale=True,
                        colorbar=dict(title="Risk Score", tickfont=dict(size=9)),
                        line=dict(color="#0d1b2a", width=1),
                    ),
                    hovertemplate=(
                        "<b>%{text}</b><br>"
                        "Mean reward: %{x:.0f}<br>"
                        "CVaR: %{y:.0f}<extra></extra>"
                    ),
                ))
                fig_p.update_layout(**chart_layout(
                    "Mean Reward vs CVaR  (bubble = visits, colour = risk score)",
                    height=340,
                    xaxis=dict(**GRID, title="Mean Reward ($)"),
                    yaxis=dict(**GRID, title="CVaR — worst tail ($)"),
                ))
                st.plotly_chart(fig_p, use_container_width=True)
                st.caption(
                    "**How to read this:** top-right = high average reward AND "
                    "manageable downside. The recommended action has the highest combined score."
                )

            with pt:
                st.dataframe(
                    path_df[["path", "mean", "cvar", "score", "visits"]].rename(columns={
                        "path": "Action", "mean": "Avg Reward",
                        "cvar": "CVaR", "score": "Risk Score", "visits": "Visits",
                    }),
                    use_container_width=True, height=340,
                )

        # ── Claude AI explanation ───────────────────────────────────────
        st.markdown("---")
        sec("AI Business Analysis")
        ai_c1, ai_c2 = st.columns([3, 1])
        with ai_c1:
            st.markdown(
                "Ask Claude to explain this decision in plain English — "
                "covering risks, trade-offs, and what your team should watch."
            )
        with ai_c2:
            gen_ai = st.button("✨ Generate", use_container_width=True)

        if gen_ai:
            with st.spinner("Asking Claude…"):
                st.session_state.ai_text = call_claude(llm_context(state, best, paths))

        if st.session_state.ai_text:
            st.markdown(
                f'<div class="alert alert-blue">{st.session_state.ai_text}</div>',
                unsafe_allow_html=True,
            )

        # ── Execute ──────────────────────────────────────────────────────
        st.markdown("---")
        sec("Execute & Step Simulation")
        st.markdown(
            "Executing applies the action, simulates one day of demand, "
            "and advances the clock by 1 day."
        )
        ex1, ex2 = st.columns(2)

        with ex1:
            if st.button("✅ Execute Recommended Action", type="primary",
                         use_container_width=True):
                new_s = apply_action(state, best)
                _d = (st.session_state.last_scenarios or [[{}]])[0]
                demand_day = _d[0] if isinstance(_d, list) and _d else (_d if isinstance(_d, dict) else {})
                new_s, reward = step_environment(new_s, demand_day)
                st.session_state.sim_log.append({
                    "Day": state.current_day, "Action": str(best),
                    "Reward ($)": round(reward, 2),
                    "Budget ($)": round(new_s.budget_remaining, 2),
                    "Service Level": fmt_pct(new_s.service_level()),
                })
                st.session_state.state     = new_s
                st.session_state.last_plan = None
                st.session_state.ai_text   = None
                st.rerun()

        with ex2:
            if st.button("⏭️ Step Forward (Do Nothing)", use_container_width=True):
                _d = (st.session_state.last_scenarios or [[{}]])[0]
                demand_day = _d[0] if isinstance(_d, list) and _d else (_d if isinstance(_d, dict) else {})
                new_s, reward = step_environment(state, demand_day)
                st.session_state.sim_log.append({
                    "Day": state.current_day, "Action": "Do Nothing",
                    "Reward ($)": round(reward, 2),
                    "Budget ($)": round(new_s.budget_remaining, 2),
                    "Service Level": fmt_pct(new_s.service_level()),
                })
                st.session_state.state     = new_s
                st.session_state.last_plan = None
                st.rerun()


# ─────────────────────────────────────────────────────────────────────────────
#  TAB 2 — INVENTORY
# ─────────────────────────────────────────────────────────────────────────────
with tab_inv:
    sec("Portfolio Overview")

    inv_rows = []
    for mid, items in state.inventory.items():
        cat_   = state.catalog.get(mid)
        total_ = sum(i.quantity for i in items)
        safe_  = sum(i.safety_stock for i in items)
        exp7_  = sum(i.quantity for i in items
                     if i.expiry_days is not None and 0 < i.expiry_days <= 7)
        min_e  = min((i.expiry_days for i in items if i.expiry_days is not None), default=None)
        cov    = total_ / max(safe_, 1)
        inv_rows.append({
            "Material":             mid,
            "Status":               "🔴 Critical" if cov < 0.8 else "🟡 Low" if cov < 1.0 else "🟢 OK",
            "On-hand":              int(total_),
            "Safety Stock":         int(safe_),
            "Coverage":             f"{cov:.1f}×",
            "Expiring ≤7d (units)": int(exp7_),
            "Min Expiry (days)":    min_e if min_e else "∞",
            "Unit Price ($)":       cat_.unit_price if cat_ else 0,
            "Total Value ($)":      round(total_ * cat_.unit_price, 0) if cat_ else 0,
        })
    inv_df = pd.DataFrame(inv_rows)

    status_filter = st.multiselect("Filter by status",
                                    ["🟢 OK", "🟡 Low", "🔴 Critical"],
                                    default=["🟢 OK", "🟡 Low", "🔴 Critical"])
    filtered_df = inv_df[inv_df["Status"].isin(status_filter)] if status_filter else inv_df
    st.dataframe(filtered_df, use_container_width=True, height=270)

    ch1, ch2 = st.columns(2, gap="large")
    with ch1:
        sec("Portfolio Value by Category")
        inv_df["Category"] = inv_df["Material"].apply(
            lambda m: ("Critical Reagents" if m.startswith("REAG_CRIT")
                       else "Standard Reagents" if m.startswith("REAG_STD")
                       else "Consumables")
        )
        fig_tree = px.treemap(
            inv_df, path=["Category", "Material"],
            values="Total Value ($)", color="Total Value ($)",
            color_continuous_scale="Blues",
        )
        fig_tree.update_layout(height=310, paper_bgcolor="#0d1b2a",
                               font=dict(color="#94a3b8"), margin=dict(t=10, b=0))
        st.plotly_chart(fig_tree, use_container_width=True)

    with ch2:
        sec("Expiry Risk Heatmap")
        exp_rows = [
            {"Material": mid, "Location": item.location,
             "Expiry (days)": item.expiry_days, "Quantity": item.quantity}
            for mid, items in state.inventory.items()
            for item in items if item.expiry_days is not None
        ]
        if exp_rows:
            fig_exp = px.scatter(
                pd.DataFrame(exp_rows),
                x="Expiry (days)", y="Material",
                size="Quantity", color="Expiry (days)",
                color_continuous_scale="RdYlGn",
                symbol="Location", hover_data=["Quantity"],
            )
            fig_exp.add_vline(x=7, line_dash="dash", line_color="#ef4444",
                              annotation_text="7-day alert")
            fig_exp.update_layout(**chart_layout("", height=310))
            st.plotly_chart(fig_exp, use_container_width=True)

    sec("Location Drilldown")
    sel_inv = st.selectbox("Material", list(state.inventory.keys()), key="sel_inv")
    loc_rows = []
    for item in state.inventory.get(sel_inv, []):
        cov = item.quantity / max(item.safety_stock, 1)
        loc_rows.append({
            "Location":      item.location,
            "Quantity":      int(item.quantity),
            "Safety Stock":  int(item.safety_stock),
            "Coverage":      f"{cov:.1f}×",
            "Expiry (days)": item.expiry_days if item.expiry_days else "∞",
            "Status":        "🔴" if cov < 0.8 else "🟡" if cov < 1.0 else "🟢",
        })
    st.dataframe(pd.DataFrame(loc_rows), use_container_width=True)


# ─────────────────────────────────────────────────────────────────────────────
#  TAB 3 — DEMAND FORECAST
# ─────────────────────────────────────────────────────────────────────────────
with tab_dem:
    sec("Historical Demand + Forward Scenarios")
    sel_dem = st.selectbox("Material", list(state.inventory.keys()), key="sel_dem")
    hist    = state.demand_history.get(sel_dem, [])

    if hist:
        _start  = datetime.now() - timedelta(days=len(hist))
        hist_df = pd.DataFrame({
            "Date":   [_start + timedelta(days=i) for i in range(len(hist))],
            "Demand": hist,
        })
        hist_df["7d MA"] = hist_df["Demand"].rolling(7, min_periods=1).mean()
        fig_h = go.Figure()
        fig_h.add_trace(go.Scatter(x=hist_df["Date"], y=hist_df["Demand"],
                                   mode="lines", name="Daily demand",
                                   line=dict(color="#3b82f6", width=1, dash="dot"), opacity=0.45))
        fig_h.add_trace(go.Scatter(x=hist_df["Date"], y=hist_df["7d MA"],
                                   mode="lines", name="7-day avg",
                                   line=dict(color="#f59e0b", width=2)))
        fig_h.update_layout(**chart_layout(
            f"{sel_dem} — 365-day demand history", height=250))
        st.plotly_chart(fig_h, use_container_width=True)

    sg2      = ScenarioGenerator(horizon=horizon, n_scenarios=50)
    scens2   = sg2.generate(state)
    summ2    = sg2.summary(scens2, sel_dem)

    fig_fan = go.Figure()
    for _sc in scens2[:20]:
        fig_fan.add_trace(go.Scatter(
            x=summ2["days"], y=[_sc[t].get(sel_dem, 0) for t in range(horizon)],
            mode="lines", line=dict(color="#3b82f6", width=1),
            opacity=0.09, showlegend=False,
        ))
    fig_fan.add_trace(go.Scatter(x=summ2["days"], y=summ2["upper"],
                                 mode="lines", line=dict(width=0), showlegend=False))
    fig_fan.add_trace(go.Scatter(
        x=summ2["days"], y=summ2["lower"],
        mode="lines", fill="tonexty", fillcolor="rgba(59,130,246,0.18)",
        line=dict(width=0), name="±1σ band",
    ))
    fig_fan.add_trace(go.Scatter(
        x=summ2["days"], y=summ2["mean"],
        mode="lines+markers", name="Mean",
        line=dict(color="#3b82f6", width=3), marker=dict(size=6),
    ))
    fig_fan.update_layout(**chart_layout(
        f"{sel_dem} — 50-scenario Monte Carlo fan ({horizon}-day horizon)", height=310))
    st.plotly_chart(fig_fan, use_container_width=True)

    m1, m2, m3 = st.columns(3)
    m1.metric("Mean forecast / day", f"{np.mean(summ2['mean']):.0f}")
    m2.metric("Peak (upper bound)",  f"{max(summ2['upper']):.0f}")
    m3.metric("Floor (lower bound)", f"{min(summ2['lower']):.0f}")

    mat_evs = [e for e in state.market_events if e.material_id == sel_dem]
    if mat_evs:
        sec("Active Market Events")
        st.dataframe(pd.DataFrame([{
            "Type": e.event_type,
            "Multiplier": f"{e.multiplier:.2f}×",
            "Duration (days)": e.duration_days,
        } for e in mat_evs]), use_container_width=True)


# ─────────────────────────────────────────────────────────────────────────────
#  TAB 4 — SUPPLIERS
# ─────────────────────────────────────────────────────────────────────────────
with tab_sup:
    sec("Supplier Registry")
    sup_rows = []
    for sid, sup in state.suppliers.items():
        cm = sup.__dict__.get("cost_multiplier", 1.0)
        # safe_elt: guard against old SupplierProfile missing the property
        try:
            elt = float(sup.effective_lead_time)
        except Exception:
            elt = float(sup.lead_time_mean)
        sup_rows.append({
            "Supplier ID":          sid,
            "Name":                 sup.name,
            "Lead time (days)":     f"{sup.lead_time_mean:.0f} ± {sup.lead_time_std:.1f}",
            "Reliability":          fmt_pct(sup.reliability),
            "Cost multiplier":      f"{cm:.2f}×",
            "Effective LT (days)":  f"{elt:.1f}",
        })
    st.dataframe(pd.DataFrame(sup_rows), use_container_width=True)

    sec("Lead Time & Reliability Comparison")
    fig_sup = go.Figure()
    for sid, sup in state.suppliers.items():
        rel = sup.reliability
        fig_sup.add_trace(go.Bar(
            name=sup.name, x=[sup.name], y=[sup.lead_time_mean],
            error_y=dict(type="data", array=[sup.lead_time_std]),
            marker_color=f"rgba(59,130,246,{rel:.2f})",
            hovertemplate=(
                f"<b>{sup.name}</b><br>"
                f"Lead time: {sup.lead_time_mean:.0f} ± {sup.lead_time_std:.1f}d<br>"
                f"Reliability: {rel:.0%}<extra></extra>"
            ),
        ))
    fig_sup.update_layout(**chart_layout(
        "Mean lead time ± std dev  (bar opacity = supplier reliability)", height=310,
        yaxis=dict(**GRID, title="Lead time (days)"), showlegend=False,
    ))
    st.plotly_chart(fig_sup, use_container_width=True)

    sec("In-Transit Purchase Orders")
    if state.in_transit:
        st.dataframe(pd.DataFrame([{
            "Material": po.material_id, "Supplier": po.supplier_id,
            "Quantity": po.quantity, "Arrives in (days)": po.eta_days,
        } for po in state.in_transit]), use_container_width=True)
    else:
        st.markdown(
            '<div class="alert alert-green">✅ No open purchase orders in transit.</div>',
            unsafe_allow_html=True,
        )


# ─────────────────────────────────────────────────────────────────────────────
#  TAB 5 — SIMULATION LOG
# ─────────────────────────────────────────────────────────────────────────────
with tab_log:
    sec("Day-by-Day Execution History")

    if not st.session_state.sim_log:
        st.markdown(
            '<div class="alert alert-amber">'
            'No steps yet. Go to the <strong>AI Planner</strong> tab, run the planner, '
            'and execute actions to build a decision history here.'
            '</div>',
            unsafe_allow_html=True,
        )
    else:
        log_df = pd.DataFrame(st.session_state.sim_log)
        st.dataframe(log_df, use_container_width=True)

        log_df["Cumulative"] = log_df["Reward ($)"].cumsum()
        fig_log = go.Figure()
        fig_log.add_trace(go.Bar(
            x=log_df["Day"], y=log_df["Reward ($)"],
            name="Daily reward",
            marker_color=["#22c55e" if r >= 0 else "#ef4444" for r in log_df["Reward ($)"]],
        ))
        fig_log.add_trace(go.Scatter(
            x=log_df["Day"], y=log_df["Cumulative"],
            name="Cumulative reward",
            line=dict(color="#f59e0b", width=2.5), yaxis="y2",
        ))
        fig_log.update_layout(
            **chart_layout("Daily vs Cumulative Reward", height=290),
            yaxis2=dict(title="Cumulative ($)", overlaying="y",
                        side="right", **GRID),
        )
        st.plotly_chart(fig_log, use_container_width=True)

        fig_bud = go.Figure(go.Scatter(
            x=log_df["Day"], y=log_df["Budget ($)"],
            mode="lines+markers", name="Budget",
            line=dict(color="#3b82f6", width=2),
            fill="tozeroy", fillcolor="rgba(59,130,246,0.08)",
        ))
        fig_bud.update_layout(**chart_layout(
            "Remaining Budget Over Time", height=230,
            yaxis=dict(**GRID, title="Budget ($)"),
        ))
        st.plotly_chart(fig_bud, use_container_width=True)

        if st.button("🗑️ Clear Log"):
            st.session_state.sim_log = []
            st.rerun()


# ══════════════════════════════════════════════════════════════════════════════
#  FOOTER
# ══════════════════════════════════════════════════════════════════════════════
st.markdown("---")
st.caption(
    "**Reagent Supply Chain AI Planner** · "
    "MCTS + CVaR Risk Management · "
    "Exponential Smoothing Demand Forecasting · "
    "Anthropic Claude AI · "
    "Streamlit & Plotly"
)