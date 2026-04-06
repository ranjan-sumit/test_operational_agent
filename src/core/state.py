# import copy
# from dataclasses import dataclass, field, replace
# from datetime import datetime
# from typing import Any, Dict, List, Tuple


# @dataclass(frozen=True)
# class InventoryItem:
#     location: str
#     quantity: float
#     safety_stock: float
#     expiry_days: int = 999


# @dataclass(frozen=True)
# class PurchaseOrder:
#     po_id: str
#     material_id: str
#     supplier_id: str
#     quantity: float
#     eta_days: int
#     promised_eta_days: int
#     unit_price: float
#     created_at: datetime


# @dataclass(frozen=True)
# class SupplierProfile:
#     name: str
#     lead_time_mean: float
#     lead_time_std: float
#     reliability: float
#     cost_multiplier: float
#     observed_delays: Tuple[int, ...] = ()

#     def effective_lead_time(self) -> float:
#         if not self.observed_delays:
#             return self.lead_time_mean
#         avg_delay = sum(self.observed_delays) / len(self.observed_delays)
#         return max(1.0, self.lead_time_mean + avg_delay)


# @dataclass(frozen=True)
# class MaterialCatalog:
#     unit_price: float
#     stockout_penalty: float
#     holding_cost_rate: float
#     expiry_penalty: float = 0.0


# @dataclass(frozen=True)
# class MarketEvent:
#     material_id: str
#     multiplier: float
#     duration_days: int
#     start_day: int = 0
#     event_type: str = "demand"


# @dataclass(frozen=True)
# class SystemState:
#     timestamp: datetime
#     inventory: Dict[str, List[InventoryItem]]
#     in_transit: List[PurchaseOrder]
#     suppliers: Dict[str, SupplierProfile]
#     catalog: Dict[str, MaterialCatalog]
#     demand_history: Dict[str, List[float]]
#     market_events: List[MarketEvent]
#     budget_remaining: float
#     window_demand: Dict[str, List[float]] = field(default_factory=dict)
#     window_fulfilled: Dict[str, List[float]] = field(default_factory=dict)

#     def deep_clone(self):
#         return SystemState(
#             timestamp=self.timestamp,
#             inventory={k: [replace(i) for i in v] for k, v in self.inventory.items()},
#             in_transit=[replace(po) for po in self.in_transit],
#             suppliers={k: replace(v, observed_delays=tuple(v.observed_delays)) for k, v in self.suppliers.items()},
#             catalog={k: replace(v) for k, v in self.catalog.items()},
#             demand_history={k: v[:] for k, v in self.demand_history.items()},
#             market_events=copy.deepcopy(self.market_events),
#             budget_remaining=self.budget_remaining,
#             window_demand={k: v[:] for k, v in self.window_demand.items()},
#             window_fulfilled={k: v[:] for k, v in self.window_fulfilled.items()},
#         )

"""
Core immutable state objects for the supply chain planner.
All mutations follow the mutable-copy → dataclasses.replace() pattern.
"""
from __future__ import annotations
import copy
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple


@dataclass
class InventoryItem:
    location: str
    quantity: float
    safety_stock: float
    expiry_days: Optional[int] = None  # None = does not expire

    def is_expiring_soon(self, threshold: int = 7) -> bool:
        return self.expiry_days is not None and 0 < self.expiry_days <= threshold


@dataclass
class SupplierProfile:
    name: str
    lead_time_mean: float
    lead_time_std: float
    reliability: float  # fraction of orders on time
    observed_delays: Tuple[float, ...] = field(default_factory=tuple)  # MUST be tuple for hashability

    @property
    def effective_lead_time(self) -> float:
        """Bayesian blend of prior and observed delays."""
        if len(self.observed_delays) == 0:
            return self.lead_time_mean
        obs_mean = sum(self.observed_delays) / len(self.observed_delays)
        weight = min(len(self.observed_delays) / 10.0, 0.7)
        return (1 - weight) * self.lead_time_mean + weight * obs_mean


@dataclass
class MaterialCatalog:
    unit_price: float
    stockout_penalty: float
    holding_cost_rate: float   # $/unit/day
    expiry_penalty: float = 0.0


@dataclass
class PurchaseOrder:
    material_id: str
    supplier_id: str
    quantity: float
    eta_days: int    # decrements each step; delivered when 0


@dataclass
class MarketEvent:
    material_id: str
    multiplier: float
    duration_days: int
    event_type: str = "demand"   # "demand" | "supply_disruption" | "weather_delay"


@dataclass
class SystemState:
    # Inventory: material_id → list of InventoryItem (one per location)
    inventory: Dict[str, List[InventoryItem]]
    # Supplier registry
    suppliers: Dict[str, SupplierProfile]
    # Material financial parameters
    catalog: Dict[str, MaterialCatalog]
    # In-transit purchase orders
    in_transit: List[PurchaseOrder] = field(default_factory=list)
    # Active market events
    market_events: List[MarketEvent] = field(default_factory=list)
    # Historical demand: material_id → list of daily demand floats
    demand_history: Dict[str, List[float]] = field(default_factory=dict)
    # Rolling 30-day windows for KPI computation
    window_demand: Dict[str, List[float]] = field(default_factory=dict)
    window_fulfilled: Dict[str, List[float]] = field(default_factory=dict)

    budget_remaining: float = 50_000.0
    current_day: int = 0

    def deep_clone(self) -> "SystemState":
        return copy.deepcopy(self)

    def service_level(self, material_id: Optional[str] = None) -> float:
        mids = [material_id] if material_id else list(self.inventory.keys())
        vals = []
        for mid in mids:
            d = sum(self.window_demand.get(mid, []))
            f = sum(self.window_fulfilled.get(mid, []))
            vals.append(f / d if d > 0 else 1.0)
        return float(sum(vals) / len(vals)) if vals else 1.0

    def expiring_soon(self, days: int = 7) -> float:
        return float(sum(
            item.quantity
            for items in self.inventory.values()
            for item in items
            if item.expiry_days is not None and 0 < item.expiry_days <= days
        ))

    def total_inventory_value(self) -> float:
        return sum(
            item.quantity * self.catalog[mid].unit_price
            for mid, items in self.inventory.items()
            for item in items
            if mid in self.catalog
        )