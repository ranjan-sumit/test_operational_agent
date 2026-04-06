# from dataclasses import dataclass


# @dataclass(frozen=True)
# class ProcurementAction:
#     material_id: str
#     supplier_id: str
#     quantity: float
#     unit_price: float

#     @property
#     def cost(self) -> float:
#         return self.quantity * self.unit_price

#     def __repr__(self) -> str:
#         return f"PROCURE {self.quantity:.0f} of {self.material_id} from {self.supplier_id}"


# @dataclass(frozen=True)
# class TransferAction:
#     material_id: str
#     from_location: str
#     to_location: str
#     quantity: float

#     @property
#     def cost(self) -> float:
#         return 20.0

#     def __repr__(self) -> str:
#         return f"TRANSFER {self.quantity:.0f} of {self.material_id} from {self.from_location} to {self.to_location}"


# @dataclass(frozen=True)
# class ExpireAction:
#     material_id: str
#     location: str
#     quantity: float

#     @property
#     def cost(self) -> float:
#         return 0.0

#     def __repr__(self) -> str:
#         return f"EXPIRE {self.quantity:.0f} of {self.material_id} at {self.location}"


# @dataclass(frozen=True)
# class DoNothingAction:
#     @property
#     def cost(self) -> float:
#         return 0.0

#     def __repr__(self) -> str:
#         return "DO NOTHING"

"""
Action types for the supply chain planner.
Mutable dataclasses with explicit __hash__ so they can be used in sets/dicts.
"""
from __future__ import annotations
from dataclasses import dataclass, field


@dataclass
class ProcurementAction:
    material_id: str
    supplier_id: str
    quantity: float
    cost: float = 0.0

    def __post_init__(self):
        # cost may be set externally by ActionGenerator
        pass

    def __hash__(self):
        return hash((self.__class__.__name__, self.material_id, self.supplier_id, self.quantity))

    def __str__(self):
        return f"Procure {self.quantity:.0f} × {self.material_id} from {self.supplier_id} (${self.cost:,.0f})"


@dataclass
class TransferAction:
    material_id: str
    from_location: str
    to_location: str
    quantity: float
    cost: float = 20.0

    def __hash__(self):
        return hash((self.__class__.__name__, self.material_id, self.from_location, self.to_location))

    def __str__(self):
        return f"Transfer {self.quantity:.0f} × {self.material_id}: {self.from_location} → {self.to_location}"


@dataclass
class ExpireAction:
    material_id: str
    location: str
    quantity: float
    cost: float = 0.0

    def __hash__(self):
        return hash((self.__class__.__name__, self.material_id, self.location))

    def __str__(self):
        return f"Dispose {self.quantity:.0f} expiring units of {self.material_id} @ {self.location}"


@dataclass
class DoNothingAction:
    cost: float = 0.0

    def __hash__(self):
        return hash(self.__class__.__name__)

    def __str__(self):
        return "Do Nothing — current stock position is acceptable"