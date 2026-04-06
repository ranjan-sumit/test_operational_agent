# # # # """
# # # # Agent Orchestrator
# # # # ==================
# # # # The LLM (Azure GPT-4o-mini) is given 5 tools and a system prompt.
# # # # It perceives the inventory, plans via MCTS, decides autonomy level,
# # # # acts (or escalates), and logs every decision to memory.

# # # # One call to  run_agent_cycle()  executes one full perceive→plan→act loop
# # # # and returns a structured result the UI can render.
# # # # """
# # # # from __future__ import annotations
# # # # import json
# # # # import urllib.request
# # # # from datetime import datetime
# # # # from typing import Any, Dict, List, Optional, Tuple

# # # # from src.core.state import SystemState
# # # # from src.agent.tools import (
# # # #     execute_action,
# # # #     log_decision,
# # # #     read_inventory,
# # # #     run_mcts_planner,
# # # #     send_alert,
# # # # )

# # # # # ── Azure OpenAI config ───────────────────────────────────────────────────────
# # # # AZURE_ENDPOINT    = (
# # # #     "https://bu24-demo.openai.azure.com/openai/deployments/"
# # # #     "gpt-4o-mini/chat/completions"
# # # # )
# # # # AZURE_API_KEY     = "8pyt1c5txcgWu"
# # # # AZURE_API_VERSION = "2025-01-01-preview"

# # # # # ── Tool schemas for the LLM ──────────────────────────────────────────────────
# # # # TOOL_SCHEMAS = [
# # # #     {
# # # #         "type": "function",
# # # #         "function": {
# # # #             "name": "read_inventory",
# # # #             "description": (
# # # #                 "Read current inventory state. Returns stock levels, expiry risk, "
# # # #                 "safety stock coverage, and active market events. "
# # # #                 "Always call this FIRST at the start of every cycle."
# # # #             ),
# # # #             "parameters": {"type": "object", "properties": {}, "required": []},
# # # #         },
# # # #     },
# # # #     {
# # # #         "type": "function",
# # # #         "function": {
# # # #             "name": "run_mcts_planner",
# # # #             "description": (
# # # #                 "Run the MCTS planning engine. Returns the best action, its risk score, "
# # # #                 "CVaR, and an autonomy recommendation: AUTO_EXECUTE, ALERT_AND_WAIT, "
# # # #                 "or ESCALATE. Call this after reading inventory."
# # # #             ),
# # # #             "parameters": {
# # # #                 "type": "object",
# # # #                 "properties": {
# # # #                     "horizon":     {"type": "integer", "description": "Planning horizon in days (3-14)", "default": 7},
# # # #                     "simulations": {"type": "integer", "description": "MCTS simulations (50-200)",       "default": 100},
# # # #                 },
# # # #                 "required": [],
# # # #             },
# # # #         },
# # # #     },
# # # #     {
# # # #         "type": "function",
# # # #         "function": {
# # # #             "name": "execute_action",
# # # #             "description": (
# # # #                 "Execute the recommended action and step the simulation forward by 1 day. "
# # # #                 "Only call this when autonomy is AUTO_EXECUTE, or after human approval."
# # # #             ),
# # # #             "parameters": {"type": "object", "properties": {}, "required": []},
# # # #         },
# # # #     },
# # # #     {
# # # #         "type": "function",
# # # #         "function": {
# # # #             "name": "send_alert",
# # # #             "description": (
# # # #                 "Send an alert to the supply chain team. Use for ALERT_AND_WAIT or "
# # # #                 "ESCALATE situations, or any critical finding (expiry, stockout risk)."
# # # #             ),
# # # #             "parameters": {
# # # #                 "type": "object",
# # # #                 "properties": {
# # # #                     "message":            {"type": "string", "description": "Alert message text"},
# # # #                     "level":              {"type": "string", "enum": ["INFO", "WARNING", "CRITICAL"]},
# # # #                     "action_required":    {"type": "boolean"},
# # # #                     "recommended_action": {"type": "string", "description": "What the agent recommends"},
# # # #                 },
# # # #                 "required": ["message", "level"],
# # # #             },
# # # #         },
# # # #     },
# # # #     {
# # # #         "type": "function",
# # # #         "function": {
# # # #             "name": "log_decision",
# # # #             "description": (
# # # #                 "Log the agent's decision and reasoning to memory. "
# # # #                 "Always call this as the LAST step of every cycle."
# # # #             ),
# # # #             "parameters": {
# # # #                 "type": "object",
# # # #                 "properties": {
# # # #                     "action":      {"type": "string"},
# # # #                     "action_type": {"type": "string"},
# # # #                     "autonomy":    {"type": "string"},
# # # #                     "risk_score":  {"type": "number"},
# # # #                     "cost":        {"type": "number"},
# # # #                     "reward":      {"type": "number"},
# # # #                     "reasoning":   {"type": "string", "description": "Plain-English explanation of decision"},
# # # #                 },
# # # #                 "required": ["action", "action_type", "autonomy",
# # # #                              "risk_score", "cost", "reward", "reasoning"],
# # # #             },
# # # #         },
# # # #     },
# # # # ]

# # # # SYSTEM_PROMPT = """You are an autonomous supply chain agent for a biotech laboratory.

# # # # Your job each cycle:
# # # # 1. Call read_inventory — understand the current situation
# # # # 2. Call run_mcts_planner — get the AI-recommended action and risk score
# # # # 3. Decide what to do based on the autonomy level returned:
# # # #    - AUTO_EXECUTE  → call execute_action immediately, then log_decision
# # # #    - ALERT_AND_WAIT → call send_alert (WARNING, action_required=true), then log_decision. Do NOT execute.
# # # #    - ESCALATE      → call send_alert (CRITICAL, action_required=true), then log_decision. Do NOT execute.
# # # # 4. Always end with log_decision — include your plain-English reasoning.

# # # # Autonomy rules you must follow:
# # # # - If the recommended action is DoNothingAction → AUTO_EXECUTE always
# # # # - If an item has expiry_days ≤ 3 → treat as CRITICAL, send alert regardless
# # # # - If coverage_ratio < 0.5 for any critical reagent → send WARNING even if auto-executing
# # # # - Never execute if cost > $50,000 without explicit ALERT_AND_WAIT

# # # # Be concise in tool calls. Your reasoning in log_decision should be 2-3 sentences max,
# # # # written for a supply chain manager — no jargon.
# # # # """


# # # # # ══════════════════════════════════════════════════════════════════════════════
# # # # #  LLM CALL
# # # # # ══════════════════════════════════════════════════════════════════════════════

# # # # def _call_azure(messages: List[Dict], tools: List[Dict]) -> Dict:
# # # #     """Raw call to Azure OpenAI chat completions endpoint."""
# # # #     url     = f"{AZURE_ENDPOINT}?api-version={AZURE_API_VERSION}"
# # # #     payload = json.dumps({
# # # #         "messages":    messages,
# # # #         "tools":       tools,
# # # #         "tool_choice": "auto",
# # # #         "max_tokens":  1000,
# # # #         "temperature": 0.1,
# # # #     }).encode()
# # # #     req = urllib.request.Request(
# # # #         url, data=payload,
# # # #         headers={"Content-Type": "application/json", "api-key": AZURE_API_KEY},
# # # #         method="POST",
# # # #     )
# # # #     with urllib.request.urlopen(req, timeout=45) as r:
# # # #         return json.loads(r.read())


# # # # # ══════════════════════════════════════════════════════════════════════════════
# # # # #  TOOL DISPATCHER
# # # # # ══════════════════════════════════════════════════════════════════════════════

# # # # def _dispatch(
# # # #     tool_name: str,
# # # #     tool_args: Dict,
# # # #     *,
# # # #     state: SystemState,
# # # #     db_path: str,
# # # #     _mcts_result: Optional[Dict],
# # # #     _exec_result: Optional[Dict],
# # # #     _scenarios: Optional[List],
# # # # ) -> Tuple[Any, Optional[SystemState]]:
# # # #     """
# # # #     Route an LLM tool call to the actual Python function.
# # # #     Returns (result_dict, optional_new_state).
# # # #     """
# # # #     new_state = None

# # # #     if tool_name == "read_inventory":
# # # #         result = read_inventory(state)

# # # #     elif tool_name == "run_mcts_planner":
# # # #         horizon     = int(tool_args.get("horizon",     7))
# # # #         simulations = int(tool_args.get("simulations", 100))
# # # #         result      = run_mcts_planner(
# # # #             state, horizon=horizon, simulations=simulations
# # # #         )
# # # #         # Regenerate scenarios for execute_action to use
# # # #         from src.demand.scenario_generator import ScenarioGenerator
# # # #         _scenarios[:] = ScenarioGenerator(
# # # #             horizon=horizon, n_scenarios=50
# # # #         ).generate(state)
# # # #         # Store for execute_action
# # # #         _mcts_result.update(result)

# # # #     elif tool_name == "execute_action":
# # # #         if not _mcts_result or "_action_obj" not in _mcts_result:
# # # #             result = {"error": "run_mcts_planner must be called first"}
# # # #         else:
# # # #             result    = execute_action(
# # # #                 state, _mcts_result["_action_obj"],
# # # #                 scenarios=_scenarios or None,
# # # #             )
# # # #             new_state = result.pop("_new_state", None)
# # # #             _exec_result.update(result)

# # # #     elif tool_name == "send_alert":
# # # #         result = send_alert(
# # # #             message            = tool_args.get("message", ""),
# # # #             level              = tool_args.get("level", "INFO"),
# # # #             action_required    = tool_args.get("action_required", False),
# # # #             recommended_action = tool_args.get("recommended_action", ""),
# # # #         )

# # # #     elif tool_name == "log_decision":
# # # #         reward = _exec_result.get("reward", 0.0) if _exec_result else 0.0
# # # #         result = log_decision(
# # # #             db_path    = db_path,
# # # #             day        = state.current_day,
# # # #             action     = tool_args.get("action", ""),
# # # #             action_type= tool_args.get("action_type", ""),
# # # #             autonomy   = tool_args.get("autonomy", ""),
# # # #             risk_score = float(tool_args.get("risk_score", 0)),
# # # #             cost       = float(tool_args.get("cost", 0)),
# # # #             reward     = float(tool_args.get("reward", reward)),
# # # #             reasoning  = tool_args.get("reasoning", ""),
# # # #         )

# # # #     else:
# # # #         result = {"error": f"Unknown tool: {tool_name}"}

# # # #     return result, new_state


# # # # # ══════════════════════════════════════════════════════════════════════════════
# # # # #  MAIN AGENT CYCLE
# # # # # ══════════════════════════════════════════════════════════════════════════════

# # # # def run_agent_cycle(
# # # #     state: SystemState,
# # # #     db_path: str = "data/inventory.db",
# # # #     max_turns: int = 12,
# # # # ) -> Dict[str, Any]:
# # # #     """
# # # #     Run one full perceive → plan → act → log cycle.

# # # #     Returns:
# # # #         {
# # # #           "new_state":   SystemState (updated if action was executed),
# # # #           "executed":    bool,
# # # #           "autonomy":    "AUTO_EXECUTE" | "ALERT_AND_WAIT" | "ESCALATE",
# # # #           "action":      str,
# # # #           "reasoning":   str,
# # # #           "reward":      float,
# # # #           "alerts":      [ alert dicts ],
# # # #           "thought_log": [ { role, content } ],   ← the agent's inner monologue
# # # #           "tool_calls":  [ { tool, args, result } ],
# # # #           "error":       str or None,
# # # #         }
# # # #     """
# # # #     messages: List[Dict] = [
# # # #         {"role": "system", "content": SYSTEM_PROMPT},
# # # #         {
# # # #             "role": "user",
# # # #             "content": (
# # # #                 f"Current simulation day: {state.current_day}. "
# # # #                 f"Budget remaining: ${state.budget_remaining:,.0f}. "
# # # #                 "Please run your supply chain planning cycle now."
# # # #             ),
# # # #         },
# # # #     ]

# # # #     thought_log: List[Dict]  = []
# # # #     tool_calls_log: List     = []
# # # #     alerts: List[Dict]       = []
# # # #     new_state: SystemState   = state

# # # #     # Shared mutable containers passed into dispatcher
# # # #     _mcts_result: Dict = {}
# # # #     _exec_result: Dict = {}
# # # #     _scenarios:   List = []

# # # #     executed  = False
# # # #     autonomy  = "UNKNOWN"
# # # #     action    = "Do Nothing"
# # # #     reasoning = ""
# # # #     reward    = 0.0
# # # #     error     = None

# # # #     try:
# # # #         for turn in range(max_turns):
# # # #             response   = _call_azure(messages, TOOL_SCHEMAS)
# # # #             choice     = response["choices"][0]
# # # #             msg        = choice["message"]
# # # #             finish     = choice["finish_reason"]

# # # #             # Record the assistant turn
# # # #             messages.append(msg)
# # # #             thought_log.append({
# # # #                 "role":    "assistant",
# # # #                 "content": msg.get("content") or "",
# # # #                 "turn":    turn + 1,
# # # #             })

# # # #             # No tool calls → LLM finished
# # # #             if finish == "stop" or not msg.get("tool_calls"):
# # # #                 break

# # # #             # Process each tool call in this turn
# # # #             for tc in msg["tool_calls"]:
# # # #                 tool_name = tc["function"]["name"]
# # # #                 tool_args = json.loads(tc["function"]["arguments"] or "{}")

# # # #                 tool_result, maybe_new_state = _dispatch(
# # # #                     tool_name, tool_args,
# # # #                     state        = new_state,
# # # #                     db_path      = db_path,
# # # #                     _mcts_result = _mcts_result,
# # # #                     _exec_result = _exec_result,
# # # #                     _scenarios   = _scenarios,
# # # #                 )

# # # #                 # Update running state if execution happened
# # # #                 if maybe_new_state is not None:
# # # #                     new_state = maybe_new_state
# # # #                     executed  = True
# # # #                     reward    = _exec_result.get("reward", 0.0)

# # # #                 # Collect alerts
# # # #                 if tool_name == "send_alert":
# # # #                     alerts.append(tool_result)

# # # #                 # Extract autonomy + reasoning from log_decision call
# # # #                 if tool_name == "log_decision":
# # # #                     autonomy  = tool_args.get("autonomy", autonomy)
# # # #                     action    = tool_args.get("action",   action)
# # # #                     reasoning = tool_args.get("reasoning", reasoning)

# # # #                 # Capture MCTS autonomy recommendation early
# # # #                 if tool_name == "run_mcts_planner" and "autonomy" in tool_result:
# # # #                     autonomy = tool_result["autonomy"]

# # # #                 # Strip internal objects before sending result back to LLM
# # # #                 safe_result = {
# # # #                     k: v for k, v in tool_result.items()
# # # #                     if not k.startswith("_")
# # # #                 }

# # # #                 tool_calls_log.append({
# # # #                     "tool":   tool_name,
# # # #                     "args":   tool_args,
# # # #                     "result": safe_result,
# # # #                 })

# # # #                 messages.append({
# # # #                     "role":         "tool",
# # # #                     "tool_call_id": tc["id"],
# # # #                     "content":      json.dumps(safe_result),
# # # #                 })

# # # #     except Exception as exc:
# # # #         error = str(exc)

# # # #     return {
# # # #         "new_state":   new_state,
# # # #         "executed":    executed,
# # # #         "autonomy":    autonomy,
# # # #         "action":      action,
# # # #         "reasoning":   reasoning,
# # # #         "reward":      reward,
# # # #         "alerts":      alerts,
# # # #         "thought_log": thought_log,
# # # #         "tool_calls":  tool_calls_log,
# # # #         "error":       error,
# # # #     }


# # # # # ══════════════════════════════════════════════════════════════════════════════
# # # # #  MEMORY READER  (for the audit trail tab)
# # # # # ══════════════════════════════════════════════════════════════════════════════

# # # # def load_agent_memory(db_path: str = "data/inventory.db"):
# # # #     """Load all agent decisions from memory table. Returns list of dicts."""
# # # #     import sqlite3 as _sq
# # # #     conn = _sq.connect(db_path)
# # # #     try:
# # # #         rows = conn.execute(
# # # #             "SELECT * FROM agent_memory ORDER BY id DESC"
# # # #         ).fetchall()
# # # #         cols = [d[0] for d in conn.execute(
# # # #             "SELECT * FROM agent_memory LIMIT 0"
# # # #         ).description or []]
# # # #         if not cols and rows:
# # # #             cols = ["id","timestamp","day","action","action_type","autonomy",
# # # #                     "risk_score","cost","reward","reasoning",
# # # #                     "human_override","override_reason"]
# # # #         return [dict(zip(cols, r)) for r in rows]
# # # #     except Exception:
# # # #         return []
# # # #     finally:
# # # #         conn.close()

# # # """
# # # Agent Orchestrator
# # # ==================
# # # The LLM (Azure GPT-4o-mini) is given 5 tools and a system prompt.
# # # It perceives the inventory, plans via MCTS, decides autonomy level,
# # # acts (or escalates), and logs every decision to memory.

# # # One call to  run_agent_cycle()  executes one full perceive→plan→act loop
# # # and returns a structured result the UI can render.
# # # """
# # # from __future__ import annotations
# # # import json
# # # import urllib.request
# # # from datetime import datetime
# # # from typing import Any, Dict, List, Optional, Tuple

# # # from src.core.state import SystemState
# # # from src.agent.tools import (
# # #     execute_action,
# # #     log_decision,
# # #     read_inventory,
# # #     run_mcts_planner,
# # #     send_alert,
# # # )

# # # # ── Azure OpenAI config ───────────────────────────────────────────────────────
# # # AZURE_ENDPOINT    = (
# # #     "https://bu24-demo.openai.azure.com/openai/deployments/"
# # #     "gpt-4o-mini/chat/completions"
# # # )
# # # AZURE_API_KEY     = ""  # overridden at runtime via UI
# # # AZURE_API_VERSION = "2025-01-01-preview"

# # # # ── Tool schemas for the LLM ──────────────────────────────────────────────────
# # # TOOL_SCHEMAS = [
# # #     {
# # #         "type": "function",
# # #         "function": {
# # #             "name": "read_inventory",
# # #             "description": (
# # #                 "Read current inventory state. Returns stock levels, expiry risk, "
# # #                 "safety stock coverage, and active market events. "
# # #                 "Always call this FIRST at the start of every cycle."
# # #             ),
# # #             "parameters": {"type": "object", "properties": {}, "required": []},
# # #         },
# # #     },
# # #     {
# # #         "type": "function",
# # #         "function": {
# # #             "name": "run_mcts_planner",
# # #             "description": (
# # #                 "Run the MCTS planning engine. Returns the best action, its risk score, "
# # #                 "CVaR, and an autonomy recommendation: AUTO_EXECUTE, ALERT_AND_WAIT, "
# # #                 "or ESCALATE. Call this after reading inventory."
# # #             ),
# # #             "parameters": {
# # #                 "type": "object",
# # #                 "properties": {
# # #                     "horizon":     {"type": "integer", "description": "Planning horizon in days (3-14)", "default": 7},
# # #                     "simulations": {"type": "integer", "description": "MCTS simulations (50-200)",       "default": 100},
# # #                 },
# # #                 "required": [],
# # #             },
# # #         },
# # #     },
# # #     {
# # #         "type": "function",
# # #         "function": {
# # #             "name": "execute_action",
# # #             "description": (
# # #                 "Execute the recommended action and step the simulation forward by 1 day. "
# # #                 "Only call this when autonomy is AUTO_EXECUTE, or after human approval."
# # #             ),
# # #             "parameters": {"type": "object", "properties": {}, "required": []},
# # #         },
# # #     },
# # #     {
# # #         "type": "function",
# # #         "function": {
# # #             "name": "send_alert",
# # #             "description": (
# # #                 "Send an alert to the supply chain team. Use for ALERT_AND_WAIT or "
# # #                 "ESCALATE situations, or any critical finding (expiry, stockout risk)."
# # #             ),
# # #             "parameters": {
# # #                 "type": "object",
# # #                 "properties": {
# # #                     "message":            {"type": "string", "description": "Alert message text"},
# # #                     "level":              {"type": "string", "enum": ["INFO", "WARNING", "CRITICAL"]},
# # #                     "action_required":    {"type": "boolean"},
# # #                     "recommended_action": {"type": "string", "description": "What the agent recommends"},
# # #                 },
# # #                 "required": ["message", "level"],
# # #             },
# # #         },
# # #     },
# # #     {
# # #         "type": "function",
# # #         "function": {
# # #             "name": "log_decision",
# # #             "description": (
# # #                 "Log the agent's decision and reasoning to memory. "
# # #                 "Always call this as the LAST step of every cycle."
# # #             ),
# # #             "parameters": {
# # #                 "type": "object",
# # #                 "properties": {
# # #                     "action":      {"type": "string"},
# # #                     "action_type": {"type": "string"},
# # #                     "autonomy":    {"type": "string"},
# # #                     "risk_score":  {"type": "number"},
# # #                     "cost":        {"type": "number"},
# # #                     "reward":      {"type": "number"},
# # #                     "reasoning":   {"type": "string", "description": "Plain-English explanation of decision"},
# # #                 },
# # #                 "required": ["action", "action_type", "autonomy",
# # #                              "risk_score", "cost", "reward", "reasoning"],
# # #             },
# # #         },
# # #     },
# # # ]

# # # SYSTEM_PROMPT = """You are an autonomous supply chain agent for a biotech laboratory.

# # # Your job each cycle:
# # # 1. Call read_inventory — understand the current situation
# # # 2. Call run_mcts_planner — get the AI-recommended action and risk score
# # # 3. Decide what to do based on the autonomy level returned:
# # #    - AUTO_EXECUTE  → call execute_action immediately, then log_decision
# # #    - ALERT_AND_WAIT → call send_alert (WARNING, action_required=true), then log_decision. Do NOT execute.
# # #    - ESCALATE      → call send_alert (CRITICAL, action_required=true), then log_decision. Do NOT execute.
# # # 4. Always end with log_decision — include your plain-English reasoning.

# # # Autonomy rules you must follow:
# # # - If the recommended action is DoNothingAction → AUTO_EXECUTE always
# # # - If an item has expiry_days ≤ 3 → treat as CRITICAL, send alert regardless
# # # - If coverage_ratio < 0.5 for any critical reagent → send WARNING even if auto-executing
# # # - Never execute if cost > $50,000 without explicit ALERT_AND_WAIT

# # # Be concise in tool calls. Your reasoning in log_decision should be 2-3 sentences max,
# # # written for a supply chain manager — no jargon.
# # # """


# # # # ══════════════════════════════════════════════════════════════════════════════
# # # #  LLM CALL
# # # # ══════════════════════════════════════════════════════════════════════════════

# # # def _call_azure(messages: List[Dict], tools: List[Dict], api_key: str = "") -> Dict:
# # #     """Raw call to Azure OpenAI chat completions endpoint."""
# # #     key     = api_key or AZURE_API_KEY
# # #     if not key:
# # #         raise ValueError("Azure API key not set. Enter it in the sidebar.")
# # #     url     = f"{AZURE_ENDPOINT}?api-version={AZURE_API_VERSION}"
# # #     payload = json.dumps({
# # #         "messages":    messages,
# # #         "tools":       tools,
# # #         "tool_choice": "auto",
# # #         "max_tokens":  1000,
# # #         "temperature": 0.1,
# # #     }).encode()
# # #     req = urllib.request.Request(
# # #         url, data=payload,
# # #         headers={"Content-Type": "application/json", "api-key": key},
# # #         method="POST",
# # #     )
# # #     with urllib.request.urlopen(req, timeout=45) as r:
# # #         return json.loads(r.read())


# # # # ══════════════════════════════════════════════════════════════════════════════
# # # #  TOOL DISPATCHER
# # # # ══════════════════════════════════════════════════════════════════════════════

# # # def _dispatch(
# # #     tool_name: str,
# # #     tool_args: Dict,
# # #     *,
# # #     state: SystemState,
# # #     db_path: str,
# # #     _mcts_result: Optional[Dict],
# # #     _exec_result: Optional[Dict],
# # #     _scenarios: Optional[List],
# # # ) -> Tuple[Any, Optional[SystemState]]:
# # #     """
# # #     Route an LLM tool call to the actual Python function.
# # #     Returns (result_dict, optional_new_state).
# # #     """
# # #     new_state = None

# # #     if tool_name == "read_inventory":
# # #         result = read_inventory(state)

# # #     elif tool_name == "run_mcts_planner":
# # #         horizon     = int(tool_args.get("horizon",     7))
# # #         simulations = int(tool_args.get("simulations", 100))
# # #         result      = run_mcts_planner(
# # #             state, horizon=horizon, simulations=simulations
# # #         )
# # #         # Regenerate scenarios for execute_action to use
# # #         from src.demand.scenario_generator import ScenarioGenerator
# # #         _scenarios[:] = ScenarioGenerator(
# # #             horizon=horizon, n_scenarios=50
# # #         ).generate(state)
# # #         # Store for execute_action
# # #         _mcts_result.update(result)

# # #     elif tool_name == "execute_action":
# # #         if not _mcts_result or "_action_obj" not in _mcts_result:
# # #             result = {"error": "run_mcts_planner must be called first"}
# # #         else:
# # #             result    = execute_action(
# # #                 state, _mcts_result["_action_obj"],
# # #                 scenarios=_scenarios or None,
# # #             )
# # #             new_state = result.pop("_new_state", None)
# # #             _exec_result.update(result)

# # #     elif tool_name == "send_alert":
# # #         result = send_alert(
# # #             message            = tool_args.get("message", ""),
# # #             level              = tool_args.get("level", "INFO"),
# # #             action_required    = tool_args.get("action_required", False),
# # #             recommended_action = tool_args.get("recommended_action", ""),
# # #         )

# # #     elif tool_name == "log_decision":
# # #         reward = _exec_result.get("reward", 0.0) if _exec_result else 0.0
# # #         result = log_decision(
# # #             db_path    = db_path,
# # #             day        = state.current_day,
# # #             action     = tool_args.get("action", ""),
# # #             action_type= tool_args.get("action_type", ""),
# # #             autonomy   = tool_args.get("autonomy", ""),
# # #             risk_score = float(tool_args.get("risk_score", 0)),
# # #             cost       = float(tool_args.get("cost", 0)),
# # #             reward     = float(tool_args.get("reward", reward)),
# # #             reasoning  = tool_args.get("reasoning", ""),
# # #         )

# # #     else:
# # #         result = {"error": f"Unknown tool: {tool_name}"}

# # #     return result, new_state


# # # # ══════════════════════════════════════════════════════════════════════════════
# # # #  MAIN AGENT CYCLE
# # # # ══════════════════════════════════════════════════════════════════════════════

# # # def run_agent_cycle(
# # #     state: SystemState,
# # #     db_path: str = "data/inventory.db",
# # #     max_turns: int = 12,
# # #     api_key: str = "",
# # # ) -> Dict[str, Any]:
# # #     """
# # #     Run one full perceive → plan → act → log cycle.

# # #     Returns:
# # #         {
# # #           "new_state":   SystemState (updated if action was executed),
# # #           "executed":    bool,
# # #           "autonomy":    "AUTO_EXECUTE" | "ALERT_AND_WAIT" | "ESCALATE",
# # #           "action":      str,
# # #           "reasoning":   str,
# # #           "reward":      float,
# # #           "alerts":      [ alert dicts ],
# # #           "thought_log": [ { role, content } ],   ← the agent's inner monologue
# # #           "tool_calls":  [ { tool, args, result } ],
# # #           "error":       str or None,
# # #         }
# # #     """
# # #     messages: List[Dict] = [
# # #         {"role": "system", "content": SYSTEM_PROMPT},
# # #         {
# # #             "role": "user",
# # #             "content": (
# # #                 f"Current simulation day: {state.current_day}. "
# # #                 f"Budget remaining: ${state.budget_remaining:,.0f}. "
# # #                 "Please run your supply chain planning cycle now."
# # #             ),
# # #         },
# # #     ]

# # #     thought_log: List[Dict]  = []
# # #     tool_calls_log: List     = []
# # #     alerts: List[Dict]       = []
# # #     new_state: SystemState   = state

# # #     # Shared mutable containers passed into dispatcher
# # #     _mcts_result: Dict = {}
# # #     _exec_result: Dict = {}
# # #     _scenarios:   List = []

# # #     executed  = False
# # #     autonomy  = "UNKNOWN"
# # #     action    = "Do Nothing"
# # #     reasoning = ""
# # #     reward    = 0.0
# # #     error     = None

# # #     try:
# # #         for turn in range(max_turns):
# # #             response   = _call_azure(messages, TOOL_SCHEMAS, api_key=api_key)
# # #             choice     = response["choices"][0]
# # #             msg        = choice["message"]
# # #             finish     = choice["finish_reason"]

# # #             # Record the assistant turn
# # #             messages.append(msg)
# # #             thought_log.append({
# # #                 "role":    "assistant",
# # #                 "content": msg.get("content") or "",
# # #                 "turn":    turn + 1,
# # #             })

# # #             # No tool calls → LLM finished
# # #             if finish == "stop" or not msg.get("tool_calls"):
# # #                 break

# # #             # Process each tool call in this turn
# # #             for tc in msg["tool_calls"]:
# # #                 tool_name = tc["function"]["name"]
# # #                 tool_args = json.loads(tc["function"]["arguments"] or "{}")

# # #                 tool_result, maybe_new_state = _dispatch(
# # #                     tool_name, tool_args,
# # #                     state        = new_state,
# # #                     db_path      = db_path,
# # #                     _mcts_result = _mcts_result,
# # #                     _exec_result = _exec_result,
# # #                     _scenarios   = _scenarios,
# # #                 )

# # #                 # Update running state if execution happened
# # #                 if maybe_new_state is not None:
# # #                     new_state = maybe_new_state
# # #                     executed  = True
# # #                     reward    = _exec_result.get("reward", 0.0)

# # #                 # Collect alerts
# # #                 if tool_name == "send_alert":
# # #                     alerts.append(tool_result)

# # #                 # Extract autonomy + reasoning from log_decision call
# # #                 if tool_name == "log_decision":
# # #                     autonomy  = tool_args.get("autonomy", autonomy)
# # #                     action    = tool_args.get("action",   action)
# # #                     reasoning = tool_args.get("reasoning", reasoning)

# # #                 # Capture MCTS autonomy recommendation early
# # #                 if tool_name == "run_mcts_planner" and "autonomy" in tool_result:
# # #                     autonomy = tool_result["autonomy"]

# # #                 # Strip internal objects before sending result back to LLM
# # #                 safe_result = {
# # #                     k: v for k, v in tool_result.items()
# # #                     if not k.startswith("_")
# # #                 }

# # #                 tool_calls_log.append({
# # #                     "tool":   tool_name,
# # #                     "args":   tool_args,
# # #                     "result": safe_result,
# # #                 })

# # #                 messages.append({
# # #                     "role":         "tool",
# # #                     "tool_call_id": tc["id"],
# # #                     "content":      json.dumps(safe_result),
# # #                 })

# # #     except Exception as exc:
# # #         error = str(exc)

# # #     return {
# # #         "new_state":   new_state,
# # #         "executed":    executed,
# # #         "autonomy":    autonomy,
# # #         "action":      action,
# # #         "reasoning":   reasoning,
# # #         "reward":      reward,
# # #         "alerts":      alerts,
# # #         "thought_log": thought_log,
# # #         "tool_calls":  tool_calls_log,
# # #         "error":       error,
# # #     }


# # # # ══════════════════════════════════════════════════════════════════════════════
# # # #  MEMORY READER  (for the audit trail tab)
# # # # ══════════════════════════════════════════════════════════════════════════════

# # # def load_agent_memory(db_path: str = "data/inventory.db"):
# # #     """Load all agent decisions from memory table. Returns list of dicts."""
# # #     import sqlite3 as _sq
# # #     conn = _sq.connect(db_path)
# # #     try:
# # #         rows = conn.execute(
# # #             "SELECT * FROM agent_memory ORDER BY id DESC"
# # #         ).fetchall()
# # #         cols = [d[0] for d in conn.execute(
# # #             "SELECT * FROM agent_memory LIMIT 0"
# # #         ).description or []]
# # #         if not cols and rows:
# # #             cols = ["id","timestamp","day","action","action_type","autonomy",
# # #                     "risk_score","cost","reward","reasoning",
# # #                     "human_override","override_reason"]
# # #         return [dict(zip(cols, r)) for r in rows]
# # #     except Exception:
# # #         return []
# # #     finally:
# # #         conn.close()

# # """
# # Agent Orchestrator
# # ==================
# # The LLM (Azure GPT-4o-mini) is given 5 tools and a system prompt.
# # It perceives the inventory, plans via MCTS, decides autonomy level,
# # acts (or escalates), and logs every decision to memory.

# # One call to  run_agent_cycle()  executes one full perceive→plan→act loop
# # and returns a structured result the UI can render.
# # """
# # from __future__ import annotations
# # import json
# # import urllib.request
# # from datetime import datetime
# # from typing import Any, Dict, List, Optional, Tuple

# # from src.core.state import SystemState
# # from src.agent.tools import (
# #     execute_action,
# #     log_decision,
# #     read_inventory,
# #     run_mcts_planner,
# #     send_alert,
# # )

# # # ── Azure OpenAI config ───────────────────────────────────────────────────────
# # AZURE_ENDPOINT    = (
# #     "https://bu24-demo.openai.azure.com/openai/deployments/"
# #     "gpt-4o-mini/chat/completions"
# # )
# # AZURE_API_KEY     = ""  # overridden at runtime via UI
# # AZURE_API_VERSION = "2025-01-01-preview"

# # # ── Tool schemas for the LLM ──────────────────────────────────────────────────
# # TOOL_SCHEMAS = [
# #     {
# #         "type": "function",
# #         "function": {
# #             "name": "read_inventory",
# #             "description": (
# #                 "Read current inventory state. Returns stock levels, expiry risk, "
# #                 "safety stock coverage, and active market events. "
# #                 "Always call this FIRST at the start of every cycle."
# #             ),
# #             "parameters": {"type": "object", "properties": {}, "required": []},
# #         },
# #     },
# #     {
# #         "type": "function",
# #         "function": {
# #             "name": "run_mcts_planner",
# #             "description": (
# #                 "Run the MCTS planning engine. Returns the best action, its risk score, "
# #                 "CVaR, and an autonomy recommendation: AUTO_EXECUTE, ALERT_AND_WAIT, "
# #                 "or ESCALATE. Call this after reading inventory."
# #             ),
# #             "parameters": {
# #                 "type": "object",
# #                 "properties": {
# #                     "horizon":     {"type": "integer", "description": "Planning horizon in days (3-14)", "default": 7},
# #                     "simulations": {"type": "integer", "description": "MCTS simulations (50-200)",       "default": 100},
# #                 },
# #                 "required": [],
# #             },
# #         },
# #     },
# #     {
# #         "type": "function",
# #         "function": {
# #             "name": "execute_action",
# #             "description": (
# #                 "Execute the recommended action and step the simulation forward by 1 day. "
# #                 "Only call this when autonomy is AUTO_EXECUTE, or after human approval."
# #             ),
# #             "parameters": {"type": "object", "properties": {}, "required": []},
# #         },
# #     },
# #     {
# #         "type": "function",
# #         "function": {
# #             "name": "send_alert",
# #             "description": (
# #                 "Send an alert to the supply chain team. Use for ALERT_AND_WAIT or "
# #                 "ESCALATE situations, or any critical finding (expiry, stockout risk)."
# #             ),
# #             "parameters": {
# #                 "type": "object",
# #                 "properties": {
# #                     "message":            {"type": "string", "description": "Alert message text"},
# #                     "level":              {"type": "string", "enum": ["INFO", "WARNING", "CRITICAL"]},
# #                     "action_required":    {"type": "boolean"},
# #                     "recommended_action": {"type": "string", "description": "What the agent recommends"},
# #                 },
# #                 "required": ["message", "level"],
# #             },
# #         },
# #     },
# #     {
# #         "type": "function",
# #         "function": {
# #             "name": "log_decision",
# #             "description": (
# #                 "Log the agent's decision and reasoning to memory. "
# #                 "Always call this as the LAST step of every cycle."
# #             ),
# #             "parameters": {
# #                 "type": "object",
# #                 "properties": {
# #                     "action":      {"type": "string"},
# #                     "action_type": {"type": "string"},
# #                     "autonomy":    {"type": "string"},
# #                     "risk_score":  {"type": "number"},
# #                     "cost":        {"type": "number"},
# #                     "reward":      {"type": "number"},
# #                     "reasoning":   {"type": "string", "description": "Plain-English explanation of decision"},
# #                 },
# #                 "required": ["action", "action_type", "autonomy",
# #                              "risk_score", "cost", "reward", "reasoning"],
# #             },
# #         },
# #     },
# # ]

# # SYSTEM_PROMPT = """You are an autonomous supply chain agent for a biotech laboratory.

# # Your job each cycle:
# # 1. Call read_inventory — understand the current situation
# # 2. Call run_mcts_planner — get the AI-recommended action and risk score
# # 3. Decide what to do based on the autonomy level returned:
# #    - AUTO_EXECUTE  → call execute_action immediately, then log_decision
# #    - ALERT_AND_WAIT → call send_alert (WARNING, action_required=true), then log_decision. Do NOT execute.
# #    - ESCALATE      → call send_alert (CRITICAL, action_required=true), then log_decision. Do NOT execute.
# # 4. Always end with log_decision — include your plain-English reasoning.

# # Autonomy rules you must follow:
# # - If the recommended action is DoNothingAction → AUTO_EXECUTE always
# # - If an item has expiry_days ≤ 3 → treat as CRITICAL, send alert regardless
# # - If coverage_ratio < 0.5 for any critical reagent → send WARNING even if auto-executing
# # - Never execute if cost > $50,000 without explicit ALERT_AND_WAIT

# # Be concise in tool calls. Your reasoning in log_decision should be 2-3 sentences max,
# # written for a supply chain manager — no jargon.
# # """


# # # ══════════════════════════════════════════════════════════════════════════════
# # #  LLM CALL
# # # ══════════════════════════════════════════════════════════════════════════════

# # def _call_azure(messages: List[Dict], tools: List[Dict], api_key: str = "") -> Dict:
# #     """Raw call to Azure OpenAI chat completions endpoint."""
# #     key     = api_key or AZURE_API_KEY
# #     if not key:
# #         raise ValueError("Azure API key not set. Enter it in the sidebar.")
# #     url     = f"{AZURE_ENDPOINT}?api-version={AZURE_API_VERSION}"
# #     payload = json.dumps({
# #         "messages":    messages,
# #         "tools":       tools,
# #         "tool_choice": "auto",
# #         "max_tokens":  1000,
# #         "temperature": 0.1,
# #     }).encode()
# #     req = urllib.request.Request(
# #         url, data=payload,
# #         headers={"Content-Type": "application/json", "api-key": key},
# #         method="POST",
# #     )
# #     with urllib.request.urlopen(req, timeout=45) as r:
# #         return json.loads(r.read())


# # # ══════════════════════════════════════════════════════════════════════════════
# # #  TOOL DISPATCHER
# # # ══════════════════════════════════════════════════════════════════════════════

# # def _dispatch(
# #     tool_name: str,
# #     tool_args: Dict,
# #     *,
# #     state: SystemState,
# #     db_path: str,
# #     _mcts_result: Optional[Dict],
# #     _exec_result: Optional[Dict],
# #     _scenarios: Optional[List],
# #     material_filter: Optional[str] = None,
# # ) -> Tuple[Any, Optional[SystemState]]:
# #     """
# #     Route an LLM tool call to the actual Python function.
# #     Returns (result_dict, optional_new_state).
# #     """
# #     new_state = None

# #     if tool_name == "read_inventory":
# #         result = read_inventory(state)

# #     elif tool_name == "run_mcts_planner":
# #         horizon     = int(tool_args.get("horizon",     7))
# #         simulations = int(tool_args.get("simulations", 100))
# #         result      = run_mcts_planner(
# #             state, horizon=horizon, simulations=simulations,
# #             material_filter=material_filter,
# #         )
# #         # Regenerate scenarios for execute_action to use
# #         from src.demand.scenario_generator import ScenarioGenerator
# #         _scenarios[:] = ScenarioGenerator(
# #             horizon=horizon, n_scenarios=50
# #         ).generate(state)
# #         # Store for execute_action
# #         _mcts_result.update(result)

# #     elif tool_name == "execute_action":
# #         if not _mcts_result or "_action_obj" not in _mcts_result:
# #             result = {"error": "run_mcts_planner must be called first"}
# #         else:
# #             result    = execute_action(
# #                 state, _mcts_result["_action_obj"],
# #                 scenarios=_scenarios or None,
# #             )
# #             new_state = result.pop("_new_state", None)
# #             _exec_result.update(result)

# #     elif tool_name == "send_alert":
# #         result = send_alert(
# #             message            = tool_args.get("message", ""),
# #             level              = tool_args.get("level", "INFO"),
# #             action_required    = tool_args.get("action_required", False),
# #             recommended_action = tool_args.get("recommended_action", ""),
# #         )

# #     elif tool_name == "log_decision":
# #         reward = _exec_result.get("reward", 0.0) if _exec_result else 0.0
# #         result = log_decision(
# #             db_path    = db_path,
# #             day        = state.current_day,
# #             action     = tool_args.get("action", ""),
# #             action_type= tool_args.get("action_type", ""),
# #             autonomy   = tool_args.get("autonomy", ""),
# #             risk_score = float(tool_args.get("risk_score", 0)),
# #             cost       = float(tool_args.get("cost", 0)),
# #             reward     = float(tool_args.get("reward", reward)),
# #             reasoning  = tool_args.get("reasoning", ""),
# #         )

# #     else:
# #         result = {"error": f"Unknown tool: {tool_name}"}

# #     return result, new_state


# # # ══════════════════════════════════════════════════════════════════════════════
# # #  MAIN AGENT CYCLE
# # # ══════════════════════════════════════════════════════════════════════════════

# # def run_agent_cycle(
# #     state: SystemState,
# #     db_path: str = "data/inventory.db",
# #     max_turns: int = 12,
# #     api_key: str = "",
# #     material_filter: Optional[str] = None,
# # ) -> Dict[str, Any]:
# #     """
# #     Run one full perceive → plan → act → log cycle.

# #     Returns:
# #         {
# #           "new_state":   SystemState (updated if action was executed),
# #           "executed":    bool,
# #           "autonomy":    "AUTO_EXECUTE" | "ALERT_AND_WAIT" | "ESCALATE",
# #           "action":      str,
# #           "reasoning":   str,
# #           "reward":      float,
# #           "alerts":      [ alert dicts ],
# #           "thought_log": [ { role, content } ],   ← the agent's inner monologue
# #           "tool_calls":  [ { tool, args, result } ],
# #           "error":       str or None,
# #         }
# #     """
# #     messages: List[Dict] = [
# #         {"role": "system", "content": SYSTEM_PROMPT},
# #         {
# #             "role": "user",
# #             "content": (
# #                 f"Current simulation day: {state.current_day}. "
# #                 f"Budget remaining: ${state.budget_remaining:,.0f}. "
# #                 + (f"Focus this cycle on material: {material_filter}. "
# #                    f"Only evaluate actions and risks for {material_filter}. "
# #                    if material_filter else "Run a full portfolio planning cycle. ")
# #                 + "Please run your supply chain planning cycle now."
# #             ),
# #         },
# #     ]

# #     thought_log: List[Dict]  = []
# #     tool_calls_log: List     = []
# #     alerts: List[Dict]       = []
# #     new_state: SystemState   = state

# #     # Shared mutable containers passed into dispatcher
# #     _mcts_result: Dict = {}
# #     _exec_result: Dict = {}
# #     _scenarios:   List = []

# #     executed  = False
# #     autonomy  = "UNKNOWN"
# #     action    = "Do Nothing"
# #     reasoning = ""
# #     reward    = 0.0
# #     error     = None

# #     try:
# #         for turn in range(max_turns):
# #             response   = _call_azure(messages, TOOL_SCHEMAS, api_key=api_key)
# #             choice     = response["choices"][0]
# #             msg        = choice["message"]
# #             finish     = choice["finish_reason"]

# #             # Record the assistant turn
# #             messages.append(msg)
# #             thought_log.append({
# #                 "role":    "assistant",
# #                 "content": msg.get("content") or "",
# #                 "turn":    turn + 1,
# #             })

# #             # No tool calls → LLM finished
# #             if finish == "stop" or not msg.get("tool_calls"):
# #                 break

# #             # Process each tool call in this turn
# #             for tc in msg["tool_calls"]:
# #                 tool_name = tc["function"]["name"]
# #                 tool_args = json.loads(tc["function"]["arguments"] or "{}")

# #                 tool_result, maybe_new_state = _dispatch(
# #                     tool_name, tool_args,
# #                     state           = new_state,
# #                     db_path         = db_path,
# #                     _mcts_result    = _mcts_result,
# #                     _exec_result    = _exec_result,
# #                     _scenarios      = _scenarios,
# #                     material_filter = material_filter,
# #                 )

# #                 # Update running state if execution happened
# #                 if maybe_new_state is not None:
# #                     new_state = maybe_new_state
# #                     executed  = True
# #                     reward    = _exec_result.get("reward", 0.0)

# #                 # Collect alerts
# #                 if tool_name == "send_alert":
# #                     alerts.append(tool_result)

# #                 # Extract autonomy + reasoning from log_decision call
# #                 if tool_name == "log_decision":
# #                     autonomy  = tool_args.get("autonomy", autonomy)
# #                     action    = tool_args.get("action",   action)
# #                     reasoning = tool_args.get("reasoning", reasoning)

# #                 # Capture MCTS autonomy recommendation early
# #                 if tool_name == "run_mcts_planner" and "autonomy" in tool_result:
# #                     autonomy = tool_result["autonomy"]

# #                 # Strip internal objects before sending result back to LLM
# #                 safe_result = {
# #                     k: v for k, v in tool_result.items()
# #                     if not k.startswith("_")
# #                 }

# #                 tool_calls_log.append({
# #                     "tool":   tool_name,
# #                     "args":   tool_args,
# #                     "result": safe_result,
# #                 })

# #                 messages.append({
# #                     "role":         "tool",
# #                     "tool_call_id": tc["id"],
# #                     "content":      json.dumps(safe_result),
# #                 })

# #     except Exception as exc:
# #         error = str(exc)

# #     return {
# #         "new_state":   new_state,
# #         "executed":    executed,
# #         "autonomy":    autonomy,
# #         "action":      action,
# #         "reasoning":   reasoning,
# #         "reward":      reward,
# #         "alerts":      alerts,
# #         "thought_log": thought_log,
# #         "tool_calls":  tool_calls_log,
# #         "error":       error,
# #     }


# # # ══════════════════════════════════════════════════════════════════════════════
# # #  MEMORY READER  (for the audit trail tab)
# # # ══════════════════════════════════════════════════════════════════════════════

# # def load_agent_memory(db_path: str = "data/inventory.db"):
# #     """Load all agent decisions from memory table. Returns list of dicts."""
# #     import sqlite3 as _sq
# #     conn = _sq.connect(db_path)
# #     try:
# #         rows = conn.execute(
# #             "SELECT * FROM agent_memory ORDER BY id DESC"
# #         ).fetchall()
# #         cols = [d[0] for d in conn.execute(
# #             "SELECT * FROM agent_memory LIMIT 0"
# #         ).description or []]
# #         if not cols and rows:
# #             cols = ["id","timestamp","day","action","action_type","autonomy",
# #                     "risk_score","cost","reward","reasoning",
# #                     "human_override","override_reason"]
# #         return [dict(zip(cols, r)) for r in rows]
# #     except Exception:
# #         return []
# #     finally:
# #         conn.close()

# """
# Agent Orchestrator
# ==================
# The LLM (Azure GPT-4o-mini) is given 5 tools and a system prompt.
# It perceives the inventory, plans via MCTS, decides autonomy level,
# acts (or escalates), and logs every decision to memory.

# One call to  run_agent_cycle()  executes one full perceive→plan→act loop
# and returns a structured result the UI can render.
# """
# from __future__ import annotations
# import json
# import urllib.request
# from datetime import datetime
# from typing import Any, Dict, List, Optional, Tuple

# from src.core.state import SystemState
# from src.agent.tools import (
#     execute_action,
#     log_decision,
#     read_inventory,
#     run_mcts_planner,
#     send_alert,
# )

# # ── Azure OpenAI config ───────────────────────────────────────────────────────
# AZURE_ENDPOINT    = (
#     "https://bu24-demo.openai.azure.com/openai/deployments/"
#     "gpt-4o-mini/chat/completions"
# )
# AZURE_API_KEY     = ""  # overridden at runtime via UI
# AZURE_API_VERSION = "2025-01-01-preview"

# # ── Tool schemas for the LLM ──────────────────────────────────────────────────
# TOOL_SCHEMAS = [
#     {
#         "type": "function",
#         "function": {
#             "name": "read_inventory",
#             "description": (
#                 "Read current inventory state. Returns stock levels, expiry risk, "
#                 "safety stock coverage, and active market events. "
#                 "Always call this FIRST at the start of every cycle."
#             ),
#             "parameters": {"type": "object", "properties": {}, "required": []},
#         },
#     },
#     {
#         "type": "function",
#         "function": {
#             "name": "run_mcts_planner",
#             "description": (
#                 "Run the MCTS planning engine. Returns the best action, its risk score, "
#                 "CVaR, and an autonomy recommendation: AUTO_EXECUTE, ALERT_AND_WAIT, "
#                 "or ESCALATE. Call this after reading inventory."
#             ),
#             "parameters": {
#                 "type": "object",
#                 "properties": {
#                     "horizon":     {"type": "integer", "description": "Planning horizon in days (3-14)", "default": 7},
#                     "simulations": {"type": "integer", "description": "MCTS simulations (50-200)",       "default": 100},
#                 },
#                 "required": [],
#             },
#         },
#     },
#     {
#         "type": "function",
#         "function": {
#             "name": "execute_action",
#             "description": (
#                 "Execute the recommended action and step the simulation forward by 1 day. "
#                 "Only call this when autonomy is AUTO_EXECUTE, or after human approval."
#             ),
#             "parameters": {"type": "object", "properties": {}, "required": []},
#         },
#     },
#     {
#         "type": "function",
#         "function": {
#             "name": "send_alert",
#             "description": (
#                 "Send an alert to the supply chain team. Use for ALERT_AND_WAIT or "
#                 "ESCALATE situations, or any critical finding (expiry, stockout risk)."
#             ),
#             "parameters": {
#                 "type": "object",
#                 "properties": {
#                     "message":            {"type": "string", "description": "Alert message text"},
#                     "level":              {"type": "string", "enum": ["INFO", "WARNING", "CRITICAL"]},
#                     "action_required":    {"type": "boolean"},
#                     "recommended_action": {"type": "string", "description": "What the agent recommends"},
#                 },
#                 "required": ["message", "level"],
#             },
#         },
#     },
#     {
#         "type": "function",
#         "function": {
#             "name": "log_decision",
#             "description": (
#                 "Log the agent's decision and reasoning to memory. "
#                 "Always call this as the LAST step of every cycle."
#             ),
#             "parameters": {
#                 "type": "object",
#                 "properties": {
#                     "action":      {"type": "string"},
#                     "action_type": {"type": "string"},
#                     "autonomy":    {"type": "string"},
#                     "risk_score":  {"type": "number"},
#                     "cost":        {"type": "number"},
#                     "reward":      {"type": "number"},
#                     "reasoning":   {"type": "string", "description": "Plain-English explanation of decision"},
#                 },
#                 "required": ["action", "action_type", "autonomy",
#                              "risk_score", "cost", "reward", "reasoning"],
#             },
#         },
#     },
# ]

# SYSTEM_PROMPT = """You are an autonomous supply chain agent for a biotech laboratory.

# Your job each cycle:
# 1. Call read_inventory — understand the current situation.
# 2. Call run_mcts_planner — get the best action and risk score.
#    IMPORTANT TRIAGE RULE: If read_inventory finds multiple CRITICAL materials,
#    you must focus run_mcts_planner on the single most urgent material.
#    Priority order (highest first):
#      a) Expiry risk (expiry_days ≤ 3) — immediate loss
#      b) Highest stockout_penalty product with coverage_ratio < 0.5
#      c) Any product with coverage_ratio < 0.3
#    Do NOT run MCTS across the full portfolio when multiple critical items exist —
#    this dilutes the signal. Focus on one product per cycle.
# 3. Decide what to do based on the autonomy level returned:
#    - AUTO_EXECUTE  → call execute_action immediately, then log_decision
#    - ALERT_AND_WAIT → call send_alert (WARNING, action_required=true), then log_decision. Do NOT execute.
#    - ESCALATE      → call send_alert (CRITICAL, action_required=true), then log_decision. Do NOT execute.
# 4. Always end with log_decision — include your plain-English reasoning.

# Autonomy rules you must follow:
# - If the recommended action is DoNothingAction → AUTO_EXECUTE always
# - If an item has expiry_days ≤ 3 → treat as CRITICAL, send alert regardless
# - If coverage_ratio < 0.5 for any critical reagent → send WARNING even if auto-executing
# - Never execute if cost > $50,000 without explicit ALERT_AND_WAIT

# Penalty reference (stockout cost per unit short):
# - Biochemistry/Haematology Analysers: $6,500–$8,000 — highest priority
# - Troponin I Antibody (cardiac):       $5,000
# - COVID-19 PCR / HbA1c / Blood Culture: $2,500–$3,500
# - Standard reagents:                   $800–$1,500
# - Consumables / PPE:                   $200–$800

# Be concise. log_decision reasoning: 2-3 sentences, plain English, no jargon.
# """


# # ══════════════════════════════════════════════════════════════════════════════
# #  LLM CALL
# # ══════════════════════════════════════════════════════════════════════════════

# def _call_azure(messages: List[Dict], tools: List[Dict], api_key: str = "") -> Dict:
#     """Raw call to Azure OpenAI chat completions endpoint."""
#     key     = api_key or AZURE_API_KEY
#     if not key:
#         raise ValueError("Azure API key not set. Enter it in the sidebar.")
#     url     = f"{AZURE_ENDPOINT}?api-version={AZURE_API_VERSION}"
#     payload = json.dumps({
#         "messages":    messages,
#         "tools":       tools,
#         "tool_choice": "auto",
#         "max_tokens":  1000,
#         "temperature": 0.1,
#     }).encode()
#     req = urllib.request.Request(
#         url, data=payload,
#         headers={"Content-Type": "application/json", "api-key": key},
#         method="POST",
#     )
#     with urllib.request.urlopen(req, timeout=45) as r:
#         return json.loads(r.read())


# # ══════════════════════════════════════════════════════════════════════════════
# #  TOOL DISPATCHER
# # ══════════════════════════════════════════════════════════════════════════════

# def _dispatch(
#     tool_name: str,
#     tool_args: Dict,
#     *,
#     state: SystemState,
#     db_path: str,
#     _mcts_result: Optional[Dict],
#     _exec_result: Optional[Dict],
#     _scenarios: Optional[List],
#     material_filter: Optional[str] = None,
# ) -> Tuple[Any, Optional[SystemState]]:
#     """
#     Route an LLM tool call to the actual Python function.
#     Returns (result_dict, optional_new_state).
#     """
#     new_state = None

#     if tool_name == "read_inventory":
#         result = read_inventory(state)

#     elif tool_name == "run_mcts_planner":
#         horizon     = int(tool_args.get("horizon",     7))
#         simulations = int(tool_args.get("simulations", 100))
#         result      = run_mcts_planner(
#             state, horizon=horizon, simulations=simulations,
#             material_filter=material_filter,
#         )
#         # Regenerate scenarios for execute_action to use
#         from src.demand.scenario_generator import ScenarioGenerator
#         _scenarios[:] = ScenarioGenerator(
#             horizon=horizon, n_scenarios=50
#         ).generate(state)
#         # Store for execute_action
#         _mcts_result.update(result)

#     elif tool_name == "execute_action":
#         if not _mcts_result or "_action_obj" not in _mcts_result:
#             result = {"error": "run_mcts_planner must be called first"}
#         else:
#             result    = execute_action(
#                 state, _mcts_result["_action_obj"],
#                 scenarios=_scenarios or None,
#             )
#             new_state = result.pop("_new_state", None)
#             _exec_result.update(result)

#     elif tool_name == "send_alert":
#         result = send_alert(
#             message            = tool_args.get("message", ""),
#             level              = tool_args.get("level", "INFO"),
#             action_required    = tool_args.get("action_required", False),
#             recommended_action = tool_args.get("recommended_action", ""),
#         )

#     elif tool_name == "log_decision":
#         reward = _exec_result.get("reward", 0.0) if _exec_result else 0.0
#         result = log_decision(
#             db_path    = db_path,
#             day        = state.current_day,
#             action     = tool_args.get("action", ""),
#             action_type= tool_args.get("action_type", ""),
#             autonomy   = tool_args.get("autonomy", ""),
#             risk_score = float(tool_args.get("risk_score", 0)),
#             cost       = float(tool_args.get("cost", 0)),
#             reward     = float(tool_args.get("reward", reward)),
#             reasoning  = tool_args.get("reasoning", ""),
#         )

#     else:
#         result = {"error": f"Unknown tool: {tool_name}"}

#     return result, new_state


# # ══════════════════════════════════════════════════════════════════════════════
# #  MAIN AGENT CYCLE
# # ══════════════════════════════════════════════════════════════════════════════

# def run_agent_cycle(
#     state: SystemState,
#     db_path: str = "data/inventory.db",
#     max_turns: int = 12,
#     api_key: str = "",
#     material_filter: Optional[str] = None,
# ) -> Dict[str, Any]:
#     """
#     Run one full perceive → plan → act → log cycle.

#     Returns:
#         {
#           "new_state":   SystemState (updated if action was executed),
#           "executed":    bool,
#           "autonomy":    "AUTO_EXECUTE" | "ALERT_AND_WAIT" | "ESCALATE",
#           "action":      str,
#           "reasoning":   str,
#           "reward":      float,
#           "alerts":      [ alert dicts ],
#           "thought_log": [ { role, content } ],   ← the agent's inner monologue
#           "tool_calls":  [ { tool, args, result } ],
#           "error":       str or None,
#         }
#     """
#     messages: List[Dict] = [
#         {"role": "system", "content": SYSTEM_PROMPT},
#         {
#             "role": "user",
#             "content": (
#                 f"Current simulation day: {state.current_day}. "
#                 f"Budget remaining: ${state.budget_remaining:,.0f}. "
#                 + (f"Focus this cycle on material: {material_filter}. "
#                    f"Only evaluate actions and risks for {material_filter}. "
#                    if material_filter else "Run a full portfolio planning cycle. ")
#                 + "Please run your supply chain planning cycle now."
#             ),
#         },
#     ]

#     thought_log: List[Dict]  = []
#     tool_calls_log: List     = []
#     alerts: List[Dict]       = []
#     new_state: SystemState   = state

#     # Shared mutable containers passed into dispatcher
#     _mcts_result: Dict = {}
#     _exec_result: Dict = {}
#     _scenarios:   List = []

#     executed  = False
#     autonomy  = "UNKNOWN"
#     action    = "Do Nothing"
#     reasoning = ""
#     reward    = 0.0
#     error     = None

#     try:
#         for turn in range(max_turns):
#             response   = _call_azure(messages, TOOL_SCHEMAS, api_key=api_key)
#             choice     = response["choices"][0]
#             msg        = choice["message"]
#             finish     = choice["finish_reason"]

#             # Record the assistant turn
#             messages.append(msg)
#             thought_log.append({
#                 "role":    "assistant",
#                 "content": msg.get("content") or "",
#                 "turn":    turn + 1,
#             })

#             # No tool calls → LLM finished
#             if finish == "stop" or not msg.get("tool_calls"):
#                 break

#             # Process each tool call in this turn
#             for tc in msg["tool_calls"]:
#                 tool_name = tc["function"]["name"]
#                 tool_args = json.loads(tc["function"]["arguments"] or "{}")

#                 tool_result, maybe_new_state = _dispatch(
#                     tool_name, tool_args,
#                     state           = new_state,
#                     db_path         = db_path,
#                     _mcts_result    = _mcts_result,
#                     _exec_result    = _exec_result,
#                     _scenarios      = _scenarios,
#                     material_filter = material_filter,
#                 )

#                 # Update running state if execution happened
#                 if maybe_new_state is not None:
#                     new_state = maybe_new_state
#                     executed  = True
#                     reward    = _exec_result.get("reward", 0.0)

#                 # Collect alerts
#                 if tool_name == "send_alert":
#                     alerts.append(tool_result)

#                 # Extract autonomy + reasoning from log_decision call
#                 if tool_name == "log_decision":
#                     autonomy  = tool_args.get("autonomy", autonomy)
#                     action    = tool_args.get("action",   action)
#                     reasoning = tool_args.get("reasoning", reasoning)

#                 # Capture MCTS autonomy recommendation early
#                 if tool_name == "run_mcts_planner" and "autonomy" in tool_result:
#                     autonomy = tool_result["autonomy"]

#                 # Strip internal objects before sending result back to LLM
#                 safe_result = {
#                     k: v for k, v in tool_result.items()
#                     if not k.startswith("_")
#                 }

#                 tool_calls_log.append({
#                     "tool":   tool_name,
#                     "args":   tool_args,
#                     "result": safe_result,
#                 })

#                 messages.append({
#                     "role":         "tool",
#                     "tool_call_id": tc["id"],
#                     "content":      json.dumps(safe_result),
#                 })

#     except Exception as exc:
#         error = str(exc)

#     return {
#         "new_state":   new_state,
#         "executed":    executed,
#         "autonomy":    autonomy,
#         "action":      action,
#         "reasoning":   reasoning,
#         "reward":      reward,
#         "alerts":      alerts,
#         "thought_log": thought_log,
#         "tool_calls":  tool_calls_log,
#         "error":       error,
#     }


# # ══════════════════════════════════════════════════════════════════════════════
# #  MEMORY READER  (for the audit trail tab)
# # ══════════════════════════════════════════════════════════════════════════════

# def load_agent_memory(db_path: str = "data/inventory.db"):
#     """Load all agent decisions from memory table. Returns list of dicts."""
#     import sqlite3 as _sq
#     conn = _sq.connect(db_path)
#     try:
#         rows = conn.execute(
#             "SELECT * FROM agent_memory ORDER BY id DESC"
#         ).fetchall()
#         cols = [d[0] for d in conn.execute(
#             "SELECT * FROM agent_memory LIMIT 0"
#         ).description or []]
#         if not cols and rows:
#             cols = ["id","timestamp","day","action","action_type","autonomy",
#                     "risk_score","cost","reward","reasoning",
#                     "human_override","override_reason"]
#         return [dict(zip(cols, r)) for r in rows]
#     except Exception:
#         return []
#     finally:
#         conn.close()

"""
Agent Orchestrator
==================
The LLM (Azure GPT-4o-mini) is given 5 tools and a system prompt.
It perceives the inventory, plans via MCTS, decides autonomy level,
acts (or escalates), and logs every decision to memory.

One call to  run_agent_cycle()  executes one full perceive→plan→act loop
and returns a structured result the UI can render.
"""
from __future__ import annotations
import json
import urllib.request
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

from src.core.state import SystemState
from src.agent.tools import (
    execute_action,
    log_decision,
    read_inventory,
    run_mcts_planner,
    send_alert,
)

# ── Azure OpenAI config ───────────────────────────────────────────────────────
AZURE_ENDPOINT    = (
    "https://bu24-demo.openai.azure.com/openai/deployments/"
    "gpt-4o-mini/chat/completions"
)
AZURE_API_KEY     = ""  # overridden at runtime via UI
AZURE_API_VERSION = "2025-01-01-preview"

# ── Tool schemas for the LLM ──────────────────────────────────────────────────
TOOL_SCHEMAS = [
    {
        "type": "function",
        "function": {
            "name": "read_inventory",
            "description": (
                "Read current inventory state. Returns stock levels, expiry risk, "
                "safety stock coverage, and active market events. "
                "Always call this FIRST at the start of every cycle."
            ),
            "parameters": {"type": "object", "properties": {}, "required": []},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "run_mcts_planner",
            "description": (
                "Run the MCTS planning engine. Returns the best action, its risk score, "
                "CVaR, and an autonomy recommendation: AUTO_EXECUTE, ALERT_AND_WAIT, "
                "or ESCALATE. Call this after reading inventory."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "horizon":     {"type": "integer", "description": "Planning horizon in days (3-14)", "default": 7},
                    "simulations": {"type": "integer", "description": "MCTS simulations (50-200)",       "default": 100},
                },
                "required": [],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "execute_action",
            "description": (
                "Execute the recommended action and step the simulation forward by 1 day. "
                "Only call this when autonomy is AUTO_EXECUTE, or after human approval."
            ),
            "parameters": {"type": "object", "properties": {}, "required": []},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "send_alert",
            "description": (
                "Send an alert to the supply chain team. Use for ALERT_AND_WAIT or "
                "ESCALATE situations, or any critical finding (expiry, stockout risk)."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "message":            {"type": "string", "description": "Alert message text"},
                    "level":              {"type": "string", "enum": ["INFO", "WARNING", "CRITICAL"]},
                    "action_required":    {"type": "boolean"},
                    "recommended_action": {"type": "string", "description": "What the agent recommends"},
                },
                "required": ["message", "level"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "log_decision",
            "description": (
                "Log the agent's decision and reasoning to memory. "
                "Always call this as the LAST step of every cycle."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "action":      {"type": "string"},
                    "action_type": {"type": "string"},
                    "autonomy":    {"type": "string"},
                    "risk_score":  {"type": "number"},
                    "cost":        {"type": "number"},
                    "reward":      {"type": "number"},
                    "reasoning":   {"type": "string", "description": "Plain-English explanation of decision"},
                },
                "required": ["action", "action_type", "autonomy",
                             "risk_score", "cost", "reward", "reasoning"],
            },
        },
    },
]

SYSTEM_PROMPT = """You are an autonomous supply chain agent for a biotech laboratory.

Your job each cycle:
1. Call read_inventory — understand the current situation.
2. Call run_mcts_planner — get the best action and risk score.
   IMPORTANT TRIAGE RULE: If read_inventory finds multiple CRITICAL materials,
   you must focus run_mcts_planner on the single most urgent material.
   Priority order (highest first):
     a) Expiry risk (expiry_days ≤ 3) — immediate loss
     b) Highest stockout_penalty product with coverage_ratio < 0.5
     c) Any product with coverage_ratio < 0.3
   Do NOT run MCTS across the full portfolio when multiple critical items exist —
   this dilutes the signal. Focus on one product per cycle.
3. Decide what to do based on the autonomy level returned:
   - AUTO_EXECUTE  → call execute_action immediately, then log_decision
   - ALERT_AND_WAIT → call send_alert (WARNING, action_required=true), then log_decision. Do NOT execute.
   - ESCALATE      → call send_alert (CRITICAL, action_required=true), then log_decision. Do NOT execute.
4. Always end with log_decision — include your plain-English reasoning.

Autonomy rules you must follow:
- If the recommended action is DoNothingAction → AUTO_EXECUTE always
- If an item has expiry_days ≤ 3 → treat as CRITICAL, send alert regardless
- If coverage_ratio < 0.5 for any critical reagent → send WARNING even if auto-executing
- Never execute if cost > $50,000 without explicit ALERT_AND_WAIT

Penalty reference (stockout cost per unit short):
- Biochemistry/Haematology Analysers: $6,500–$8,000 — highest priority
- Troponin I Antibody (cardiac):       $5,000
- COVID-19 PCR / HbA1c / Blood Culture: $2,500–$3,500
- Standard reagents:                   $800–$1,500
- Consumables / PPE:                   $200–$800

Be concise. log_decision reasoning: 2-3 sentences, plain English, no jargon.
"""


# ══════════════════════════════════════════════════════════════════════════════
#  LLM CALL
# ══════════════════════════════════════════════════════════════════════════════

def _call_azure(messages: List[Dict], tools: List[Dict], api_key: str = "") -> Dict:
    """Raw call to Azure OpenAI chat completions endpoint."""
    key     = api_key or AZURE_API_KEY
    if not key:
        raise ValueError("Azure API key not set. Enter it in the sidebar.")
    url     = f"{AZURE_ENDPOINT}?api-version={AZURE_API_VERSION}"
    payload = json.dumps({
        "messages":    messages,
        "tools":       tools,
        "tool_choice": "auto",
        "max_tokens":  1000,
        "temperature": 0.1,
    }).encode()
    req = urllib.request.Request(
        url, data=payload,
        headers={"Content-Type": "application/json", "api-key": key},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=45) as r:
        return json.loads(r.read())


# ══════════════════════════════════════════════════════════════════════════════
#  TOOL DISPATCHER
# ══════════════════════════════════════════════════════════════════════════════

def _dispatch(
    tool_name: str,
    tool_args: Dict,
    *,
    state: SystemState,
    db_path: str,
    _mcts_result: Optional[Dict],
    _exec_result: Optional[Dict],
    _scenarios: Optional[List],
    material_filter: Optional[str] = None,
) -> Tuple[Any, Optional[SystemState]]:
    """
    Route an LLM tool call to the actual Python function.
    Returns (result_dict, optional_new_state).
    """
    new_state = None

    if tool_name == "read_inventory":
        result = read_inventory(state)
        # Auto-triage: find highest-penalty critical material
        # Store it so run_mcts_planner can focus on it automatically
        critical_mats = [m for m in result.get("materials", [])
                         if m["status"] == "CRITICAL"]
        if critical_mats:
            def _triage_score(m):
                cat = state.catalog.get(m["material_id"])
                pen = cat.stockout_penalty if cat else 0
                items = state.inventory.get(m["material_id"], [])
                min_exp = min(
                    (i.expiry_days for i in items if i.expiry_days is not None),
                    default=999,
                )
                return pen * (3 if min_exp <= 3 else 1)
            _top = max(critical_mats, key=_triage_score)
            _mcts_result["_auto_filter"] = _top["material_id"]
        else:
            _mcts_result["_auto_filter"] = None

    elif tool_name == "run_mcts_planner":
        horizon     = int(tool_args.get("horizon",     7))
        simulations = int(tool_args.get("simulations", 150))
        # Use auto-triage filter if no explicit filter was provided
        effective_filter = (
            material_filter or
            _mcts_result.get("_auto_filter") or
            None
        )
        result      = run_mcts_planner(
            state, horizon=horizon, simulations=simulations,
            material_filter=effective_filter,
        )
        # Regenerate scenarios for execute_action to use
        from src.demand.scenario_generator import ScenarioGenerator
        _scenarios[:] = ScenarioGenerator(
            horizon=horizon, n_scenarios=50
        ).generate(state)
        # Store for execute_action
        _mcts_result.update(result)

    elif tool_name == "execute_action":
        if not _mcts_result or "_action_obj" not in _mcts_result:
            result = {"error": "run_mcts_planner must be called first"}
        else:
            result    = execute_action(
                state, _mcts_result["_action_obj"],
                scenarios=_scenarios or None,
            )
            new_state = result.pop("_new_state", None)
            _exec_result.update(result)

    elif tool_name == "send_alert":
        result = send_alert(
            message            = tool_args.get("message", ""),
            level              = tool_args.get("level", "INFO"),
            action_required    = tool_args.get("action_required", False),
            recommended_action = tool_args.get("recommended_action", ""),
        )

    elif tool_name == "log_decision":
        reward = _exec_result.get("reward", 0.0) if _exec_result else 0.0
        result = log_decision(
            db_path    = db_path,
            day        = state.current_day,
            action     = tool_args.get("action", ""),
            action_type= tool_args.get("action_type", ""),
            autonomy   = tool_args.get("autonomy", ""),
            risk_score = float(tool_args.get("risk_score", 0)),
            cost       = float(tool_args.get("cost", 0)),
            reward     = float(tool_args.get("reward", reward)),
            reasoning  = tool_args.get("reasoning", ""),
        )

    else:
        result = {"error": f"Unknown tool: {tool_name}"}

    return result, new_state


# ══════════════════════════════════════════════════════════════════════════════
#  MAIN AGENT CYCLE
# ══════════════════════════════════════════════════════════════════════════════

def run_agent_cycle(
    state: SystemState,
    db_path: str = "data/inventory.db",
    max_turns: int = 12,
    api_key: str = "",
    material_filter: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Run one full perceive → plan → act → log cycle.

    Returns:
        {
          "new_state":   SystemState (updated if action was executed),
          "executed":    bool,
          "autonomy":    "AUTO_EXECUTE" | "ALERT_AND_WAIT" | "ESCALATE",
          "action":      str,
          "reasoning":   str,
          "reward":      float,
          "alerts":      [ alert dicts ],
          "thought_log": [ { role, content } ],   ← the agent's inner monologue
          "tool_calls":  [ { tool, args, result } ],
          "error":       str or None,
        }
    """
    messages: List[Dict] = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {
            "role": "user",
            "content": (
                f"Current simulation day: {state.current_day}. "
                f"Budget remaining: ${state.budget_remaining:,.0f}. "
                + (f"Focus this cycle on material: {material_filter}. "
                   f"Only evaluate actions and risks for {material_filter}. "
                   if material_filter else "Run a full portfolio planning cycle. ")
                + "Please run your supply chain planning cycle now."
            ),
        },
    ]

    thought_log: List[Dict]  = []
    tool_calls_log: List     = []
    alerts: List[Dict]       = []
    new_state: SystemState   = state

    # Shared mutable containers passed into dispatcher
    _mcts_result: Dict = {}
    _exec_result: Dict = {}
    _scenarios:   List = []

    executed  = False
    autonomy  = "UNKNOWN"
    action    = "Do Nothing"
    reasoning = ""
    reward    = 0.0
    error     = None

    try:
        for turn in range(max_turns):
            response   = _call_azure(messages, TOOL_SCHEMAS, api_key=api_key)
            choice     = response["choices"][0]
            msg        = choice["message"]
            finish     = choice["finish_reason"]

            # Record the assistant turn
            messages.append(msg)
            thought_log.append({
                "role":    "assistant",
                "content": msg.get("content") or "",
                "turn":    turn + 1,
            })

            # No tool calls → LLM finished
            if finish == "stop" or not msg.get("tool_calls"):
                break

            # Process each tool call in this turn
            for tc in msg["tool_calls"]:
                tool_name = tc["function"]["name"]
                tool_args = json.loads(tc["function"]["arguments"] or "{}")

                tool_result, maybe_new_state = _dispatch(
                    tool_name, tool_args,
                    state           = new_state,
                    db_path         = db_path,
                    _mcts_result    = _mcts_result,
                    _exec_result    = _exec_result,
                    _scenarios      = _scenarios,
                    material_filter = material_filter,
                )

                # Update running state if execution happened
                if maybe_new_state is not None:
                    new_state = maybe_new_state
                    executed  = True
                    reward    = _exec_result.get("reward", 0.0)

                # Collect alerts
                if tool_name == "send_alert":
                    alerts.append(tool_result)

                # Extract autonomy + reasoning from log_decision call
                if tool_name == "log_decision":
                    autonomy  = tool_args.get("autonomy", autonomy)
                    action    = tool_args.get("action",   action)
                    reasoning = tool_args.get("reasoning", reasoning)

                # Capture MCTS autonomy recommendation early
                if tool_name == "run_mcts_planner" and "autonomy" in tool_result:
                    autonomy = tool_result["autonomy"]

                # Strip internal objects before sending result back to LLM
                safe_result = {
                    k: v for k, v in tool_result.items()
                    if not k.startswith("_")
                }

                tool_calls_log.append({
                    "tool":   tool_name,
                    "args":   tool_args,
                    "result": safe_result,
                })

                messages.append({
                    "role":         "tool",
                    "tool_call_id": tc["id"],
                    "content":      json.dumps(safe_result),
                })

    except Exception as exc:
        error = str(exc)

    return {
        "new_state":   new_state,
        "executed":    executed,
        "autonomy":    autonomy,
        "action":      action,
        "reasoning":   reasoning,
        "reward":      reward,
        "alerts":      alerts,
        "thought_log": thought_log,
        "tool_calls":  tool_calls_log,
        "error":       error,
    }


# ══════════════════════════════════════════════════════════════════════════════
#  MEMORY READER  (for the audit trail tab)
# ══════════════════════════════════════════════════════════════════════════════

def load_agent_memory(db_path: str = "data/inventory.db"):
    """Load all agent decisions from memory table. Returns list of dicts."""
    import sqlite3 as _sq
    conn = _sq.connect(db_path)
    try:
        rows = conn.execute(
            "SELECT * FROM agent_memory ORDER BY id DESC"
        ).fetchall()
        cols = [d[0] for d in conn.execute(
            "SELECT * FROM agent_memory LIMIT 0"
        ).description or []]
        if not cols and rows:
            cols = ["id","timestamp","day","action","action_type","autonomy",
                    "risk_score","cost","reward","reasoning",
                    "human_override","override_reason"]
        return [dict(zip(cols, r)) for r in rows]
    except Exception:
        return []
    finally:
        conn.close()