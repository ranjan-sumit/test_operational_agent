# # # from src.core.action import DoNothingAction, ExpireAction, ProcurementAction, TransferAction


# # # class ActionGenerator:
# # #     def generate_all(self, state):
# # #         actions = []

# # #         for mid, items in state.inventory.items():
# # #             total_stock = sum(i.quantity for i in items)
# # #             safety = sum(i.safety_stock for i in items)

# # #             actions.append(DoNothingAction())

# # #             if total_stock < safety * 1.2:
# # #                 for sid, supplier in state.suppliers.items():
# # #                     qty = max(100, int(safety * 1.5))
# # #                     unit_price = state.catalog[mid].unit_price * supplier.cost_multiplier
# # #                     actions.append(ProcurementAction(mid, sid, qty, unit_price))

# # #             for src in items:
# # #                 for dst in items:
# # #                     if src.location == dst.location:
# # #                         continue
# # #                     excess = src.quantity - src.safety_stock
# # #                     deficit = dst.safety_stock - dst.quantity
# # #                     if excess > 0 and deficit > 0:
# # #                         qty = min(excess, deficit)
# # #                         actions.append(TransferAction(mid, src.location, dst.location, qty))

# # #             for item in items:
# # #                 if item.expiry_days <= 3 and item.quantity > 0:
# # #                     actions.append(ExpireAction(mid, item.location, item.quantity))

# # #         unique = {}
# # #         for a in actions:
# # #             unique[repr(a)] = a
# # #         return list(unique.values())

# # """
# # Enumerate all feasible actions for a given SystemState.
# # """
# # from __future__ import annotations
# # from typing import List

# # from src.core.action import DoNothingAction, ExpireAction, ProcurementAction, TransferAction
# # from src.core.state import SystemState

# # QTY_MULTIPLIERS = [0.5, 1.0, 1.5, 2.0]   # multiples of safety stock to order


# # class ActionGenerator:
# #     def generate_all(self, state: SystemState) -> List:
# #         actions = []

# #         for mid, items in state.inventory.items():
# #             cat = state.catalog.get(mid)
# #             if cat is None:
# #                 continue

# #             total_qty = sum(i.quantity for i in items)
# #             total_safety = sum(i.safety_stock for i in items)

# #             # ---- Procurement ----
# #             if total_qty < total_safety * 1.5:
# #                 for sup_id, sup in state.suppliers.items():
# #                     for mult in QTY_MULTIPLIERS:
# #                         qty = total_safety * mult
# #                         cost = qty * cat.unit_price * sup.cost_multiplier if hasattr(sup, "cost_multiplier") else qty * cat.unit_price
# #                         if cost <= state.budget_remaining:
# #                             actions.append(ProcurementAction(
# #                                 material_id=mid,
# #                                 supplier_id=sup_id,
# #                                 quantity=qty,
# #                                 cost=cost,
# #                             ))

# #             # ---- Transfer ----
# #             locs = {i.location: i for i in items}
# #             for src_loc, src_item in locs.items():
# #                 if src_item.quantity > src_item.safety_stock * 1.3:
# #                     for dst_loc, dst_item in locs.items():
# #                         if dst_loc != src_loc and dst_item.quantity < dst_item.safety_stock:
# #                             transfer_qty = min(
# #                                 src_item.quantity - src_item.safety_stock,
# #                                 dst_item.safety_stock - dst_item.quantity,
# #                             )
# #                             if transfer_qty > 0:
# #                                 actions.append(TransferAction(
# #                                     material_id=mid,
# #                                     from_location=src_loc,
# #                                     to_location=dst_loc,
# #                                     quantity=transfer_qty,
# #                                 ))

# #             # ---- Expire (proactive disposal) ----
# #             for item in items:
# #                 if item.expiry_days is not None and 0 < item.expiry_days <= 3 and item.quantity > 0:
# #                     actions.append(ExpireAction(
# #                         material_id=mid,
# #                         location=item.location,
# #                         quantity=item.quantity,
# #                     ))

# #         actions.append(DoNothingAction())
# #         return actions

# """
# Enumerate all feasible actions for a given SystemState.
# """
# from __future__ import annotations
# from typing import List

# from src.core.action import DoNothingAction, ExpireAction, ProcurementAction, TransferAction
# from src.core.state import SystemState

# # Multiples of safety stock to consider ordering
# QTY_MULTIPLIERS = [0.25, 0.5, 1.0, 1.5, 2.0]


# class ActionGenerator:
#     def generate_all(self, state: SystemState) -> List:
#         actions = []
#         seen = set()   # de-duplicate (mid, supplier, qty_rounded)

#         for mid, items in state.inventory.items():
#             cat = state.catalog.get(mid)
#             if cat is None:
#                 continue

#             total_qty    = sum(i.quantity for i in items)
#             total_safety = sum(i.safety_stock for i in items)
#             demand_hist  = state.demand_history.get(mid, [])
#             avg_daily    = (sum(demand_hist[-30:]) / 30) if len(demand_hist) >= 30 else 1.0

#             # ── Procurement ──────────────────────────────────────────────────
#             if total_qty < total_safety * 1.5:
#                 # Candidate quantities: safety-stock multiples + emergency 7-day cover
#                 emergency_qty = avg_daily * 7
#                 candidate_qtys = set()
#                 for mult in QTY_MULTIPLIERS:
#                     candidate_qtys.add(round(total_safety * mult))
#                 candidate_qtys.add(round(emergency_qty))
#                 # Also add a "minimum viable" quantity — cheapest that fits budget
#                 candidate_qtys.add(round(max(emergency_qty * 0.5, 10)))

#                 for sup_id, sup in state.suppliers.items():
#                     cm = sup.__dict__.get("cost_multiplier", 1.0)
#                     for qty in sorted(candidate_qtys):
#                         if qty <= 0:
#                             continue
#                         cost = qty * cat.unit_price * cm
#                         key  = (mid, sup_id, round(qty / 10) * 10)
#                         if cost > state.budget_remaining or key in seen:
#                             continue
#                         seen.add(key)
#                         actions.append(ProcurementAction(
#                             material_id=mid,
#                             supplier_id=sup_id,
#                             quantity=qty,
#                             cost=cost,
#                         ))

#             # ── Transfer ─────────────────────────────────────────────────────
#             locs = {i.location: i for i in items}
#             for src_loc, src_item in locs.items():
#                 if src_item.quantity > src_item.safety_stock * 1.3:
#                     for dst_loc, dst_item in locs.items():
#                         if dst_loc != src_loc and dst_item.quantity < dst_item.safety_stock:
#                             transfer_qty = min(
#                                 src_item.quantity - src_item.safety_stock,
#                                 dst_item.safety_stock - dst_item.quantity,
#                             )
#                             if transfer_qty > 0:
#                                 actions.append(TransferAction(
#                                     material_id=mid,
#                                     from_location=src_loc,
#                                     to_location=dst_loc,
#                                     quantity=transfer_qty,
#                                 ))

#             # ── Expire (proactive disposal) ───────────────────────────────────
#             for item in items:
#                 if item.expiry_days is not None and 0 < item.expiry_days <= 3 and item.quantity > 0:
#                     actions.append(ExpireAction(
#                         material_id=mid,
#                         location=item.location,
#                         quantity=item.quantity,
#                     ))

#         actions.append(DoNothingAction())
#         return actions

"""
Enumerate all feasible actions for a given SystemState.
"""
from __future__ import annotations
from typing import List

from src.core.action import DoNothingAction, ExpireAction, ProcurementAction, TransferAction
from src.core.state import SystemState

# Multiples of safety stock to consider ordering
QTY_MULTIPLIERS = [0.25, 0.5, 1.0, 1.5, 2.0]


class ActionGenerator:
    def generate_all(self, state: SystemState) -> List:
        actions = []
        seen = set()   # de-duplicate (mid, supplier, qty_rounded)

        for mid, items in state.inventory.items():
            cat = state.catalog.get(mid)
            if cat is None:
                continue

            total_qty    = sum(i.quantity for i in items)
            total_safety = sum(i.safety_stock for i in items)
            demand_hist  = state.demand_history.get(mid, [])
            avg_daily    = (sum(demand_hist[-30:]) / 30) if len(demand_hist) >= 30 else 1.0

            # ── Procurement ──────────────────────────────────────────────────
            if total_qty < total_safety * 1.2:  # only when close to safety stock
                # Candidate quantities: safety-stock multiples + emergency 7-day cover
                emergency_qty = avg_daily * 7
                candidate_qtys = set()
                for mult in QTY_MULTIPLIERS:
                    candidate_qtys.add(round(total_safety * mult))
                candidate_qtys.add(round(emergency_qty))
                # Also add a "minimum viable" quantity — cheapest that fits budget
                candidate_qtys.add(round(max(emergency_qty * 0.5, 10)))

                for sup_id, sup in state.suppliers.items():
                    cm = sup.__dict__.get("cost_multiplier", 1.0)
                    for qty in sorted(candidate_qtys):
                        if qty <= 0:
                            continue
                        cost = qty * cat.unit_price * cm
                        key  = (mid, sup_id, round(qty / 10) * 10)
                        if cost > state.budget_remaining or key in seen:
                            continue
                        seen.add(key)
                        actions.append(ProcurementAction(
                            material_id=mid,
                            supplier_id=sup_id,
                            quantity=qty,
                            cost=cost,
                        ))

            # ── Transfer ─────────────────────────────────────────────────────
            locs = {i.location: i for i in items}
            for src_loc, src_item in locs.items():
                if src_item.quantity > src_item.safety_stock * 1.3:
                    for dst_loc, dst_item in locs.items():
                        if dst_loc != src_loc and dst_item.quantity < dst_item.safety_stock:
                            transfer_qty = min(
                                src_item.quantity - src_item.safety_stock,
                                dst_item.safety_stock - dst_item.quantity,
                            )
                            if transfer_qty > 0:
                                actions.append(TransferAction(
                                    material_id=mid,
                                    from_location=src_loc,
                                    to_location=dst_loc,
                                    quantity=transfer_qty,
                                ))

            # ── Expire (proactive disposal) ───────────────────────────────────
            for item in items:
                if item.expiry_days is not None and 0 < item.expiry_days <= 3 and item.quantity > 0:
                    actions.append(ExpireAction(
                        material_id=mid,
                        location=item.location,
                        quantity=item.quantity,
                    ))

        actions.append(DoNothingAction())
        return actions