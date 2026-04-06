# import numpy as np
# from typing import Dict, List

# from src.core.state import SystemState


# class ScenarioGenerator:
#     def __init__(self, horizon: int = 7, n_scenarios: int = 30, alpha: float = 0.3):
#         self.horizon = horizon
#         self.n_scenarios = n_scenarios
#         self.alpha = alpha

#     def _exp_smooth_params(self, history: List[float]):
#         if not history:
#             return 400.0, 50.0
#         level = history[0]
#         for val in history[1:]:
#             level = self.alpha * val + (1 - self.alpha) * level
#         std = np.std(history) if len(history) > 1 else 50.0
#         return float(level), float(max(1.0, std))

#     def generate(self, state: SystemState):
#         demand_models: Dict[str, tuple[float, float]] = {}
#         for mid, hist in state.demand_history.items():
#             demand_models[mid] = self._exp_smooth_params(hist)

#         scenarios = []
#         for _ in range(self.n_scenarios):
#             traj = []
#             for day in range(self.horizon):
#                 daily = {}
#                 for mid, (mu, sigma) in demand_models.items():
#                     val = max(0.0, np.random.normal(mu, sigma))

#                     for ev in state.market_events:
#                         if ev.material_id == mid and ev.start_day <= day < ev.start_day + ev.duration_days:
#                             val *= ev.multiplier

#                     daily[mid] = float(val)
#                 traj.append(daily)
#             scenarios.append(traj)

#         return scenarios

"""
Stochastic demand scenario generator.
Uses exponential smoothing fitted from actual demand_history.
Market events inject demand multipliers per material.
"""
from __future__ import annotations
from typing import Dict, List, Tuple

import numpy as np

from src.core.state import SystemState


class ScenarioGenerator:
    def __init__(self, horizon: int = 7, n_scenarios: int = 30, alpha: float = 0.3):
        self.horizon = horizon
        self.n_scenarios = n_scenarios
        self.alpha = alpha

    # ------------------------------------------------------------------ #
    def _exp_smooth_params(self, history: List[float]) -> Tuple[float, float]:
        """Return (smoothed_mean, std) from demand history via exp smoothing."""
        if not history:
            return 100.0, 20.0
        level = float(history[0])
        for obs in history[1:]:
            level = self.alpha * obs + (1 - self.alpha) * level
        if len(history) > 1:
            residuals = [abs(history[i] - level) for i in range(len(history))]
            std = max(1.0, float(np.mean(residuals[-30:])))
        else:
            std = max(1.0, level * 0.15)
        return level, std

    def _event_multiplier(self, state: SystemState, material_id: str, day_offset: int) -> float:
        mult = 1.0
        for ev in state.market_events:
            if ev.material_id == material_id and day_offset < ev.duration_days:
                mult *= ev.multiplier
        return mult

    # ------------------------------------------------------------------ #
    def generate(self, state: SystemState) -> List[List[Dict[str, float]]]:
        """
        Returns n_scenarios trajectories, each a list of horizon dicts:
          scenarios[scenario_idx][day_offset][material_id] = demand_units
        """
        # Fit params per material
        params: Dict[str, Tuple[float, float]] = {}
        for mid in state.inventory:
            hist = state.demand_history.get(mid, [])
            params[mid] = self._exp_smooth_params(hist)

        scenarios = []
        rng = np.random.default_rng()
        for _ in range(self.n_scenarios):
            trajectory = []
            for t in range(self.horizon):
                day_demand: Dict[str, float] = {}
                for mid, (mean, std) in params.items():
                    mult = self._event_multiplier(state, mid, t)
                    raw = rng.normal(mean * mult, std)
                    day_demand[mid] = max(0.0, float(raw))
                trajectory.append(day_demand)
            scenarios.append(trajectory)
        return scenarios

    # ------------------------------------------------------------------ #
    def summary(self, scenarios: List[List[Dict[str, float]]], material_id: str) -> Dict:
        """Return mean / upper / lower curves for plotting."""
        means, uppers, lowers = [], [], []
        for t in range(self.horizon):
            vals = [sc[t].get(material_id, 0.0) for sc in scenarios]
            m = float(np.mean(vals))
            s = float(np.std(vals))
            means.append(m)
            uppers.append(m + s)
            lowers.append(max(0.0, m - s))
        return {"mean": means, "upper": uppers, "lower": lowers, "days": list(range(1, self.horizon + 1))}