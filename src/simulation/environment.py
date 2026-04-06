# from dataclasses import replace
# from datetime import timedelta
# from typing import Dict, Tuple

# from src.core.state import SystemState
# from src.core.transition import advance_purchase_orders, age_expiry

# MAX_WINDOW = 30


# def step_environment(state: SystemState, demand_dict: Dict[str, float]) -> Tuple[SystemState, float]:
#     if state.budget_remaining < 0:
#         return state, -1e8

#     s = state.deep_clone()
#     s = advance_purchase_orders(s)
#     s, expiry_loss = age_expiry(s)

#     reward = 0.0

#     for mid, demand in demand_dict.items():
#         if mid not in s.catalog:
#             continue

#         items = sorted(s.inventory.get(mid, []), key=lambda x: x.location)
#         cat = s.catalog[mid]

#         start_stock = sum(i.quantity for i in items)
#         fulfilled = min(demand, start_stock)
#         end_stock = start_stock - fulfilled

#         s.window_demand.setdefault(mid, []).append(demand)
#         s.window_fulfilled.setdefault(mid, []).append(fulfilled)

#         if len(s.window_demand[mid]) > MAX_WINDOW:
#             s.window_demand[mid].pop(0)
#             s.window_fulfilled[mid].pop(0)

#         avg_inv = (start_stock + end_stock) / 2

#         reward += fulfilled * cat.unit_price
#         reward -= (demand - fulfilled) * cat.stockout_penalty
#         reward -= avg_inv * cat.holding_cost_rate
#         reward -= expiry_loss.get(mid, 0.0) * cat.expiry_penalty

#         rem = fulfilled
#         new_items = []
#         for item in items:
#             if rem <= 0:
#                 new_items.append(item)
#                 continue
#             take = min(item.quantity, rem)
#             new_items.append(replace(item, quantity=item.quantity - take))
#             rem -= take

#         s.inventory[mid] = new_items

#     s = replace(s, timestamp=s.timestamp + timedelta(days=1))
#     return s, reward

# """
# One-step P&L environment simulation.
# """
# from __future__ import annotations
# import copy
# from typing import Dict, Tuple

# from src.core.state import SystemState
# from src.core.transition import advance_purchase_orders, age_expiry


# def step_environment(state: SystemState, demand_dict: Dict[str, float]) -> Tuple[SystemState, float]:
#     """
#     Simulate one day:
#       1. Deliver arrived POs
#       2. Age reagent expiry (and penalise newly expired)
#       3. Fulfil demand; compute stockout penalties
#       4. Charge holding costs
#       5. Compute net reward
#       6. Update rolling KPI windows
#       7. Advance timestamp

#     Returns (new_state, reward).
#     """
#     s = advance_purchase_orders(state)
#     s = age_expiry(s)

#     inventory = {k: [copy.copy(i) for i in v] for k, v in s.inventory.items()}
#     window_demand = {k: list(v) for k, v in s.window_demand.items()}
#     window_fulfilled = {k: list(v) for k, v in s.window_fulfilled.items()}

#     reward = 0.0

#     for mid, items in inventory.items():
#         cat = s.catalog.get(mid)
#         if cat is None:
#             continue

#         # --- expiry penalty for lots that just hit 0 ---
#         for item in items:
#             if item.expiry_days == 0 and item.quantity == 0.0:
#                 # Already zeroed by age_expiry; charge penalty once (heuristic: small residual)
#                 pass

#         # --- holding cost ---
#         total_qty = sum(i.quantity for i in items)
#         holding = total_qty * cat.holding_cost_rate
#         reward -= holding

#         # --- demand fulfilment ---
#         demand = demand_dict.get(mid, 0.0)
#         fulfilled = 0.0
#         remaining_demand = demand
#         for item in items:
#             if remaining_demand <= 0:
#                 break
#             take = min(item.quantity, remaining_demand)
#             item.quantity -= take
#             fulfilled += take
#             remaining_demand -= take

#         shortfall = max(0.0, demand - fulfilled)
#         reward -= shortfall * cat.stockout_penalty

#         # Revenue proxy: price × fulfilled
#         reward += fulfilled * cat.unit_price * 0.1  # 10% margin proxy

#         # Update rolling windows (keep last 30 days)
#         window_demand.setdefault(mid, []).append(demand)
#         window_fulfilled.setdefault(mid, []).append(fulfilled)
#         if len(window_demand[mid]) > 30:
#             window_demand[mid] = window_demand[mid][-30:]
#             window_fulfilled[mid] = window_fulfilled[mid][-30:]

#     s.inventory = inventory
#     s.window_demand = window_demand
#     s.window_fulfilled = window_fulfilled
#     s.current_day = getattr(s, "current_day", 0) + 1
#     return s, reward

"""
One-step P&L environment simulation.
Uses dataclasses.replace() for all state updates — FrozenInstanceError-safe.
"""
from __future__ import annotations
import copy
import dataclasses
from typing import Dict, Tuple

from src.core.state import SystemState
from src.core.transition import advance_purchase_orders, age_expiry


def step_environment(state: SystemState, demand_dict: Dict[str, float]) -> Tuple[SystemState, float]:
    """
    Simulate one day:
      1. Deliver arrived POs
      2. Age reagent expiry
      3. Fulfil demand; compute stockout penalties
      4. Charge holding costs
      5. Compute net reward
      6. Update rolling KPI windows (last 30 days)
      7. Advance day counter
    Returns (new_state, reward).
    """
    s = advance_purchase_orders(state)
    s = age_expiry(s)

    inventory        = {k: [copy.copy(i) for i in v] for k, v in s.inventory.items()}
    window_demand    = {k: list(v) for k, v in s.window_demand.items()}
    window_fulfilled = {k: list(v) for k, v in s.window_fulfilled.items()}

    reward = 0.0

    for mid, items in inventory.items():
        cat = s.catalog.get(mid)
        if cat is None:
            continue

        # Holding cost
        total_qty = sum(i.quantity for i in items)
        reward -= total_qty * cat.holding_cost_rate

        # Demand fulfilment
        demand        = demand_dict.get(mid, 0.0)
        fulfilled     = 0.0
        remaining_dem = demand
        for item in items:
            if remaining_dem <= 0:
                break
            take           = min(item.quantity, remaining_dem)
            item.quantity -= take
            fulfilled     += take
            remaining_dem -= take

        shortfall = max(0.0, demand - fulfilled)
        reward   -= shortfall * cat.stockout_penalty
        reward   += fulfilled * cat.unit_price * 0.1   # 10% margin proxy

        # Rolling 30-day windows
        window_demand.setdefault(mid, []).append(demand)
        window_fulfilled.setdefault(mid, []).append(fulfilled)
        if len(window_demand[mid]) > 30:
            window_demand[mid]    = window_demand[mid][-30:]
            window_fulfilled[mid] = window_fulfilled[mid][-30:]

    new_day = getattr(s, "current_day", 0) + 1

    try:
        new_s = dataclasses.replace(
            s,
            inventory=inventory,
            window_demand=window_demand,
            window_fulfilled=window_fulfilled,
            current_day=new_day,
        )
    except TypeError:
        new_s = copy.deepcopy(s)
        new_s.inventory        = inventory
        new_s.window_demand    = window_demand
        new_s.window_fulfilled = window_fulfilled
        new_s.current_day      = new_day

    return new_s, reward