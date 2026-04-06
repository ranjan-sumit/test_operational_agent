# # """
# # Agent Tools — the 5 callable functions exposed to the LLM orchestrator.

# # Each tool returns a plain dict so it can be JSON-serialised into the
# # LLM's tool-result message without any custom serialisation logic.
# # """
# # from __future__ import annotations
# # import copy
# # import sqlite3
# # from datetime import datetime
# # from typing import Any, Dict, List, Optional

# # from src.core.action import (
# #     DoNothingAction, ExpireAction, ProcurementAction, TransferAction,
# # )
# # from src.core.state import MarketEvent, SystemState
# # from src.core.transition import apply_action
# # from src.demand.scenario_generator import ScenarioGenerator
# # from src.planning.action_generator import ActionGenerator
# # from src.planning.mcts import MCTS
# # from src.simulation.environment import step_environment


# # # ── Tool 1: read_inventory ────────────────────────────────────────────────────

# # def read_inventory(state: SystemState) -> Dict[str, Any]:
# #     """
# #     Snapshot of current inventory health.
# #     Returns per-material status including stock coverage, expiry risk, and
# #     whether each material is in alert territory.
# #     """
# #     materials = []
# #     for mid, items in state.inventory.items():
# #         cat        = state.catalog.get(mid)
# #         total_qty  = sum(i.quantity for i in items)
# #         total_safe = sum(i.safety_stock for i in items)
# #         exp_soon   = sum(i.quantity for i in items
# #                          if i.expiry_days is not None and 0 < i.expiry_days <= 7)
# #         min_exp    = min(
# #             (i.expiry_days for i in items if i.expiry_days is not None),
# #             default=None,
# #         )
# #         coverage   = total_qty / max(total_safe, 1)

# #         if coverage < 0.5:
# #             status = "CRITICAL"
# #         elif coverage < 1.0:
# #             status = "LOW"
# #         elif exp_soon > 0:
# #             status = "EXPIRY_RISK"
# #         else:
# #             status = "OK"

# #         materials.append({
# #             "material_id":        mid,
# #             "status":             status,
# #             "on_hand_qty":        round(total_qty, 0),
# #             "safety_stock":       round(total_safe, 0),
# #             "coverage_ratio":     round(coverage, 2),
# #             "expiring_le7d":      round(exp_soon, 0),
# #             "min_expiry_days":    min_exp,
# #             "stockout_penalty":   cat.stockout_penalty if cat else 0,
# #             "unit_price":         cat.unit_price if cat else 0,
# #         })

# #     alerts = [m for m in materials if m["status"] != "OK"]
# #     return {
# #         "day":              state.current_day,
# #         "budget_remaining": round(state.budget_remaining, 2),
# #         "total_materials":  len(materials),
# #         "alerts":           len(alerts),
# #         "materials":        materials,
# #         "active_events":    [
# #             {"material": e.material_id, "type": e.event_type,
# #              "multiplier": e.multiplier, "duration_days": e.duration_days}
# #             for e in state.market_events
# #         ],
# #     }


# # # ── Tool 2: run_mcts_planner ──────────────────────────────────────────────────

# # def run_mcts_planner(
# #     state: SystemState,
# #     material_id: Optional[str] = None,
# #     horizon: int = 7,
# #     simulations: int = 100,
# #     cvar_alpha: float = 0.20,
# # ) -> Dict[str, Any]:
# #     """
# #     Run MCTS planner and return the best action with its risk profile.
# #     If material_id is given, focuses scenario generation on that material;
# #     otherwise plans across all materials.
# #     """
# #     scen_gen  = ScenarioGenerator(horizon=horizon, n_scenarios=50)
# #     scenarios = scen_gen.generate(state)

# #     planner   = MCTS(
# #         ActionGenerator(), scenarios,
# #         simulations=simulations,
# #         horizon=min(horizon, 5),
# #         cvar_alpha=cvar_alpha,
# #     )
# #     best_action, top_paths = planner.search(state)

# #     # Determine autonomy recommendation
# #     score     = top_paths[0]["score"] if top_paths else 0
# #     cost      = getattr(best_action, "cost", 0)

# #     if isinstance(best_action, DoNothingAction):
# #         autonomy = "AUTO_EXECUTE"
# #     elif isinstance(best_action, ExpireAction):
# #         autonomy = "AUTO_EXECUTE"          # always safe to dispose imminently expiring stock
# #     elif score >= 0.0 and cost <= 10_000:
# #         autonomy = "AUTO_EXECUTE"
# #     elif score >= -200 and cost <= 50_000:
# #         autonomy = "ALERT_AND_WAIT"        # send alert, wait for human approval
# #     else:
# #         autonomy = "ESCALATE"              # high cost or low confidence → human decides

# #     return {
# #         "recommended_action": str(best_action),
# #         "action_type":        type(best_action).__name__,
# #         "action_cost":        round(cost, 2),
# #         "risk_score":         round(score, 3),
# #         "autonomy":           autonomy,
# #         "top_paths": [
# #             {
# #                 "action":      p["path"],
# #                 "mean_reward": round(p["mean"], 2),
# #                 "cvar":        round(p["cvar"], 2),
# #                 "risk_score":  round(p["score"], 3),
# #                 "visits":      p["visits"],
# #             }
# #             for p in top_paths[:3]
# #         ],
# #         "_action_obj": best_action,   # internal — stripped before sending to LLM
# #     }


# # # ── Tool 3: execute_action ────────────────────────────────────────────────────

# # def execute_action(
# #     state: SystemState,
# #     action_obj,
# #     scenarios: Optional[List] = None,
# # ) -> Dict[str, Any]:
# #     """
# #     Apply action_obj to state, step the environment by one day.
# #     Returns the new state and the day's P&L reward.
# #     """
# #     new_state = apply_action(state, action_obj)

# #     if scenarios:
# #         demand_today = scenarios[0][0]
# #     else:
# #         # Fall back to mean demand from history
# #         demand_today = {
# #             mid: float(sum(hist[-30:]) / max(len(hist[-30:]), 1))
# #             for mid, hist in state.demand_history.items()
# #         }

# #     new_state, reward = step_environment(new_state, demand_today)

# #     # Compute what changed
# #     old_val = sum(
# #         item.quantity * state.catalog[mid].unit_price
# #         for mid, items in state.inventory.items()
# #         for item in items if mid in state.catalog
# #     )
# #     new_val = sum(
# #         item.quantity * new_state.catalog[mid].unit_price
# #         for mid, items in new_state.inventory.items()
# #         for item in items if mid in new_state.catalog
# #     )

# #     return {
# #         "executed":          str(action_obj),
# #         "day":               new_state.current_day,
# #         "reward":            round(reward, 2),
# #         "budget_remaining":  round(new_state.budget_remaining, 2),
# #         "inventory_value_delta": round(new_val - old_val, 2),
# #         "new_service_level": round(new_state.service_level(), 3),
# #         "_new_state":        new_state,   # internal
# #     }


# # # ── Tool 4: send_alert ────────────────────────────────────────────────────────

# # def send_alert(
# #     message: str,
# #     level: str = "INFO",          # INFO | WARNING | CRITICAL
# #     channel: str = "supply_chain",
# #     action_required: bool = False,
# #     recommended_action: str = "",
# # ) -> Dict[str, Any]:
# #     """
# #     In production this would POST to Slack / Teams / email.
# #     For the demo it returns a structured alert that the UI renders.
# #     """
# #     alert = {
# #         "timestamp":          datetime.now().isoformat(timespec="seconds"),
# #         "level":              level,
# #         "channel":            channel,
# #         "message":            message,
# #         "action_required":    action_required,
# #         "recommended_action": recommended_action,
# #     }
# #     return alert


# # # ── Tool 5: log_decision ──────────────────────────────────────────────────────

# # def log_decision(
# #     db_path: str,
# #     day: int,
# #     action: str,
# #     action_type: str,
# #     autonomy: str,
# #     risk_score: float,
# #     cost: float,
# #     reward: float,
# #     reasoning: str,
# #     human_override: bool = False,
# #     override_reason: str = "",
# # ) -> Dict[str, Any]:
# #     """
# #     Persist agent decision to the memory SQLite table.
# #     Creates the table on first call.
# #     """
# #     conn = sqlite3.connect(db_path)
# #     conn.execute("""
# #         CREATE TABLE IF NOT EXISTS agent_memory (
# #             id             INTEGER PRIMARY KEY AUTOINCREMENT,
# #             timestamp      TEXT,
# #             day            INTEGER,
# #             action         TEXT,
# #             action_type    TEXT,
# #             autonomy       TEXT,
# #             risk_score     REAL,
# #             cost           REAL,
# #             reward         REAL,
# #             reasoning      TEXT,
# #             human_override INTEGER DEFAULT 0,
# #             override_reason TEXT DEFAULT ''
# #         )
# #     """)
# #     conn.execute("""
# #         INSERT INTO agent_memory
# #         (timestamp, day, action, action_type, autonomy, risk_score,
# #          cost, reward, reasoning, human_override, override_reason)
# #         VALUES (?,?,?,?,?,?,?,?,?,?,?)
# #     """, (
# #         datetime.now().isoformat(timespec="seconds"),
# #         day, action, action_type, autonomy,
# #         round(risk_score, 4), round(cost, 2), round(reward, 2),
# #         reasoning, int(human_override), override_reason,
# #     ))
# #     conn.commit()
# #     conn.close()
# #     return {"logged": True, "day": day, "action": action}


# """
# Agent Tools — the 5 callable functions exposed to the LLM orchestrator.

# Each tool returns a plain dict so it can be JSON-serialised into the
# LLM's tool-result message without any custom serialisation logic.
# """
# from __future__ import annotations
# import copy
# import sqlite3
# from datetime import datetime
# from typing import Any, Dict, List, Optional

# from src.core.action import (
#     DoNothingAction, ExpireAction, ProcurementAction, TransferAction,
# )
# from src.core.state import MarketEvent, SystemState
# from src.core.transition import apply_action
# from src.demand.scenario_generator import ScenarioGenerator
# from src.planning.action_generator import ActionGenerator
# from src.planning.mcts import MCTS
# from src.simulation.environment import step_environment


# # ── Tool 1: read_inventory ────────────────────────────────────────────────────

# def read_inventory(state: SystemState) -> Dict[str, Any]:
#     """
#     Snapshot of current inventory health.
#     Returns per-material status including stock coverage, expiry risk, and
#     whether each material is in alert territory.
#     """
#     materials = []
#     for mid, items in state.inventory.items():
#         cat        = state.catalog.get(mid)
#         total_qty  = sum(i.quantity for i in items)
#         total_safe = sum(i.safety_stock for i in items)
#         exp_soon   = sum(i.quantity for i in items
#                          if i.expiry_days is not None and 0 < i.expiry_days <= 7)
#         min_exp    = min(
#             (i.expiry_days for i in items if i.expiry_days is not None),
#             default=None,
#         )
#         coverage   = total_qty / max(total_safe, 1)

#         if coverage < 0.5:
#             status = "CRITICAL"
#         elif coverage < 1.0:
#             status = "LOW"
#         elif exp_soon > 0:
#             status = "EXPIRY_RISK"
#         else:
#             status = "OK"

#         materials.append({
#             "material_id":        mid,
#             "status":             status,
#             "on_hand_qty":        round(total_qty, 0),
#             "safety_stock":       round(total_safe, 0),
#             "coverage_ratio":     round(coverage, 2),
#             "expiring_le7d":      round(exp_soon, 0),
#             "min_expiry_days":    min_exp,
#             "stockout_penalty":   cat.stockout_penalty if cat else 0,
#             "unit_price":         cat.unit_price if cat else 0,
#         })

#     alerts = [m for m in materials if m["status"] != "OK"]
#     return {
#         "day":              state.current_day,
#         "budget_remaining": round(state.budget_remaining, 2),
#         "total_materials":  len(materials),
#         "alerts":           len(alerts),
#         "materials":        materials,
#         "active_events":    [
#             {"material": e.material_id, "type": e.event_type,
#              "multiplier": e.multiplier, "duration_days": e.duration_days}
#             for e in state.market_events
#         ],
#     }


# # ── Tool 2: run_mcts_planner ──────────────────────────────────────────────────

# def run_mcts_planner(
#     state: SystemState,
#     material_id: Optional[str] = None,
#     horizon: int = 7,
#     simulations: int = 100,
#     cvar_alpha: float = 0.20,
#     material_filter: Optional[str] = None,
# ) -> Dict[str, Any]:
#     """
#     Run MCTS planner and return the best action with its risk profile.
#     If material_id is given, focuses scenario generation on that material;
#     otherwise plans across all materials.
#     """
#     # If filtering to one material, clone state with only that material's inventory
#     # so MCTS focuses actions and scenarios on it exclusively
#     plan_state = state
#     if material_filter and material_filter in state.inventory:
#         plan_state = state.deep_clone()
#         plan_state.inventory = {
#             k: v for k, v in plan_state.inventory.items()
#             if k == material_filter
#         }

#     scen_gen  = ScenarioGenerator(horizon=horizon, n_scenarios=50)
#     scenarios = scen_gen.generate(plan_state)

#     planner   = MCTS(
#         ActionGenerator(), scenarios,
#         simulations=simulations,
#         horizon=min(horizon, 5),
#         cvar_alpha=cvar_alpha,
#     )
#     best_action, top_paths = planner.search(plan_state)

#     # Determine autonomy recommendation
#     score     = top_paths[0]["score"] if top_paths else 0
#     cost      = getattr(best_action, "cost", 0)

#     if isinstance(best_action, DoNothingAction):
#         autonomy = "AUTO_EXECUTE"
#     elif isinstance(best_action, ExpireAction):
#         autonomy = "AUTO_EXECUTE"          # always safe to dispose imminently expiring stock
#     elif score >= 0.0 and cost <= 10_000:
#         autonomy = "AUTO_EXECUTE"
#     elif score >= -200 and cost <= 50_000:
#         autonomy = "ALERT_AND_WAIT"        # send alert, wait for human approval
#     else:
#         autonomy = "ESCALATE"              # high cost or low confidence → human decides

#     return {
#         "recommended_action": str(best_action),
#         "action_type":        type(best_action).__name__,
#         "action_cost":        round(cost, 2),
#         "risk_score":         round(score, 3),
#         "autonomy":           autonomy,
#         "top_paths": [
#             {
#                 "action":      p["path"],
#                 "mean_reward": round(p["mean"], 2),
#                 "cvar":        round(p["cvar"], 2),
#                 "risk_score":  round(p["score"], 3),
#                 "visits":      p["visits"],
#             }
#             for p in top_paths[:3]
#         ],
#         "_action_obj": best_action,   # internal — stripped before sending to LLM
#     }


# # ── Tool 3: execute_action ────────────────────────────────────────────────────

# def execute_action(
#     state: SystemState,
#     action_obj,
#     scenarios: Optional[List] = None,
# ) -> Dict[str, Any]:
#     """
#     Apply action_obj to state, step the environment by one day.
#     Returns the new state and the day's P&L reward.
#     """
#     new_state = apply_action(state, action_obj)

#     if scenarios:
#         demand_today = scenarios[0][0]
#     else:
#         # Fall back to mean demand from history
#         demand_today = {
#             mid: float(sum(hist[-30:]) / max(len(hist[-30:]), 1))
#             for mid, hist in state.demand_history.items()
#         }

#     new_state, reward = step_environment(new_state, demand_today)

#     # Compute what changed
#     old_val = sum(
#         item.quantity * state.catalog[mid].unit_price
#         for mid, items in state.inventory.items()
#         for item in items if mid in state.catalog
#     )
#     new_val = sum(
#         item.quantity * new_state.catalog[mid].unit_price
#         for mid, items in new_state.inventory.items()
#         for item in items if mid in new_state.catalog
#     )

#     return {
#         "executed":          str(action_obj),
#         "day":               new_state.current_day,
#         "reward":            round(reward, 2),
#         "budget_remaining":  round(new_state.budget_remaining, 2),
#         "inventory_value_delta": round(new_val - old_val, 2),
#         "new_service_level": round(new_state.service_level(), 3),
#         "_new_state":        new_state,   # internal
#     }


# # ── Tool 4: send_alert ────────────────────────────────────────────────────────

# def send_alert(
#     message: str,
#     level: str = "INFO",          # INFO | WARNING | CRITICAL
#     channel: str = "supply_chain",
#     action_required: bool = False,
#     recommended_action: str = "",
# ) -> Dict[str, Any]:
#     """
#     In production this would POST to Slack / Teams / email.
#     For the demo it returns a structured alert that the UI renders.
#     """
#     alert = {
#         "timestamp":          datetime.now().isoformat(timespec="seconds"),
#         "level":              level,
#         "channel":            channel,
#         "message":            message,
#         "action_required":    action_required,
#         "recommended_action": recommended_action,
#     }
#     return alert


# # ── Tool 5: log_decision ──────────────────────────────────────────────────────

# def log_decision(
#     db_path: str,
#     day: int,
#     action: str,
#     action_type: str,
#     autonomy: str,
#     risk_score: float,
#     cost: float,
#     reward: float,
#     reasoning: str,
#     human_override: bool = False,
#     override_reason: str = "",
# ) -> Dict[str, Any]:
#     """
#     Persist agent decision to the memory SQLite table.
#     Creates the table on first call.
#     """
#     conn = sqlite3.connect(db_path)
#     conn.execute("""
#         CREATE TABLE IF NOT EXISTS agent_memory (
#             id             INTEGER PRIMARY KEY AUTOINCREMENT,
#             timestamp      TEXT,
#             day            INTEGER,
#             action         TEXT,
#             action_type    TEXT,
#             autonomy       TEXT,
#             risk_score     REAL,
#             cost           REAL,
#             reward         REAL,
#             reasoning      TEXT,
#             human_override INTEGER DEFAULT 0,
#             override_reason TEXT DEFAULT ''
#         )
#     """)
#     conn.execute("""
#         INSERT INTO agent_memory
#         (timestamp, day, action, action_type, autonomy, risk_score,
#          cost, reward, reasoning, human_override, override_reason)
#         VALUES (?,?,?,?,?,?,?,?,?,?,?)
#     """, (
#         datetime.now().isoformat(timespec="seconds"),
#         day, action, action_type, autonomy,
#         round(risk_score, 4), round(cost, 2), round(reward, 2),
#         reasoning, int(human_override), override_reason,
#     ))
#     conn.commit()
#     conn.close()
#     return {"logged": True, "day": day, "action": action}

"""
Agent Tools — the 5 callable functions exposed to the LLM orchestrator.

Each tool returns a plain dict so it can be JSON-serialised into the
LLM's tool-result message without any custom serialisation logic.
"""
from __future__ import annotations
import copy
import sqlite3
from datetime import datetime
from typing import Any, Dict, List, Optional

from src.core.action import (
    DoNothingAction, ExpireAction, ProcurementAction, TransferAction,
)
from src.core.state import MarketEvent, SystemState
from src.core.transition import apply_action
from src.demand.scenario_generator import ScenarioGenerator
from src.planning.action_generator import ActionGenerator
from src.planning.mcts import MCTS
from src.simulation.environment import step_environment


# ── Tool 1: read_inventory ────────────────────────────────────────────────────

def read_inventory(state: SystemState) -> Dict[str, Any]:
    """
    Snapshot of current inventory health.
    Returns per-material status including stock coverage, expiry risk, and
    whether each material is in alert territory.
    """
    materials = []
    for mid, items in state.inventory.items():
        cat        = state.catalog.get(mid)
        total_qty  = sum(i.quantity for i in items)
        total_safe = sum(i.safety_stock for i in items)
        exp_soon   = sum(i.quantity for i in items
                         if i.expiry_days is not None and 0 < i.expiry_days <= 7)
        min_exp    = min(
            (i.expiry_days for i in items if i.expiry_days is not None),
            default=None,
        )
        coverage   = total_qty / max(total_safe, 1)

        if coverage < 0.5:
            status = "CRITICAL"
        elif coverage < 1.0:
            status = "LOW"
        elif exp_soon > 0:
            status = "EXPIRY_RISK"
        else:
            status = "OK"

        materials.append({
            "material_id":        mid,
            "status":             status,
            "on_hand_qty":        round(total_qty, 0),
            "safety_stock":       round(total_safe, 0),
            "coverage_ratio":     round(coverage, 2),
            "expiring_le7d":      round(exp_soon, 0),
            "min_expiry_days":    min_exp,
            "stockout_penalty":   cat.stockout_penalty if cat else 0,
            "unit_price":         cat.unit_price if cat else 0,
        })

    alerts = [m for m in materials if m["status"] != "OK"]
    return {
        "day":              state.current_day,
        "budget_remaining": round(state.budget_remaining, 2),
        "total_materials":  len(materials),
        "alerts":           len(alerts),
        "materials":        materials,
        "active_events":    [
            {"material": e.material_id, "type": e.event_type,
             "multiplier": e.multiplier, "duration_days": e.duration_days}
            for e in state.market_events
        ],
    }


# ── Tool 2: run_mcts_planner ──────────────────────────────────────────────────

def run_mcts_planner(
    state: SystemState,
    material_id: Optional[str] = None,
    horizon: int = 7,
    simulations: int = 150,
    cvar_alpha: float = 0.20,
    material_filter: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Run MCTS planner and return the best action with its risk profile.
    If material_id is given, focuses scenario generation on that material;
    otherwise plans across all materials.
    """
    # If filtering to one material, clone state with only that material's inventory
    # so MCTS focuses actions and scenarios on it exclusively
    plan_state = state
    if material_filter and material_filter in state.inventory:
        plan_state = state.deep_clone()
        plan_state.inventory = {
            k: v for k, v in plan_state.inventory.items()
            if k == material_filter
        }

    scen_gen  = ScenarioGenerator(horizon=horizon, n_scenarios=50)
    scenarios = scen_gen.generate(plan_state)

    planner   = MCTS(
        ActionGenerator(), scenarios,
        simulations=simulations,
        horizon=min(horizon, 5),
        cvar_alpha=cvar_alpha,
    )
    best_action, top_paths = planner.search(plan_state)

    # Determine autonomy recommendation
    score     = top_paths[0]["score"] if top_paths else 0
    cost      = getattr(best_action, "cost", 0)

    if isinstance(best_action, DoNothingAction):
        autonomy = "AUTO_EXECUTE"
    elif isinstance(best_action, ExpireAction):
        autonomy = "AUTO_EXECUTE"          # always safe to dispose imminently expiring stock
    elif score >= 0.0 and cost <= 10_000:
        autonomy = "AUTO_EXECUTE"
    elif score >= -200 and cost <= 50_000:
        autonomy = "ALERT_AND_WAIT"        # send alert, wait for human approval
    else:
        autonomy = "ESCALATE"              # high cost or low confidence → human decides

    return {
        "recommended_action": str(best_action),
        "action_type":        type(best_action).__name__,
        "action_cost":        round(cost, 2),
        "risk_score":         round(score, 3),
        "autonomy":           autonomy,
        "top_paths": [
            {
                "action":      p["path"],
                "mean_reward": round(p["mean"], 2),
                "cvar":        round(p["cvar"], 2),
                "risk_score":  round(p["score"], 3),
                "visits":      p["visits"],
            }
            for p in top_paths[:3]
        ],
        "_action_obj": best_action,   # internal — stripped before sending to LLM
    }


# ── Tool 3: execute_action ────────────────────────────────────────────────────

def execute_action(
    state: SystemState,
    action_obj,
    scenarios: Optional[List] = None,
) -> Dict[str, Any]:
    """
    Apply action_obj to state, step the environment by one day.
    Returns the new state and the day's P&L reward.
    """
    new_state = apply_action(state, action_obj)

    if scenarios:
        demand_today = scenarios[0][0]
    else:
        # Fall back to mean demand from history
        demand_today = {
            mid: float(sum(hist[-30:]) / max(len(hist[-30:]), 1))
            for mid, hist in state.demand_history.items()
        }

    new_state, reward = step_environment(new_state, demand_today)

    # Compute what changed
    old_val = sum(
        item.quantity * state.catalog[mid].unit_price
        for mid, items in state.inventory.items()
        for item in items if mid in state.catalog
    )
    new_val = sum(
        item.quantity * new_state.catalog[mid].unit_price
        for mid, items in new_state.inventory.items()
        for item in items if mid in new_state.catalog
    )

    return {
        "executed":          str(action_obj),
        "day":               new_state.current_day,
        "reward":            round(reward, 2),
        "budget_remaining":  round(new_state.budget_remaining, 2),
        "inventory_value_delta": round(new_val - old_val, 2),
        "new_service_level": round(new_state.service_level(), 3),
        "_new_state":        new_state,   # internal
    }


# ── Tool 4: send_alert ────────────────────────────────────────────────────────

def send_alert(
    message: str,
    level: str = "INFO",          # INFO | WARNING | CRITICAL
    channel: str = "supply_chain",
    action_required: bool = False,
    recommended_action: str = "",
) -> Dict[str, Any]:
    """
    In production this would POST to Slack / Teams / email.
    For the demo it returns a structured alert that the UI renders.
    """
    alert = {
        "timestamp":          datetime.now().isoformat(timespec="seconds"),
        "level":              level,
        "channel":            channel,
        "message":            message,
        "action_required":    action_required,
        "recommended_action": recommended_action,
    }
    return alert


# ── Tool 5: log_decision ──────────────────────────────────────────────────────

def log_decision(
    db_path: str,
    day: int,
    action: str,
    action_type: str,
    autonomy: str,
    risk_score: float,
    cost: float,
    reward: float,
    reasoning: str,
    human_override: bool = False,
    override_reason: str = "",
) -> Dict[str, Any]:
    """
    Persist agent decision to the memory SQLite table.
    Creates the table on first call.
    """
    conn = sqlite3.connect(db_path)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS agent_memory (
            id             INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp      TEXT,
            day            INTEGER,
            action         TEXT,
            action_type    TEXT,
            autonomy       TEXT,
            risk_score     REAL,
            cost           REAL,
            reward         REAL,
            reasoning      TEXT,
            human_override INTEGER DEFAULT 0,
            override_reason TEXT DEFAULT ''
        )
    """)
    conn.execute("""
        INSERT INTO agent_memory
        (timestamp, day, action, action_type, autonomy, risk_score,
         cost, reward, reasoning, human_override, override_reason)
        VALUES (?,?,?,?,?,?,?,?,?,?,?)
    """, (
        datetime.now().isoformat(timespec="seconds"),
        day, action, action_type, autonomy,
        round(risk_score, 4), round(cost, 2), round(reward, 2),
        reasoning, int(human_override), override_reason,
    ))
    conn.commit()
    conn.close()
    return {"logged": True, "day": day, "action": action}