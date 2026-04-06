# from dataclasses import replace
# from datetime import datetime
# from typing import Any, Tuple

# import numpy as np

# from src.core.action import DoNothingAction, ExpireAction, ProcurementAction, TransferAction
# from src.core.state import InventoryItem, PurchaseOrder, SystemState


# def apply_action(state: SystemState, action: Any) -> SystemState:
#     s = state.deep_clone()

#     if isinstance(action, ProcurementAction):
#         supplier = s.suppliers[action.supplier_id]
#         promised = max(1, int(round(supplier.effective_lead_time())))

#         actual_eta = max(
#             1,
#             int(round(np.random.normal(supplier.lead_time_mean, max(0.5, supplier.lead_time_std))))
#         )
#         if np.random.random() > supplier.reliability:
#             actual_eta += int(np.random.randint(1, 4))

#         po = PurchaseOrder(
#             po_id=f"PO_{np.random.randint(1_000_000_000)}",
#             material_id=action.material_id,
#             supplier_id=action.supplier_id,
#             quantity=action.quantity,
#             eta_days=actual_eta,
#             promised_eta_days=promised,
#             unit_price=action.unit_price,
#             created_at=s.timestamp,
#         )
#         s.in_transit.append(po)
#         s = replace(s, budget_remaining=s.budget_remaining - action.cost)

#     elif isinstance(action, TransferAction):
#         items = s.inventory.get(action.material_id, [])
#         from_item = next((it for it in items if it.location == action.from_location), None)
#         to_item = next((it for it in items if it.location == action.to_location), None)

#         if from_item is not None and from_item.quantity >= action.quantity:
#             new_items = []
#             for item in items:
#                 if item.location == action.from_location:
#                     new_items.append(replace(item, quantity=item.quantity - action.quantity))
#                 elif item.location == action.to_location:
#                     new_items.append(replace(item, quantity=item.quantity + action.quantity))
#                 else:
#                     new_items.append(item)

#             if to_item is None:
#                 new_items.append(
#                     InventoryItem(
#                         location=action.to_location,
#                         quantity=action.quantity,
#                         safety_stock=0,
#                         expiry_days=from_item.expiry_days,
#                     )
#                 )

#             s.inventory[action.material_id] = new_items
#             s = replace(s, budget_remaining=s.budget_remaining - action.cost)

#     elif isinstance(action, ExpireAction):
#         items = s.inventory.get(action.material_id, [])
#         for idx, item in enumerate(items):
#             if item.location == action.location:
#                 items[idx] = replace(item, quantity=max(0.0, item.quantity - action.quantity))
#                 break
#         s.inventory[action.material_id] = items

#     elif isinstance(action, DoNothingAction):
#         pass

#     return s


# def advance_purchase_orders(state: SystemState) -> SystemState:
#     s = state.deep_clone()
#     new_in_transit = []
#     # We need to update suppliers as well, so work on a mutable copy
#     new_suppliers = dict(s.suppliers)

#     for po in s.in_transit:
#         if po.eta_days <= 1:
#             # PO arrives today
#             actual_days = max(1, (s.timestamp - po.created_at).days + 1)
#             delay = max(0, actual_days - po.promised_eta_days)

#             # Update supplier delay history
#             supplier = new_suppliers[po.supplier_id]
#             new_delays = tuple(list(supplier.observed_delays) + [delay])
#             new_suppliers[po.supplier_id] = replace(supplier, observed_delays=new_delays)

#             # Add to inventory
#             inv = s.inventory.get(po.material_id, [])
#             if inv:
#                 inv[0] = replace(inv[0], quantity=inv[0].quantity + po.quantity)
#                 s.inventory[po.material_id] = inv
#             else:
#                 s.inventory[po.material_id] = [
#                     InventoryItem(location="WH1", quantity=po.quantity, safety_stock=0, expiry_days=999)
#                 ]
#         else:
#             # Still in transit, reduce ETA
#             new_in_transit.append(replace(po, eta_days=po.eta_days - 1))

#     # Create a new state with updated in_transit and suppliers
#     return replace(s, in_transit=new_in_transit, suppliers=new_suppliers)


# def age_expiry(state: SystemState) -> Tuple[SystemState, dict]:
#     s = state.deep_clone()
#     expiry_loss = {}

#     for mid, items in s.inventory.items():
#         new_items = []
#         expired_units = 0.0

#         for item in items:
#             if item.quantity <= 0:
#                 new_items.append(item)
#                 continue

#             new_expiry = max(0, item.expiry_days - 1)
#             if new_expiry == 0:
#                 expired_units += item.quantity
#                 new_items.append(replace(item, quantity=0.0, expiry_days=0))
#             else:
#                 new_items.append(replace(item, expiry_days=new_expiry))

#         s.inventory[mid] = new_items
#         expiry_loss[mid] = expired_units

#     return s, expiry_loss

"""
State transition logic.
All functions return a NEW SystemState using dataclasses.replace() — never
mutate the input state directly (FrozenInstanceError-safe).
"""
from __future__ import annotations
import copy
import dataclasses
from typing import Dict, List

from src.core.action import DoNothingAction, ExpireAction, ProcurementAction, TransferAction
from src.core.state import InventoryItem, PurchaseOrder, SystemState


def apply_action(state: SystemState, action) -> SystemState:
    """Apply an action and return a brand-new SystemState. Never mutates input."""
    # Work on plain mutable copies
    inventory  = {k: [copy.copy(i) for i in v] for k, v in state.inventory.items()}
    in_transit = [copy.copy(po) for po in state.in_transit]
    budget     = state.budget_remaining

    if isinstance(action, ProcurementAction):
        po = PurchaseOrder(
            material_id=action.material_id,
            supplier_id=action.supplier_id,
            quantity=action.quantity,
            eta_days=int(state.suppliers[action.supplier_id].effective_lead_time),
        )
        in_transit.append(po)
        budget = max(0.0, budget - action.cost)

    elif isinstance(action, TransferAction):
        mid = action.material_id
        for item in inventory.get(mid, []):
            if item.location == action.from_location:
                item.quantity = max(0.0, item.quantity - action.quantity)
        for item in inventory.get(mid, []):
            if item.location == action.to_location:
                item.quantity += action.quantity
        budget = max(0.0, budget - action.cost)

    elif isinstance(action, ExpireAction):
        mid = action.material_id
        for item in inventory.get(mid, []):
            if item.location == action.location and \
               item.expiry_days is not None and item.expiry_days <= 3:
                item.quantity = 0.0

    # DoNothingAction: no changes needed

    # Build new state via dataclasses.replace() — works whether frozen or not
    try:
        return dataclasses.replace(
            state,
            inventory=inventory,
            in_transit=in_transit,
            budget_remaining=budget,
        )
    except TypeError:
        # Fallback: deep-clone then set attributes directly (non-frozen dataclass)
        s = copy.deepcopy(state)
        s.inventory       = inventory
        s.in_transit      = in_transit
        s.budget_remaining = budget
        return s


def advance_purchase_orders(state: SystemState) -> SystemState:
    """Age all PO ETAs by 1 day; deliver arrived orders to inventory."""
    inventory  = {k: [copy.copy(i) for i in v] for k, v in state.inventory.items()}
    remaining  = []

    for po in state.in_transit:
        po = copy.copy(po)
        po.eta_days -= 1
        if po.eta_days <= 0:
            for item in inventory.get(po.material_id, []):
                item.quantity += po.quantity
                break          # deliver to first location that stocks this material
        else:
            remaining.append(po)

    try:
        return dataclasses.replace(state, inventory=inventory, in_transit=remaining)
    except TypeError:
        s = copy.deepcopy(state)
        s.inventory  = inventory
        s.in_transit = remaining
        return s


def age_expiry(state: SystemState) -> SystemState:
    """Decrement expiry_days for all lots; zero out expired ones."""
    inventory = {k: [copy.copy(i) for i in v] for k, v in state.inventory.items()}
    for items in inventory.values():
        for item in items:
            if item.expiry_days is not None:
                item.expiry_days -= 1
                if item.expiry_days <= 0:
                    item.quantity    = 0.0
                    item.expiry_days = 0

    try:
        return dataclasses.replace(state, inventory=inventory)
    except TypeError:
        s = copy.deepcopy(state)
        s.inventory = inventory
        return s