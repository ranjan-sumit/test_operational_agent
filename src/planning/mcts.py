# import numpy as np

# from src.core.action import DoNothingAction, ExpireAction, ProcurementAction, TransferAction
# from src.core.transition import apply_action
# from src.simulation.environment import step_environment


# class Node:
#     def __init__(self, state, parent=None, action=None, reward=0.0, path=None):
#         self.state = state
#         self.parent = parent
#         self.action = action
#         self.reward = reward
#         self.children = []
#         self.visits = 0
#         self.value = 0.0
#         self.rewards = []
#         self.path = path or ([] if parent is None else (parent.path + [action]))

#     def mean(self):
#         return self.value / self.visits if self.visits > 0 else 0.0


# class MCTS:
#     def __init__(self, action_gen, scenarios, simulations=60, k=2.0, alpha=0.5, gamma=0.99):
#         self.action_gen = action_gen
#         self.scenarios = scenarios
#         self.simulations = simulations
#         self.k = k
#         self.alpha = alpha
#         self.gamma = gamma
#         self.root = None

#     def search(self, root_state):
#         self.root = Node(root_state.deep_clone())

#         for _ in range(self.simulations):
#             scen_idx = np.random.randint(len(self.scenarios))
#             self._simulate(self.root, 0, scen_idx)

#         if not self.root.children:
#             return DoNothingAction(), []

#         best = max(self.root.children, key=self._risk_score)
#         return best.action, self.get_top_paths(top_k=3)

#     def _simulate(self, node, depth, scen_idx):
#         scenario = self.scenarios[scen_idx]
#         if depth >= len(scenario):
#             return 0.0

#         limit = max(1, int(self.k * (node.visits ** self.alpha)) + 1)

#         if len(node.children) < limit:
#             actions = self.action_gen.generate_all(node.state)
#             valid = [a for a in actions if getattr(a, "cost", 0.0) <= node.state.budget_remaining]

#             existing = {repr(c.action) for c in node.children}
#             new_actions = [a for a in valid if repr(a) not in existing]

#             if new_actions:
#                 act = new_actions[np.random.randint(len(new_actions))]
#                 s1 = apply_action(node.state.deep_clone(), act)
#                 s2, r = step_environment(s1, scenario[depth])
#                 node.children.append(
#                     Node(s2, parent=node, action=act, reward=r, path=node.path + [act])
#                 )

#         if not node.children:
#             return 0.0

#         def ucb(c):
#             if c.visits == 0:
#                 return float("inf")
#             mean = c.value / (c.visits + 1e-6)
#             explore = 1.41 * np.sqrt(np.log(node.visits + 1) / (c.visits + 1e-6))
#             return mean + explore

#         best = max(node.children, key=ucb)
#         future = self._simulate(best, depth + 1, scen_idx)
#         total = best.reward + self.gamma * future

#         self._backprop(best, total)
#         return total

#     def _backprop(self, node, value):
#         curr = node
#         while curr is not None:
#             curr.visits += 1
#             curr.value += value
#             curr.rewards.append(value)
#             curr = curr.parent

#     def _risk_score(self, node, alpha=0.2):
#         if node.visits < 3:
#             return node.mean()

#         mean = node.mean()
#         sorted_r = sorted(node.rewards)
#         cvar = np.mean(sorted_r[:max(1, int(alpha * len(sorted_r)))])
#         return 0.7 * mean + 0.3 * cvar

#     def get_top_paths(self, top_k=3):
#         results = []

#         def dfs(node):
#             if node is not self.root and node.path:
#                 mean = node.mean()
#                 if node.rewards:
#                     sorted_r = sorted(node.rewards)
#                     cvar = np.mean(sorted_r[:max(1, int(0.2 * len(sorted_r)))])
#                 else:
#                     cvar = mean
#                 score = 0.7 * mean + 0.3 * cvar
#                 results.append({
#                     "path": " -> ".join(repr(a) for a in node.path),
#                     "mean": mean,
#                     "cvar": cvar,
#                     "score": score,
#                     "visits": node.visits,
#                     "immediate_reward": node.reward,
#                 })

#             for child in node.children:
#                 dfs(child)

#         dfs(self.root)
#         results.sort(key=lambda x: x["score"], reverse=True)
#         return results[:top_k]

"""
Monte Carlo Tree Search planner with CVaR risk-adjusted scoring.

Key parameters
--------------
simulations : int   Number of MCTS iterations (higher = better quality, slower)
horizon     : int   Rollout depth in days
gamma       : float Discount rate
k           : float Progressive widening breadth constant
cvar_alpha  : float Tail fraction for CVaR (0.2 = worst 20% of outcomes)
"""
from __future__ import annotations
import math
import random
from typing import Dict, List, Optional, Tuple

import numpy as np

from src.core.action import DoNothingAction
from src.core.state import SystemState
from src.planning.action_generator import ActionGenerator
from src.simulation.environment import step_environment


class MCTSNode:
    def __init__(self, state: SystemState, action=None, parent: Optional["MCTSNode"] = None):
        self.state = state
        self.action = action
        self.parent = parent
        self.children: List["MCTSNode"] = []
        self.visits: int = 0
        self.rewards: List[float] = []
        self._untried_actions = None

    def is_fully_expanded(self, all_actions: List) -> bool:
        return len(self.children) >= len(all_actions)

    def ucb1(self, c: float = 1.41) -> float:
        if self.visits == 0:
            return float("inf")
        mean = sum(self.rewards) / self.visits
        parent_visits = self.parent.visits if self.parent else self.visits
        return mean + c * math.sqrt(math.log(parent_visits + 1) / self.visits)


class MCTS:
    def __init__(
        self,
        action_generator: ActionGenerator,
        scenarios: List[List[Dict[str, float]]],
        simulations: int = 80,
        horizon: int = 5,
        gamma: float = 0.99,
        k: float = 2.0,
        pw_alpha: float = 0.5,
        cvar_alpha: float = 0.2,
    ):
        self.action_gen = action_generator
        self.scenarios = scenarios
        self.simulations = simulations
        self.horizon = horizon
        self.gamma = gamma
        self.k = k
        self.pw_alpha = pw_alpha
        self.cvar_alpha = cvar_alpha

    # ------------------------------------------------------------------ #

    def search(self, root_state: SystemState) -> Tuple[object, List[Dict]]:
        root = MCTSNode(state=root_state)
        all_actions = self.action_gen.generate_all(root_state)

        if not all_actions:
            return DoNothingAction(), []

        for _ in range(self.simulations):
            node = self._select(root, all_actions)
            node = self._expand(node, all_actions)
            reward = self._rollout(node.state)
            self._backprop(node, reward)

        top_paths = self._get_top_paths(root)
        best = self._best_child(root)
        if best is None or best.action is None:
            return DoNothingAction(), top_paths
        return best.action, top_paths

    # ------------------------------------------------------------------ #

    def _select(self, node: MCTSNode, all_actions: List) -> MCTSNode:
        """Walk tree selecting nodes by UCB1 until a non-fully-expanded node."""
        max_children = max(1, int(self.k * (node.visits ** self.pw_alpha)))
        while node.children and len(node.children) >= min(len(all_actions), max_children):
            node = max(node.children, key=lambda n: n.ucb1())
            all_actions = self.action_gen.generate_all(node.state)
            max_children = max(1, int(self.k * (node.visits ** self.pw_alpha)))
        return node

    def _expand(self, node: MCTSNode, all_actions: List) -> MCTSNode:
        """Add one new child for an untried action."""
        tried = {id(c.action) for c in node.children}
        untried = [a for a in all_actions if id(a) not in tried]
        if not untried:
            return node
        action = random.choice(untried)
        from src.core.transition import apply_action
        new_state = apply_action(node.state, action)
        child = MCTSNode(state=new_state, action=action, parent=node)
        node.children.append(child)
        return child

    def _rollout(self, state: SystemState) -> float:
        """Heuristic rollout: reorder if below safety stock; run for horizon steps."""
        s = state.deep_clone()
        scenario = random.choice(self.scenarios)
        total_reward = 0.0
        for t in range(min(self.horizon, len(scenario))):
            demand = scenario[t]
            s, r = step_environment(s, demand)
            total_reward += (self.gamma ** t) * r
        return total_reward

    def _backprop(self, node: MCTSNode, reward: float):
        """Walk from node to root updating visit counts and rewards."""
        cur = node
        while cur is not None:
            cur.visits += 1
            cur.rewards.append(reward)
            cur = cur.parent

    def _risk_score(self, node: MCTSNode) -> float:
        """CVaR-adjusted score: 0.7 × mean + 0.3 × CVaR (worst tail)."""
        if not node.rewards:
            return float("-inf")
        rewards = sorted(node.rewards)
        mean = sum(rewards) / len(rewards)
        tail_n = max(1, int(len(rewards) * self.cvar_alpha))
        cvar = sum(rewards[:tail_n]) / tail_n
        return 0.7 * mean + 0.3 * cvar

    def _best_child(self, root: MCTSNode) -> Optional[MCTSNode]:
        if not root.children:
            return None
        return max(root.children, key=self._risk_score)

    def _get_top_paths(self, root: MCTSNode, top_n: int = 5) -> List[Dict]:
        results = []
        for child in root.children:
            if child.visits == 0:
                continue
            rewards = sorted(child.rewards)
            mean = sum(rewards) / len(rewards)
            tail_n = max(1, int(len(rewards) * self.cvar_alpha))
            cvar = sum(rewards[:tail_n]) / tail_n
            score = 0.7 * mean + 0.3 * cvar
            results.append({
                "path": str(child.action),
                "mean": round(mean, 2),
                "cvar": round(cvar, 2),
                "score": round(score, 2),
                "visits": child.visits,
                "action": child.action,
            })
        return sorted(results, key=lambda x: x["score"], reverse=True)[:top_n]