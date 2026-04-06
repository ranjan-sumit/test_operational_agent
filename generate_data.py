# # # import os
# # # import sqlite3
# # # from datetime import datetime, timedelta

# # # import numpy as np
# # # import pandas as pd


# # # def generate_database(db_path: str = "data/inventory.db") -> None:
# # #     os.makedirs("data", exist_ok=True)
# # #     conn = sqlite3.connect(db_path)

# # #     materials = pd.DataFrame([
# # #         {
# # #             "material_id": "REAGENT1",
# # #             "name": "Critical Reagent",
# # #             "unit_cost": 50.0,
# # #             "stockout_penalty": 800.0,
# # #             "holding_cost_rate": 2.0,
# # #             "expiry_penalty": 100.0,
# # #         },
# # #         {
# # #             "material_id": "REAGENT2",
# # #             "name": "Secondary Reagent",
# # #             "unit_cost": 30.0,
# # #             "stockout_penalty": 400.0,
# # #             "holding_cost_rate": 1.5,
# # #             "expiry_penalty": 50.0,
# # #         },
# # #     ])
# # #     materials.to_sql("materials", conn, if_exists="replace", index=False)

# # #     suppliers = pd.DataFrame([
# # #         {
# # #             "supplier_id": "SUP1",
# # #             "name": "ThermoFisher",
# # #             "lead_time_mean": 5.0,
# # #             "lead_time_std": 1.5,
# # #             "reliability": 0.92,
# # #             "cost_multiplier": 1.0,
# # #         },
# # #         {
# # #             "supplier_id": "SUP2",
# # #             "name": "SigmaAldrich",
# # #             "lead_time_mean": 7.0,
# # #             "lead_time_std": 2.0,
# # #             "reliability": 0.88,
# # #             "cost_multiplier": 1.1,
# # #         },
# # #     ])
# # #     suppliers.to_sql("suppliers", conn, if_exists="replace", index=False)

# # #     locations = pd.DataFrame([
# # #         {"location_id": "WH1", "name": "Boston DC", "capacity": 10000},
# # #         {"location_id": "WH2", "name": "Chicago DC", "capacity": 8000},
# # #     ])
# # #     locations.to_sql("locations", conn, if_exists="replace", index=False)

# # #     inventory_rows = []
# # #     for mat_id in ["REAGENT1", "REAGENT2"]:
# # #         for loc in ["WH1", "WH2"]:
# # #             qty = int(np.random.randint(200, 800))
# # #             safety = 150 if mat_id == "REAGENT1" else 100
# # #             expiry = int(np.random.randint(5, 30) if mat_id == "REAGENT1" else np.random.randint(10, 60))
# # #             inventory_rows.append({
# # #                 "material_id": mat_id,
# # #                 "location": loc,
# # #                 "quantity": qty,
# # #                 "safety_stock": safety,
# # #                 "expiry_days": expiry,
# # #             })
# # #     pd.DataFrame(inventory_rows).to_sql("inventory", conn, if_exists="replace", index=False)

# # #     demand_history = []
# # #     start_date = datetime.now() - timedelta(days=90)
# # #     for mat_id in ["REAGENT1", "REAGENT2"]:
# # #         base = 400 if mat_id == "REAGENT1" else 250
# # #         for i in range(90):
# # #             dt = start_date + timedelta(days=i)
# # #             demand = max(0, int(np.random.normal(base, 50)))
# # #             demand_history.append({
# # #                 "material_id": mat_id,
# # #                 "date": dt.date().isoformat(),
# # #                 "demand_units": demand,
# # #             })
# # #     pd.DataFrame(demand_history).to_sql("demand_history", conn, if_exists="replace", index=False)

# # #     market_events = pd.DataFrame([
# # #         {
# # #             "material_id": "REAGENT1",
# # #             "start_day": 0,
# # #             "duration_days": 5,
# # #             "multiplier": 1.25,
# # #             "event_type": "promo",
# # #         },
# # #         {
# # #             "material_id": "REAGENT2",
# # #             "start_day": 12,
# # #             "duration_days": 4,
# # #             "multiplier": 0.80,
# # #             "event_type": "supply_softness",
# # #         },
# # #     ])
# # #     market_events.to_sql("market_events", conn, if_exists="replace", index=False)

# # #     conn.close()
# # #     print("✅ Synthetic database created at data/inventory.db")


# # # if __name__ == "__main__":
# # #     generate_database()


# # import os
# # import sqlite3
# # from datetime import datetime, timedelta

# # import numpy as np
# # import pandas as pd


# # def generate_database(db_path: str = "data/inventory.db") -> None:
# #     os.makedirs("data", exist_ok=True)
# #     conn = sqlite3.connect(db_path)

# #     # ---------- 1. Materials (10 products, different categories, expiry profiles) ----------
# #     materials_data = [
# #         # Critical reagents (short expiry, high penalty)
# #         {"material_id": "REAG_CRIT01", "name": "Monoclonal Antibody XYZ", "category": "Antibody",
# #          "unit_cost": 250.0, "stockout_penalty": 2000.0, "holding_cost_rate": 3.0, "expiry_penalty": 500.0,
# #          "avg_daily_demand": 45, "demand_volatility": 15, "expiry_days_min": 14, "expiry_days_max": 30},
# #         {"material_id": "REAG_CRIT02", "name": "Enzyme Blend ABC", "category": "Enzyme",
# #          "unit_cost": 180.0, "stockout_penalty": 1500.0, "holding_cost_rate": 2.5, "expiry_penalty": 400.0,
# #          "avg_daily_demand": 60, "demand_volatility": 20, "expiry_days_min": 10, "expiry_days_max": 25},
# #         {"material_id": "REAG_CRIT03", "name": "Cell Culture Media", "category": "Media",
# #          "unit_cost": 120.0, "stockout_penalty": 1200.0, "holding_cost_rate": 2.0, "expiry_penalty": 300.0,
# #          "avg_daily_demand": 100, "demand_volatility": 25, "expiry_days_min": 30, "expiry_days_max": 60},
# #         # Standard reagents (medium expiry)
# #         {"material_id": "REAG_STD01", "name": "PCR Master Mix", "category": "Molecular Biology",
# #          "unit_cost": 85.0, "stockout_penalty": 600.0, "holding_cost_rate": 1.5, "expiry_penalty": 150.0,
# #          "avg_daily_demand": 80, "demand_volatility": 18, "expiry_days_min": 60, "expiry_days_max": 120},
# #         {"material_id": "REAG_STD02", "name": "Buffer Solution pH 7.4", "category": "Buffer",
# #          "unit_cost": 35.0, "stockout_penalty": 400.0, "holding_cost_rate": 1.0, "expiry_penalty": 50.0,
# #          "avg_daily_demand": 150, "demand_volatility": 30, "expiry_days_min": 90, "expiry_days_max": 180},
# #         {"material_id": "REAG_STD03", "name": "Protein Ladder", "category": "Protein",
# #          "unit_cost": 200.0, "stockout_penalty": 900.0, "holding_cost_rate": 2.0, "expiry_penalty": 200.0,
# #          "avg_daily_demand": 30, "demand_volatility": 10, "expiry_days_min": 60, "expiry_days_max": 120},
# #         # Plastics & consumables (long expiry, low penalty)
# #         {"material_id": "CONS_TUBE01", "name": "Microcentrifuge Tubes (2mL)", "category": "Plastic",
# #          "unit_cost": 12.0, "stockout_penalty": 150.0, "holding_cost_rate": 0.5, "expiry_penalty": 5.0,
# #          "avg_daily_demand": 500, "demand_volatility": 80, "expiry_days_min": 180, "expiry_days_max": 365},
# #         {"material_id": "CONS_TIP01", "name": "Filter Pipette Tips (200µL)", "category": "Plastic",
# #          "unit_cost": 18.0, "stockout_penalty": 200.0, "holding_cost_rate": 0.6, "expiry_penalty": 5.0,
# #          "avg_daily_demand": 800, "demand_volatility": 100, "expiry_days_min": 180, "expiry_days_max": 365},
# #         {"material_id": "CONS_PLATE01", "name": "96-Well Assay Plate", "category": "Plastic",
# #          "unit_cost": 45.0, "stockout_penalty": 350.0, "holding_cost_rate": 0.8, "expiry_penalty": 10.0,
# #          "avg_daily_demand": 200, "demand_volatility": 40, "expiry_days_min": 180, "expiry_days_max": 365},
# #         {"material_id": "CONS_GLOVE01", "name": "Nitrile Gloves (Box)", "category": "Safety",
# #          "unit_cost": 15.0, "stockout_penalty": 100.0, "holding_cost_rate": 0.4, "expiry_penalty": 2.0,
# #          "avg_daily_demand": 300, "demand_volatility": 50, "expiry_days_min": 365, "expiry_days_max": 730},
# #     ]

# #     materials = pd.DataFrame(materials_data)
# #     # Keep only columns needed for DB
# #     materials_db = materials[["material_id", "name", "unit_cost", "stockout_penalty", "holding_cost_rate", "expiry_penalty"]]
# #     materials_db.to_sql("materials", conn, if_exists="replace", index=False)

# #     # ---------- 2. Suppliers (5 suppliers with realistic profiles) ----------
# #     suppliers_data = [
# #         {"supplier_id": "SUP_THERMO", "name": "Thermo Fisher Scientific", "lead_time_mean": 5.0, "lead_time_std": 1.5, "reliability": 0.95, "cost_multiplier": 1.0},
# #         {"supplier_id": "SUP_SIGMA", "name": "Sigma-Aldrich (Merck)", "lead_time_mean": 7.0, "lead_time_std": 2.0, "reliability": 0.92, "cost_multiplier": 1.05},
# #         {"supplier_id": "SUP_CORNING", "name": "Corning Life Sciences", "lead_time_mean": 6.0, "lead_time_std": 1.8, "reliability": 0.94, "cost_multiplier": 0.98},
# #         {"supplier_id": "SUP_BD", "name": "BD Biosciences", "lead_time_mean": 8.0, "lead_time_std": 2.5, "reliability": 0.90, "cost_multiplier": 1.10},
# #         {"supplier_id": "SUP_ROCHE", "name": "Roche Diagnostics", "lead_time_mean": 10.0, "lead_time_std": 3.0, "reliability": 0.88, "cost_multiplier": 1.15},
# #     ]
# #     suppliers = pd.DataFrame(suppliers_data)
# #     suppliers.to_sql("suppliers", conn, if_exists="replace", index=False)

# #     # ---------- 3. Locations (4 DCs across US) ----------
# #     locations_data = [
# #         {"location_id": "LOC_BOS", "name": "Boston DC (Northeast)", "capacity": 25000, "region": "Northeast"},
# #         {"location_id": "LOC_ATL", "name": "Atlanta DC (Southeast)", "capacity": 20000, "region": "Southeast"},
# #         {"location_id": "LOC_CHI", "name": "Chicago DC (Midwest)", "capacity": 22000, "region": "Midwest"},
# #         {"location_id": "LOC_LAX", "name": "Los Angeles DC (West)", "capacity": 18000, "region": "West"},
# #     ]
# #     locations = pd.DataFrame(locations_data)
# #     locations.to_sql("locations", conn, if_exists="replace", index=False)

# #     # ---------- 4. Inventory (for each material at each location, with expiry) ----------
# #     inventory_rows = []
# #     for idx, mat in materials.iterrows():
# #         mat_id = mat["material_id"]
# #         # Use material-specific expiry range
# #         expiry_min = materials_data[idx]["expiry_days_min"]
# #         expiry_max = materials_data[idx]["expiry_days_max"]
# #         # Safety stock proportional to demand volatility
# #         avg_demand = materials_data[idx]["avg_daily_demand"]
# #         volatility = materials_data[idx]["demand_volatility"]
# #         safety_stock = int(avg_demand * 2.5 + volatility * 1.5)  # heuristic

# #         for loc in locations_data:
# #             loc_id = loc["location_id"]
# #             # Current stock: between safety stock and 3x safety stock
# #             qty = np.random.randint(safety_stock, int(safety_stock * 3))
# #             # Expiry days: random within material range
# #             expiry = np.random.randint(expiry_min, expiry_max)
# #             inventory_rows.append({
# #                 "material_id": mat_id,
# #                 "location": loc_id,
# #                 "quantity": qty,
# #                 "safety_stock": safety_stock,
# #                 "expiry_days": expiry,
# #             })
# #     pd.DataFrame(inventory_rows).to_sql("inventory", conn, if_exists="replace", index=False)

# #     # ---------- 5. Demand History (365 days, with trend + seasonality + noise) ----------
# #     demand_history = []
# #     start_date = datetime.now() - timedelta(days=365)
# #     # Add a yearly sinusoidal seasonality and a slight upward trend
# #     for mat_idx, mat in materials.iterrows():
# #         mat_id = mat["material_id"]
# #         base_avg = materials_data[mat_idx]["avg_daily_demand"]
# #         volatility = materials_data[mat_idx]["demand_volatility"]
# #         trend_factor = 1.02  # 2% growth over year
# #         for day_offset in range(365):
# #             dt = start_date + timedelta(days=day_offset)
# #             # Seasonal component (peak in summer, trough in winter)
# #             season = 1 + 0.15 * np.sin(2 * np.pi * (day_offset - 180) / 365)  # peak around day 180 (July)
# #             # Trend
# #             trend = 1 + (day_offset / 365) * (trend_factor - 1)
# #             # Random noise
# #             noise = np.random.normal(0, volatility * 0.2)
# #             demand = max(0, int(base_avg * season * trend + noise + np.random.normal(0, volatility * 0.5)))
# #             demand_history.append({
# #                 "material_id": mat_id,
# #                 "date": dt.date().isoformat(),
# #                 "demand_units": demand,
# #             })
# #     pd.DataFrame(demand_history).to_sql("demand_history", conn, if_exists="replace", index=False)

# #     # ---------- 6. Market Events (realistic: promos, supply shocks, weather) ----------
# #     # Generate events across multiple materials
# #     events = []
# #     # Promo on critical reagents (weeks 2 and 3)
# #     for mat in ["REAG_CRIT01", "REAG_CRIT02"]:
# #         events.append({"material_id": mat, "start_day": 14, "duration_days": 7, "multiplier": 1.35, "event_type": "promotion"})
# #     # Supply disruption for a standard reagent (day 30-35)
# #     events.append({"material_id": "REAG_STD01", "start_day": 30, "duration_days": 5, "multiplier": 0.0, "event_type": "supply_disruption"})
# #     # Weather impact on West coast (affects plastics)
# #     for mat in ["CONS_TUBE01", "CONS_TIP01"]:
# #         events.append({"material_id": mat, "start_day": 60, "duration_days": 4, "multiplier": 0.5, "event_type": "weather_delay"})
# #     # New product launch (demand spike for assay plates)
# #     events.append({"material_id": "CONS_PLATE01", "start_day": 90, "duration_days": 14, "multiplier": 1.5, "event_type": "new_product_launch"})
# #     # Summer holiday slowdown (all materials)
# #     for mat in materials["material_id"]:
# #         events.append({"material_id": mat, "start_day": 210, "duration_days": 10, "multiplier": 0.7, "event_type": "holiday_slowdown"})
# #     # Black Friday promo (critical and standard reagents)
# #     for mat in ["REAG_CRIT01", "REAG_CRIT02", "REAG_STD01", "REAG_STD02"]:
# #         events.append({"material_id": mat, "start_day": 330, "duration_days": 5, "multiplier": 1.45, "event_type": "black_friday"})

# #     market_events = pd.DataFrame(events)
# #     market_events.to_sql("market_events", conn, if_exists="replace", index=False)

# #     conn.close()
# #     print("✅ Enhanced synthetic database created at data/inventory.db")
# #     print(f"   - {len(materials)} materials")
# #     print(f"   - {len(suppliers)} suppliers")
# #     print(f"   - {len(locations_data)} locations")
# #     print(f"   - {len(inventory_rows)} inventory records")
# #     print(f"   - {len(demand_history)} demand history records")
# #     print(f"   - {len(events)} market events")


# # if __name__ == "__main__":
# #     # Set seed for reproducibility
# #     np.random.seed(42)
# #     generate_database()

# """
# generate_database.py
# ====================
# Generates inventory.db with:
#   - 18 real Indian diagnostics/biotech products
#   - 6 real suppliers
#   - 4 Indian distribution centres
#   - 365 days demand history with seasonality + trend
#   - 20 named business scenarios (all in one DB)

# Run:  python generate_database.py
# """
# import json
# import os
# import sqlite3
# from datetime import datetime, timedelta

# import numpy as np
# import pandas as pd

# np.random.seed(42)

# # ─────────────────────────────────────────────────────────────────────────────
# #  MASTER DATA
# # ─────────────────────────────────────────────────────────────────────────────

# MATERIALS = [
#     # ── Critical Reagents ────────────────────────────────────────────────────
#     {"material_id": "DIAG_CRIT01", "name": "COVID-19 PCR Master Mix",
#      "category": "Critical Reagent",
#      "unit_cost": 320.0,  "stockout_penalty": 3500.0, "holding_cost_rate": 4.0, "expiry_penalty": 600.0,
#      "avg_daily_demand": 55,  "demand_volatility": 20, "expiry_days_min": 14,  "expiry_days_max": 35,
#      "primary_supplier": "SUP_ROCHE"},

#     {"material_id": "DIAG_CRIT02", "name": "Troponin I Antibody (Cardiac)",
#      "category": "Critical Reagent",
#      "unit_cost": 480.0,  "stockout_penalty": 5000.0, "holding_cost_rate": 5.0, "expiry_penalty": 800.0,
#      "avg_daily_demand": 28,  "demand_volatility": 10, "expiry_days_min": 10,  "expiry_days_max": 21,
#      "primary_supplier": "SUP_ABBOTT"},

#     {"material_id": "DIAG_CRIT03", "name": "HbA1c Calibrator Solution",
#      "category": "Critical Reagent",
#      "unit_cost": 210.0,  "stockout_penalty": 2000.0, "holding_cost_rate": 3.0, "expiry_penalty": 450.0,
#      "avg_daily_demand": 80,  "demand_volatility": 18, "expiry_days_min": 20,  "expiry_days_max": 45,
#      "primary_supplier": "SUP_BIORAD"},

#     {"material_id": "DIAG_CRIT04", "name": "Blood Culture Broth (Aerobic)",
#      "category": "Critical Reagent",
#      "unit_cost": 145.0,  "stockout_penalty": 2500.0, "holding_cost_rate": 3.5, "expiry_penalty": 400.0,
#      "avg_daily_demand": 65,  "demand_volatility": 15, "expiry_days_min": 14,  "expiry_days_max": 30,
#      "primary_supplier": "SUP_BECTON"},

#     # ── Standard Reagents ────────────────────────────────────────────────────
#     {"material_id": "DIAG_STD01", "name": "Dengue NS1 ELISA Kit",
#      "category": "Standard Reagent",
#      "unit_cost": 95.0,   "stockout_penalty": 1200.0, "holding_cost_rate": 1.8, "expiry_penalty": 200.0,
#      "avg_daily_demand": 45,  "demand_volatility": 30, "expiry_days_min": 60,  "expiry_days_max": 120,
#      "primary_supplier": "SUP_MERIL"},

#     {"material_id": "DIAG_STD02", "name": "CBC Diluent Solution",
#      "category": "Standard Reagent",
#      "unit_cost": 38.0,   "stockout_penalty": 800.0,  "holding_cost_rate": 1.0, "expiry_penalty": 80.0,
#      "avg_daily_demand": 180, "demand_volatility": 25, "expiry_days_min": 90,  "expiry_days_max": 180,
#      "primary_supplier": "SUP_BECTON"},

#     {"material_id": "DIAG_STD03", "name": "Lipid Panel Control Serum",
#      "category": "Standard Reagent",
#      "unit_cost": 175.0,  "stockout_penalty": 900.0,  "holding_cost_rate": 2.0, "expiry_penalty": 180.0,
#      "avg_daily_demand": 35,  "demand_volatility": 8,  "expiry_days_min": 60,  "expiry_days_max": 120,
#      "primary_supplier": "SUP_BIORAD"},

#     {"material_id": "DIAG_STD04", "name": "Hepatitis B Surface Antigen Kit",
#      "category": "Standard Reagent",
#      "unit_cost": 82.0,   "stockout_penalty": 1500.0, "holding_cost_rate": 1.2, "expiry_penalty": 150.0,
#      "avg_daily_demand": 60,  "demand_volatility": 12, "expiry_days_min": 90,  "expiry_days_max": 180,
#      "primary_supplier": "SUP_ABBOTT"},

#     {"material_id": "DIAG_STD05", "name": "Urine Dipstick Strips (100-pk)",
#      "category": "Standard Reagent",
#      "unit_cost": 22.0,   "stockout_penalty": 400.0,  "holding_cost_rate": 0.6, "expiry_penalty": 40.0,
#      "avg_daily_demand": 220, "demand_volatility": 35, "expiry_days_min": 180, "expiry_days_max": 365,
#      "primary_supplier": "SUP_MERIL"},

#     # ── Consumables ──────────────────────────────────────────────────────────
#     {"material_id": "CONS_VAC01", "name": "Vacutainer EDTA Tubes (100-pk)",
#      "category": "Consumable",
#      "unit_cost": 28.0,   "stockout_penalty": 350.0,  "holding_cost_rate": 0.5, "expiry_penalty": 15.0,
#      "avg_daily_demand": 320, "demand_volatility": 45, "expiry_days_min": 365, "expiry_days_max": 730,
#      "primary_supplier": "SUP_BECTON"},

#     {"material_id": "CONS_VAC02", "name": "Vacutainer SST Tubes (100-pk)",
#      "category": "Consumable",
#      "unit_cost": 32.0,   "stockout_penalty": 350.0,  "holding_cost_rate": 0.5, "expiry_penalty": 15.0,
#      "avg_daily_demand": 280, "demand_volatility": 40, "expiry_days_min": 365, "expiry_days_max": 730,
#      "primary_supplier": "SUP_BECTON"},

#     {"material_id": "CONS_SWB01", "name": "Nasopharyngeal Swab Kit",
#      "category": "Consumable",
#      "unit_cost": 18.0,   "stockout_penalty": 600.0,  "holding_cost_rate": 0.4, "expiry_penalty": 20.0,
#      "avg_daily_demand": 150, "demand_volatility": 80, "expiry_days_min": 180, "expiry_days_max": 365,
#      "primary_supplier": "SUP_MERIL"},

#     {"material_id": "CONS_PPE01", "name": "Nitrile Exam Gloves (Box/100)",
#      "category": "PPE",
#      "unit_cost": 14.0,   "stockout_penalty": 200.0,  "holding_cost_rate": 0.3, "expiry_penalty": 5.0,
#      "avg_daily_demand": 280, "demand_volatility": 50, "expiry_days_min": 365, "expiry_days_max": 730,
#      "primary_supplier": "SUP_MERIL"},

#     {"material_id": "CONS_PPE02", "name": "N95 Respirator Masks (Box/20)",
#      "category": "PPE",
#      "unit_cost": 42.0,   "stockout_penalty": 800.0,  "holding_cost_rate": 0.7, "expiry_penalty": 30.0,
#      "avg_daily_demand": 90,  "demand_volatility": 60, "expiry_days_min": 365, "expiry_days_max": 730,
#      "primary_supplier": "SUP_MERIL"},

#     {"material_id": "CONS_TIP01", "name": "200µL Filter Tips (Rack/96)",
#      "category": "Lab Consumable",
#      "unit_cost": 16.0,   "stockout_penalty": 180.0,  "holding_cost_rate": 0.3, "expiry_penalty": 5.0,
#      "avg_daily_demand": 420, "demand_volatility": 60, "expiry_days_min": 365, "expiry_days_max": 730,
#      "primary_supplier": "SUP_BIORAD"},

#     {"material_id": "CONS_PLT01", "name": "96-Well PCR Plate",
#      "category": "Lab Consumable",
#      "unit_cost": 55.0,   "stockout_penalty": 500.0,  "holding_cost_rate": 0.8, "expiry_penalty": 25.0,
#      "avg_daily_demand": 120, "demand_volatility": 30, "expiry_days_min": 365, "expiry_days_max": 730,
#      "primary_supplier": "SUP_ROCHE"},

#     # ── Instrument Reagents ──────────────────────────────────────────────────
#     {"material_id": "INST_CAL01", "name": "Haematology Analyser Calibrator",
#      "category": "Instrument Reagent",
#      "unit_cost": 580.0,  "stockout_penalty": 8000.0, "holding_cost_rate": 6.0, "expiry_penalty": 900.0,
#      "avg_daily_demand": 12,  "demand_volatility": 4,  "expiry_days_min": 14,  "expiry_days_max": 30,
#      "primary_supplier": "SUP_SIEMENS"},

#     {"material_id": "INST_CAL02", "name": "Biochemistry Analyser Control",
#      "category": "Instrument Reagent",
#      "unit_cost": 420.0,  "stockout_penalty": 6500.0, "holding_cost_rate": 5.0, "expiry_penalty": 700.0,
#      "avg_daily_demand": 18,  "demand_volatility": 5,  "expiry_days_min": 14,  "expiry_days_max": 28,
#      "primary_supplier": "SUP_SIEMENS"},
# ]

# SUPPLIERS = [
#     {"supplier_id": "SUP_ABBOTT",  "name": "Abbott Diagnostics India",      "lead_time_mean": 4.0,  "lead_time_std": 1.2, "reliability": 0.96, "cost_multiplier": 1.00},
#     {"supplier_id": "SUP_ROCHE",   "name": "Roche Diagnostics India",       "lead_time_mean": 6.0,  "lead_time_std": 1.8, "reliability": 0.93, "cost_multiplier": 1.10},
#     {"supplier_id": "SUP_BECTON",  "name": "Becton Dickinson India",        "lead_time_mean": 5.0,  "lead_time_std": 1.5, "reliability": 0.94, "cost_multiplier": 1.05},
#     {"supplier_id": "SUP_BIORAD",  "name": "Bio-Rad Laboratories India",    "lead_time_mean": 8.0,  "lead_time_std": 2.5, "reliability": 0.89, "cost_multiplier": 1.08},
#     {"supplier_id": "SUP_MERIL",   "name": "Meril Life Sciences",           "lead_time_mean": 3.0,  "lead_time_std": 1.0, "reliability": 0.91, "cost_multiplier": 0.92},
#     {"supplier_id": "SUP_SIEMENS", "name": "Siemens Healthineers India",    "lead_time_mean": 10.0, "lead_time_std": 3.0, "reliability": 0.87, "cost_multiplier": 1.20},
# ]

# LOCATIONS = [
#     {"location_id": "LOC_MUM", "name": "Mumbai Central Warehouse",    "capacity": 30000, "region": "West"},
#     {"location_id": "LOC_DEL", "name": "Delhi NCR Distribution Hub",  "capacity": 28000, "region": "North"},
#     {"location_id": "LOC_BLR", "name": "Bangalore South Depot",       "capacity": 22000, "region": "South"},
#     {"location_id": "LOC_HYD", "name": "Hyderabad Regional Centre",   "capacity": 20000, "region": "South"},
# ]

# # ─────────────────────────────────────────────────────────────────────────────
# #  20 SCENARIOS
# # ─────────────────────────────────────────────────────────────────────────────

# SCENARIOS = [
#     {
#         "scenario_id":    "S01_BASELINE",
#         "name":           "The Quiet Day — All Products Healthy",
#         "category":       "Baseline",
#         "difficulty":     "LOW",
#         "description":    "All 18 products are above safety stock with healthy coverage. No market events active. A typical stable operating day for the supply chain team.",
#         "expected_action":"Agent should recommend Do Nothing across the portfolio and confirm healthy status.",
#         "business_impact":"Low risk. Missing this scenario would mean unnecessary procurement spend.",
#         "config_json": json.dumps({
#             "inventory_overrides": [],
#             "market_events": []
#         }),
#     },
#     {
#         "scenario_id":    "S02_CRITICAL_LOW",
#         "name":           "Critical Reagent Running Low — COVID PCR Mix",
#         "category":       "Stock Crisis",
#         "difficulty":     "MEDIUM",
#         "description":    "COVID-19 PCR Master Mix is down to 25% of safety stock across all warehouses. At current demand rates, stockout will occur in 6 days. Supplier lead time is 4 days — the window is tight.",
#         "expected_action":"Agent should auto-execute emergency procurement from Roche Diagnostics India.",
#         "business_impact":"Stockout halts all COVID-19 diagnostic testing. Penalty: ₹3,500 per unit short.",
#         "config_json": json.dumps({
#             "inventory_overrides": [
#                 {"material_id": "DIAG_CRIT01", "location": "ALL", "quantity_pct_of_safety": 0.25, "expiry_days": None}
#             ],
#             "market_events": []
#         }),
#     },
#     {
#         "scenario_id":    "S03_EXPIRY_CRISIS",
#         "name":           "Expiry Crisis — Blood Culture Broth",
#         "category":       "Expiry Risk",
#         "difficulty":     "MEDIUM",
#         "description":    "Blood Culture Broth (Aerobic) has a batch expiring in 3 days across all distribution centres. Current stock is adequate in quantity but will become worthless. Immediate disposal and reorder needed.",
#         "expected_action":"Agent should recommend disposal of expiring stock followed by emergency procurement.",
#         "business_impact":"Write-off loss of ₹400/unit on expired stock. Microbiology testing halted after expiry.",
#         "config_json": json.dumps({
#             "inventory_overrides": [
#                 {"material_id": "DIAG_CRIT04", "location": "ALL", "quantity_pct_of_safety": 1.8, "expiry_days": 3}
#             ],
#             "market_events": []
#         }),
#     },
#     {
#         "scenario_id":    "S04_WAREHOUSE_IMBALANCE",
#         "name":           "Warehouse Imbalance — CBC Diluent",
#         "category":       "Transfer Opportunity",
#         "difficulty":     "LOW",
#         "description":    "Mumbai warehouse has 3x excess CBC Diluent Solution while Delhi NCR Hub is at 40% safety stock. A direct inter-warehouse transfer costs far less than new procurement.",
#         "expected_action":"Agent should recommend a warehouse transfer from Mumbai to Delhi — no new procurement needed.",
#         "business_impact":"If transfer is missed, Delhi will need emergency procurement at full cost. Transfer saves ~40% of procurement cost.",
#         "config_json": json.dumps({
#             "inventory_overrides": [
#                 {"material_id": "DIAG_STD02", "location": "LOC_MUM", "quantity_pct_of_safety": 3.2, "expiry_days": None},
#                 {"material_id": "DIAG_STD02", "location": "LOC_DEL", "quantity_pct_of_safety": 0.4, "expiry_days": None},
#             ],
#             "market_events": []
#         }),
#     },
#     {
#         "scenario_id":    "S05_DENGUE_SEASON",
#         "name":           "Monsoon Season Demand Spike — Dengue NS1 Kit",
#         "category":       "Demand Surge",
#         "difficulty":     "MEDIUM",
#         "description":    "Monsoon season has arrived. Dengue NS1 ELISA Kit demand is spiking +80% above baseline for the next 14 days. Current stock was sized for normal demand and now has only 5-day coverage.",
#         "expected_action":"Agent should escalate for emergency procurement given the cost and severity of the spike.",
#         "business_impact":"Dengue testing backlog builds rapidly in monsoon. Every missed test is a delayed diagnosis. Penalty: ₹1,200/unit short.",
#         "config_json": json.dumps({
#             "inventory_overrides": [
#                 {"material_id": "DIAG_STD01", "location": "ALL", "quantity_pct_of_safety": 0.9, "expiry_days": None}
#             ],
#             "market_events": [
#                 {"material_id": "DIAG_STD01", "multiplier": 1.8, "duration_days": 14, "event_type": "demand_spike"}
#             ]
#         }),
#     },
#     {
#         "scenario_id":    "S06_SOLE_SOURCE_DISRUPTION",
#         "name":           "Sole-Source Supplier Disruption — Haematology Calibrator",
#         "category":       "Supply Shock",
#         "difficulty":     "HIGH",
#         "description":    "Siemens Healthineers India — the only supplier for Haematology Analyser Calibrator — has announced a 7-day supply disruption due to port congestion. Current stock gives only 8 days of coverage. Zero buffer once disruption hits.",
#         "expected_action":"Agent should escalate CRITICAL procurement immediately to build buffer stock before the disruption window.",
#         "business_impact":"Haematology analysers go offline without calibrator. All CBC tests halted. Penalty: ₹8,000/unit short.",
#         "config_json": json.dumps({
#             "inventory_overrides": [
#                 {"material_id": "INST_CAL01", "location": "ALL", "quantity_pct_of_safety": 1.1, "expiry_days": None}
#             ],
#             "market_events": [
#                 {"material_id": "INST_CAL01", "multiplier": 0.0, "duration_days": 7, "event_type": "supply_disruption"}
#             ]
#         }),
#     },
#     {
#         "scenario_id":    "S07_BUDGET_CONSTRAINED",
#         "name":           "Budget Crunch — Multiple Stockouts, Limited Funds",
#         "category":       "Budget Constraint",
#         "difficulty":     "HIGH",
#         "description":    "COVID PCR Mix, Troponin I Antibody, and HbA1c Calibrator are all below safety stock simultaneously. Total procurement cost to fix all three exceeds the remaining budget. Agent must prioritise by stockout penalty.",
#         "expected_action":"Agent should prioritise Troponin I (highest penalty ₹5,000) and COVID PCR (₹3,500), escalate HbA1c separately.",
#         "business_impact":"If wrong priority chosen, cardiac emergency testing fails first — the highest clinical risk.",
#         "config_json": json.dumps({
#             "inventory_overrides": [
#                 {"material_id": "DIAG_CRIT01", "location": "ALL", "quantity_pct_of_safety": 0.35, "expiry_days": None},
#                 {"material_id": "DIAG_CRIT02", "location": "ALL", "quantity_pct_of_safety": 0.30, "expiry_days": None},
#                 {"material_id": "DIAG_CRIT03", "location": "ALL", "quantity_pct_of_safety": 0.40, "expiry_days": None},
#             ],
#             "market_events": [],
#             "budget_override": 45000
#         }),
#     },
#     {
#         "scenario_id":    "S08_COVID_OUTBREAK_WAVE",
#         "name":           "COVID Outbreak Wave — 3 Products Surge Simultaneously",
#         "category":       "Multi-Product Crisis",
#         "difficulty":     "EXTREME",
#         "description":    "A new COVID wave is declared. PCR Mix demand +150%, Nasopharyngeal Swabs +200%, N95 Masks +120% — all for the next 10 days. Three concurrent demand surges with stock sized for normal operations.",
#         "expected_action":"Agent should identify all three at risk and recommend sequential procurement with priority on PCR Mix.",
#         "business_impact":"Entire COVID testing workflow collapses. Government-mandated testing targets missed. Multi-crore penalty exposure.",
#         "config_json": json.dumps({
#             "inventory_overrides": [
#                 {"material_id": "DIAG_CRIT01", "location": "ALL", "quantity_pct_of_safety": 1.0, "expiry_days": None},
#                 {"material_id": "CONS_SWB01",   "location": "ALL", "quantity_pct_of_safety": 0.9, "expiry_days": None},
#                 {"material_id": "CONS_PPE02",   "location": "ALL", "quantity_pct_of_safety": 1.1, "expiry_days": None},
#             ],
#             "market_events": [
#                 {"material_id": "DIAG_CRIT01", "multiplier": 2.5, "duration_days": 10, "event_type": "demand_spike"},
#                 {"material_id": "CONS_SWB01",  "multiplier": 3.0, "duration_days": 10, "event_type": "demand_spike"},
#                 {"material_id": "CONS_PPE02",  "multiplier": 2.2, "duration_days": 10, "event_type": "demand_spike"},
#             ]
#         }),
#     },
#     {
#         "scenario_id":    "S09_OVERSTOCKED",
#         "name":           "Overstocked Low-Priority Items — Hold Position",
#         "category":       "Baseline",
#         "difficulty":     "LOW",
#         "description":    "Filter Tips, Nitrile Gloves, and Vacutainer SST Tubes are massively overstocked at 5x safety stock with 180+ days coverage. No action needed — carrying cost would be higher than risk of stockout.",
#         "expected_action":"Agent should recommend Do Nothing. Highlight overstock as a holding cost concern, not a procurement opportunity.",
#         "business_impact":"Unnecessary procurement increases holding cost. Correct call is to let overstock naturally deplete.",
#         "config_json": json.dumps({
#             "inventory_overrides": [
#                 {"material_id": "CONS_TIP01", "location": "ALL", "quantity_pct_of_safety": 5.2, "expiry_days": None},
#                 {"material_id": "CONS_PPE01", "location": "ALL", "quantity_pct_of_safety": 4.8, "expiry_days": None},
#                 {"material_id": "CONS_VAC02", "location": "ALL", "quantity_pct_of_safety": 5.0, "expiry_days": None},
#             ],
#             "market_events": []
#         }),
#     },
#     {
#         "scenario_id":    "S10_DIWALI_SLOWDOWN",
#         "name":           "Diwali Holiday Slowdown — Deferred Procurement",
#         "category":       "Demand Drop",
#         "difficulty":     "LOW",
#         "description":    "Diwali holiday period. Lab volumes drop 35% across all tests for 5 days. Products that appeared borderline are now safe. Non-urgent procurement should be deferred to avoid overstocking.",
#         "expected_action":"Agent should recognise reduced urgency and defer any borderline procurement decisions.",
#         "business_impact":"Premature procurement during holiday creates unnecessary inventory overhang and holding cost.",
#         "config_json": json.dumps({
#             "inventory_overrides": [
#                 {"material_id": "DIAG_STD02", "location": "ALL", "quantity_pct_of_safety": 1.1, "expiry_days": None},
#                 {"material_id": "DIAG_STD05", "location": "ALL", "quantity_pct_of_safety": 1.0, "expiry_days": None},
#             ],
#             "market_events": [
#                 {"material_id": mid, "multiplier": 0.65, "duration_days": 5, "event_type": "holiday_slowdown"}
#                 for mid in ["DIAG_STD02", "DIAG_STD05", "CONS_VAC01", "CONS_PPE01"]
#             ]
#         }),
#     },
#     {
#         "scenario_id":    "S11_GOVT_MANDATE_SURGE",
#         "name":           "Government Mandate — HepB Screening Campaign",
#         "category":       "Demand Surge",
#         "difficulty":     "MEDIUM",
#         "description":    "State government launches mandatory Hepatitis B screening for all healthcare workers. HepB Surface Antigen Kit demand spikes +90% for 21 days. Previously stable product becomes urgent overnight.",
#         "expected_action":"Agent should detect the demand spike event and recommend emergency procurement with escalation.",
#         "business_impact":"Government mandate compliance failure has regulatory consequences. Testing SLA breached within 3 days if not acted on.",
#         "config_json": json.dumps({
#             "inventory_overrides": [
#                 {"material_id": "DIAG_STD04", "location": "ALL", "quantity_pct_of_safety": 1.0, "expiry_days": None}
#             ],
#             "market_events": [
#                 {"material_id": "DIAG_STD04", "multiplier": 1.9, "duration_days": 21, "event_type": "demand_spike"}
#             ]
#         }),
#     },
#     {
#         "scenario_id":    "S12_LEAD_TIME_SHOCK",
#         "name":           "Supplier Lead Time Doubles — Roche Port Congestion",
#         "category":       "Supply Shock",
#         "difficulty":     "MEDIUM",
#         "description":    "Roche Diagnostics India announces lead times extending from 6 days to 15 days due to Mumbai port congestion. HbA1c Calibrator and 96-Well PCR Plates need earlier reorder triggers to maintain safety stock.",
#         "expected_action":"Agent should bring forward procurement for Roche-supplied items to compensate for longer lead times.",
#         "business_impact":"If reorder point not adjusted, stockout occurs during the extended delivery window — invisible until too late.",
#         "config_json": json.dumps({
#             "inventory_overrides": [
#                 {"material_id": "DIAG_CRIT03", "location": "ALL", "quantity_pct_of_safety": 1.2, "expiry_days": None},
#                 {"material_id": "CONS_PLT01",  "location": "ALL", "quantity_pct_of_safety": 1.1, "expiry_days": None},
#             ],
#             "market_events": [
#                 {"material_id": "DIAG_CRIT03", "multiplier": 1.0, "duration_days": 10, "event_type": "supply_disruption"},
#                 {"material_id": "CONS_PLT01",  "multiplier": 1.0, "duration_days": 10, "event_type": "supply_disruption"},
#             ]
#         }),
#     },
#     {
#         "scenario_id":    "S13_DOUBLE_JEOPARDY",
#         "name":           "Double Jeopardy — Low Stock AND Near Expiry",
#         "category":       "Compound Crisis",
#         "difficulty":     "EXTREME",
#         "description":    "Troponin I Antibody (Cardiac): only 4 days of stock remaining AND the current batch expires in 3 days. Both stockout and expiry risk are simultaneous. Most complex single-product scenario — disposal plus emergency reorder needed.",
#         "expected_action":"Agent should recommend immediate disposal of expiring stock AND escalate emergency procurement simultaneously.",
#         "business_impact":"Cardiac Troponin tests are life-critical in emergency medicine. Any gap in supply directly impacts patient outcomes. Penalty: ₹5,000/unit.",
#         "config_json": json.dumps({
#             "inventory_overrides": [
#                 {"material_id": "DIAG_CRIT02", "location": "ALL", "quantity_pct_of_safety": 0.45, "expiry_days": 3}
#             ],
#             "market_events": []
#         }),
#     },
#     {
#         "scenario_id":    "S14_CASCADING_FAILURE",
#         "name":           "Cascading Failure — 3 Critical Reagents Depleted",
#         "category":       "Multi-Product Crisis",
#         "difficulty":     "EXTREME",
#         "description":    "A large unexpected diagnostic camp was conducted without inventory planning. COVID PCR Mix, Troponin I, and Blood Culture Broth are all below 30% safety stock simultaneously. Budget covers only 2 of 3 full replenishments.",
#         "expected_action":"Agent should prioritise Troponin I first (highest penalty), PCR Mix second. Escalate Blood Culture as separate approval request.",
#         "business_impact":"This scenario tests whether the agent can triage correctly under budget constraints. Wrong prioritisation could mean cardiac labs go dark.",
#         "config_json": json.dumps({
#             "inventory_overrides": [
#                 {"material_id": "DIAG_CRIT01", "location": "ALL", "quantity_pct_of_safety": 0.28, "expiry_days": None},
#                 {"material_id": "DIAG_CRIT02", "location": "ALL", "quantity_pct_of_safety": 0.22, "expiry_days": None},
#                 {"material_id": "DIAG_CRIT04", "location": "ALL", "quantity_pct_of_safety": 0.30, "expiry_days": None},
#             ],
#             "market_events": [],
#             "budget_override": 50000
#         }),
#     },
#     {
#         "scenario_id":    "S15_FORECAST_NOISE",
#         "name":           "False Alarm — Historical Spike Inflating Forecast",
#         "category":       "Forecast Quality",
#         "difficulty":     "MEDIUM",
#         "description":    "Last month's H3N2 flu outbreak created a 3-week demand spike for Urine Dipstick Strips that has now fully passed. The AI's demand model still shows elevated forecast. Current stock is actually sufficient for real projected demand.",
#         "expected_action":"Agent should show moderate caution but NOT over-order. The Monte Carlo scenarios should show high variance, suggesting restraint.",
#         "business_impact":"Over-reacting to a passed event wastes procurement budget and creates overstock of a low-value item.",
#         "config_json": json.dumps({
#             "inventory_overrides": [
#                 {"material_id": "DIAG_STD05", "location": "ALL", "quantity_pct_of_safety": 1.3, "expiry_days": None}
#             ],
#             "market_events": [
#                 {"material_id": "DIAG_STD05", "multiplier": 0.85, "duration_days": 7, "event_type": "demand_spike"}
#             ]
#         }),
#     },
#     {
#         "scenario_id":    "S16_ANALYSER_AT_RISK",
#         "name":           "Analyser at Risk — Biochemistry Control Critical",
#         "category":       "Instrument Crisis",
#         "difficulty":     "HIGH",
#         "description":    "Biochemistry Analyser Control has only 3 days of coverage. If it runs out, the entire biochemistry workflow (liver function, kidney function, glucose, lipids) stops. Highest single-product business impact in the portfolio.",
#         "expected_action":"Agent should ESCALATE with CRITICAL flag — cost exceeds autonomous threshold. Requires immediate human approval.",
#         "business_impact":"Lab biochemistry goes offline. Estimated revenue loss: ₹8,000+ per hour of downtime. 400+ tests per day affected.",
#         "config_json": json.dumps({
#             "inventory_overrides": [
#                 {"material_id": "INST_CAL02", "location": "ALL", "quantity_pct_of_safety": 0.20, "expiry_days": None}
#             ],
#             "market_events": []
#         }),
#     },
#     {
#         "scenario_id":    "S17_TRANSFER_IMPOSSIBLE",
#         "name":           "Transfer Not Possible — All Warehouses Uniformly Low",
#         "category":       "Stock Crisis",
#         "difficulty":     "MEDIUM",
#         "description":    "CBC Diluent Solution is uniformly low across ALL four warehouses at 35% safety stock. There is no surplus anywhere to transfer. Only new procurement from Becton Dickinson India can resolve this.",
#         "expected_action":"Agent should correctly skip TransferAction (no viable source) and recommend direct procurement.",
#         "business_impact":"CBC (Complete Blood Count) is the most ordered lab test in India. Stockout impacts every inpatient admission test.",
#         "config_json": json.dumps({
#             "inventory_overrides": [
#                 {"material_id": "DIAG_STD02", "location": "LOC_MUM", "quantity_pct_of_safety": 0.35, "expiry_days": None},
#                 {"material_id": "DIAG_STD02", "location": "LOC_DEL", "quantity_pct_of_safety": 0.38, "expiry_days": None},
#                 {"material_id": "DIAG_STD02", "location": "LOC_BLR", "quantity_pct_of_safety": 0.32, "expiry_days": None},
#                 {"material_id": "DIAG_STD02", "location": "LOC_HYD", "quantity_pct_of_safety": 0.36, "expiry_days": None},
#             ],
#             "market_events": []
#         }),
#     },
#     {
#         "scenario_id":    "S18_ONE_EXCEPTION",
#         "name":           "Needle in a Haystack — 17 Healthy, 1 Critical",
#         "category":       "Precision Test",
#         "difficulty":     "MEDIUM",
#         "description":    "17 of 18 products are in excellent health. Only N95 Respirator Masks are critically low at 15% safety stock — buried in a sea of green. Agent must find the single critical item without any false alerts on healthy products.",
#         "expected_action":"Agent should pinpoint N95 Masks as the sole action and recommend procurement. No other products should be flagged.",
#         "business_impact":"Missed detection means lab staff have no respiratory protection during pathogen handling. Regulatory and safety violation.",
#         "config_json": json.dumps({
#             "inventory_overrides": [
#                 {"material_id": "CONS_PPE02", "location": "ALL", "quantity_pct_of_safety": 0.15, "expiry_days": None}
#             ],
#             "market_events": []
#         }),
#     },
#     {
#         "scenario_id":    "S19_POST_RECOVERY",
#         "name":           "Post-Crisis Recovery — Day After Emergency Procurement",
#         "category":       "Baseline",
#         "difficulty":     "LOW",
#         "description":    "Yesterday's emergency procurement of COVID PCR Mix has partially arrived. Stock is now back above safety level. Remaining order is in transit. Agent should recognise the improved position and stand down from emergency mode.",
#         "expected_action":"Agent should recommend Do Nothing or minor adjustments. Should NOT re-order the same product that was just stocked.",
#         "business_impact":"Duplicate ordering after recovery wastes ₹50,000+ and creates overstock that will expire.",
#         "config_json": json.dumps({
#             "inventory_overrides": [
#                 {"material_id": "DIAG_CRIT01", "location": "ALL", "quantity_pct_of_safety": 1.4, "expiry_days": None}
#             ],
#             "market_events": []
#         }),
#     },
#     {
#         "scenario_id":    "S20_REGULATORY_MINIMUM",
#         "name":           "Regulatory Compliance Stock — Cannot Go Below Minimum",
#         "category":       "Compliance",
#         "difficulty":     "MEDIUM",
#         "description":    "HepB Surface Antigen Kits and N95 Masks have regulatory minimum stock requirements under NABL accreditation standards. Even though demand is currently low, stock must be maintained above the compliance threshold at all times.",
#         "expected_action":"Agent should maintain minimum stock levels even if normal analysis would suggest holding. Compliance overrides cost optimisation.",
#         "business_impact":"NABL accreditation lapse if minimum stock not maintained. Lab loses certification to operate. Revenue loss: total lab shutdown.",
#         "config_json": json.dumps({
#             "inventory_overrides": [
#                 {"material_id": "DIAG_STD04", "location": "ALL", "quantity_pct_of_safety": 0.85, "expiry_days": None},
#                 {"material_id": "CONS_PPE02", "location": "ALL", "quantity_pct_of_safety": 0.80, "expiry_days": None},
#             ],
#             "market_events": [
#                 {"material_id": "DIAG_STD04", "multiplier": 0.5, "duration_days": 7, "event_type": "holiday_slowdown"},
#                 {"material_id": "CONS_PPE02", "multiplier": 0.5, "duration_days": 7, "event_type": "holiday_slowdown"},
#             ]
#         }),
#     },
# ]


# # ─────────────────────────────────────────────────────────────────────────────
# #  GENERATOR
# # ─────────────────────────────────────────────────────────────────────────────

# def generate_database(db_path: str = "data/inventory.db") -> None:
#     os.makedirs("data", exist_ok=True)
#     conn = sqlite3.connect(db_path)

#     mat_df = pd.DataFrame(MATERIALS)

#     # ── 1. Materials ──────────────────────────────────────────────────────────
#     mat_df[["material_id","name","unit_cost","stockout_penalty",
#             "holding_cost_rate","expiry_penalty"]].to_sql(
#         "materials", conn, if_exists="replace", index=False)

#     # ── 2. Suppliers ──────────────────────────────────────────────────────────
#     pd.DataFrame(SUPPLIERS).to_sql("suppliers", conn, if_exists="replace", index=False)

#     # ── 3. Locations ──────────────────────────────────────────────────────────
#     pd.DataFrame(LOCATIONS).to_sql("locations", conn, if_exists="replace", index=False)

#     # ── 4. Inventory (base state — healthy for all products) ──────────────────
#     inv_rows = []
#     for _, mat in mat_df.iterrows():
#         mid       = mat["material_id"]
#         avg_d     = mat["avg_daily_demand"]
#         vol       = mat["demand_volatility"]
#         safety    = int(avg_d * 2.5 + vol * 1.5)
#         exp_min   = mat["expiry_days_min"]
#         exp_max   = mat["expiry_days_max"]
#         for loc in LOCATIONS:
#             inv_rows.append({
#                 "material_id":  mid,
#                 "location":     loc["location_id"],
#                 "quantity":     np.random.randint(safety, int(safety * 2.8)),
#                 "safety_stock": safety,
#                 "expiry_days":  np.random.randint(exp_min, exp_max),
#             })
#     pd.DataFrame(inv_rows).to_sql("inventory", conn, if_exists="replace", index=False)

#     # ── 5. Demand History (365 days, seasonal + trend) ────────────────────────
#     dem_rows = []
#     start    = datetime.now() - timedelta(days=365)
#     for _, mat in mat_df.iterrows():
#         mid    = mat["material_id"]
#         base   = mat["avg_daily_demand"]
#         vol    = mat["demand_volatility"]
#         # Monsoon peak (July–Sep) for diagnostic products; flat for consumables
#         is_seasonal = mid.startswith("DIAG")
#         for d in range(365):
#             dt     = start + timedelta(days=d)
#             season = (1 + 0.25 * np.sin(2 * np.pi * (d - 150) / 365)
#                       if is_seasonal else 1.0)
#             trend  = 1 + (d / 365) * 0.04   # 4% annual growth
#             noise  = np.random.normal(0, vol * 0.45)
#             demand = max(0, int(base * season * trend + noise))
#             dem_rows.append({
#                 "material_id":  mid,
#                 "date":         dt.date().isoformat(),
#                 "demand_units": demand,
#             })
#     pd.DataFrame(dem_rows).to_sql("demand_history", conn, if_exists="replace", index=False)

#     # ── 6. Market Events (base — none active at startup) ─────────────────────
#     # Scenarios inject their own events dynamically; base table is empty
#     pd.DataFrame(columns=["material_id","start_day","duration_days",
#                            "multiplier","event_type"]).to_sql(
#         "market_events", conn, if_exists="replace", index=False)

#     # ── 7. Scenarios table ────────────────────────────────────────────────────
#     pd.DataFrame(SCENARIOS).to_sql("scenarios", conn, if_exists="replace", index=False)

#     conn.close()

#     print("✅ Database created:", db_path)
#     print(f"   {len(mat_df)} products  |  {len(SUPPLIERS)} suppliers  |  "
#           f"{len(LOCATIONS)} DCs  |  {len(inv_rows)} inventory records  |  "
#           f"{len(dem_rows)} demand rows  |  {len(SCENARIOS)} scenarios")


# if __name__ == "__main__":
#     generate_database()
"""
generate_database.py
====================
Generates inventory.db with:
  - 18 real Indian diagnostics/biotech products
  - 6 real suppliers
  - 4 Indian distribution centres
  - 365 days demand history with seasonality + trend
  - 20 named business scenarios (all in one DB)

Run:  python generate_database.py
"""
import json
import os
import sqlite3
from datetime import datetime, timedelta

import numpy as np
import pandas as pd

np.random.seed(42)

# ─────────────────────────────────────────────────────────────────────────────
#  MASTER DATA
# ─────────────────────────────────────────────────────────────────────────────

MATERIALS = [
    # ── Critical Reagents ────────────────────────────────────────────────────
    {"material_id": "DIAG_CRIT01", "name": "COVID-19 PCR Master Mix",
     "category": "Critical Reagent",
     "unit_cost": 320.0,  "stockout_penalty": 3500.0, "holding_cost_rate": 4.0, "expiry_penalty": 600.0,
     "avg_daily_demand": 55,  "demand_volatility": 20, "expiry_days_min": 14,  "expiry_days_max": 35,
     "primary_supplier": "SUP_ROCHE"},

    {"material_id": "DIAG_CRIT02", "name": "Troponin I Antibody (Cardiac)",
     "category": "Critical Reagent",
     "unit_cost": 480.0,  "stockout_penalty": 5000.0, "holding_cost_rate": 5.0, "expiry_penalty": 800.0,
     "avg_daily_demand": 28,  "demand_volatility": 10, "expiry_days_min": 10,  "expiry_days_max": 21,
     "primary_supplier": "SUP_ABBOTT"},

    {"material_id": "DIAG_CRIT03", "name": "HbA1c Calibrator Solution",
     "category": "Critical Reagent",
     "unit_cost": 210.0,  "stockout_penalty": 2000.0, "holding_cost_rate": 3.0, "expiry_penalty": 450.0,
     "avg_daily_demand": 80,  "demand_volatility": 18, "expiry_days_min": 20,  "expiry_days_max": 45,
     "primary_supplier": "SUP_BIORAD"},

    {"material_id": "DIAG_CRIT04", "name": "Blood Culture Broth (Aerobic)",
     "category": "Critical Reagent",
     "unit_cost": 145.0,  "stockout_penalty": 2500.0, "holding_cost_rate": 3.5, "expiry_penalty": 400.0,
     "avg_daily_demand": 65,  "demand_volatility": 15, "expiry_days_min": 14,  "expiry_days_max": 30,
     "primary_supplier": "SUP_BECTON"},

    # ── Standard Reagents ────────────────────────────────────────────────────
    {"material_id": "DIAG_STD01", "name": "Dengue NS1 ELISA Kit",
     "category": "Standard Reagent",
     "unit_cost": 95.0,   "stockout_penalty": 1200.0, "holding_cost_rate": 1.8, "expiry_penalty": 200.0,
     "avg_daily_demand": 45,  "demand_volatility": 30, "expiry_days_min": 60,  "expiry_days_max": 120,
     "primary_supplier": "SUP_MERIL"},

    {"material_id": "DIAG_STD02", "name": "CBC Diluent Solution",
     "category": "Standard Reagent",
     "unit_cost": 38.0,   "stockout_penalty": 800.0,  "holding_cost_rate": 1.0, "expiry_penalty": 80.0,
     "avg_daily_demand": 180, "demand_volatility": 25, "expiry_days_min": 90,  "expiry_days_max": 180,
     "primary_supplier": "SUP_BECTON"},

    {"material_id": "DIAG_STD03", "name": "Lipid Panel Control Serum",
     "category": "Standard Reagent",
     "unit_cost": 175.0,  "stockout_penalty": 900.0,  "holding_cost_rate": 2.0, "expiry_penalty": 180.0,
     "avg_daily_demand": 35,  "demand_volatility": 8,  "expiry_days_min": 60,  "expiry_days_max": 120,
     "primary_supplier": "SUP_BIORAD"},

    {"material_id": "DIAG_STD04", "name": "Hepatitis B Surface Antigen Kit",
     "category": "Standard Reagent",
     "unit_cost": 82.0,   "stockout_penalty": 1500.0, "holding_cost_rate": 1.2, "expiry_penalty": 150.0,
     "avg_daily_demand": 60,  "demand_volatility": 12, "expiry_days_min": 90,  "expiry_days_max": 180,
     "primary_supplier": "SUP_ABBOTT"},

    {"material_id": "DIAG_STD05", "name": "Urine Dipstick Strips (100-pk)",
     "category": "Standard Reagent",
     "unit_cost": 22.0,   "stockout_penalty": 400.0,  "holding_cost_rate": 0.6, "expiry_penalty": 40.0,
     "avg_daily_demand": 220, "demand_volatility": 35, "expiry_days_min": 180, "expiry_days_max": 365,
     "primary_supplier": "SUP_MERIL"},

    # ── Consumables ──────────────────────────────────────────────────────────
    {"material_id": "CONS_VAC01", "name": "Vacutainer EDTA Tubes (100-pk)",
     "category": "Consumable",
     "unit_cost": 28.0,   "stockout_penalty": 350.0,  "holding_cost_rate": 0.5, "expiry_penalty": 15.0,
     "avg_daily_demand": 320, "demand_volatility": 45, "expiry_days_min": 365, "expiry_days_max": 730,
     "primary_supplier": "SUP_BECTON"},

    {"material_id": "CONS_VAC02", "name": "Vacutainer SST Tubes (100-pk)",
     "category": "Consumable",
     "unit_cost": 32.0,   "stockout_penalty": 350.0,  "holding_cost_rate": 0.5, "expiry_penalty": 15.0,
     "avg_daily_demand": 280, "demand_volatility": 40, "expiry_days_min": 365, "expiry_days_max": 730,
     "primary_supplier": "SUP_BECTON"},

    {"material_id": "CONS_SWB01", "name": "Nasopharyngeal Swab Kit",
     "category": "Consumable",
     "unit_cost": 18.0,   "stockout_penalty": 600.0,  "holding_cost_rate": 0.4, "expiry_penalty": 20.0,
     "avg_daily_demand": 150, "demand_volatility": 80, "expiry_days_min": 180, "expiry_days_max": 365,
     "primary_supplier": "SUP_MERIL"},

    {"material_id": "CONS_PPE01", "name": "Nitrile Exam Gloves (Box/100)",
     "category": "PPE",
     "unit_cost": 14.0,   "stockout_penalty": 200.0,  "holding_cost_rate": 0.3, "expiry_penalty": 5.0,
     "avg_daily_demand": 280, "demand_volatility": 50, "expiry_days_min": 365, "expiry_days_max": 730,
     "primary_supplier": "SUP_MERIL"},

    {"material_id": "CONS_PPE02", "name": "N95 Respirator Masks (Box/20)",
     "category": "PPE",
     "unit_cost": 42.0,   "stockout_penalty": 800.0,  "holding_cost_rate": 0.7, "expiry_penalty": 30.0,
     "avg_daily_demand": 90,  "demand_volatility": 60, "expiry_days_min": 365, "expiry_days_max": 730,
     "primary_supplier": "SUP_MERIL"},

    {"material_id": "CONS_TIP01", "name": "200µL Filter Tips (Rack/96)",
     "category": "Lab Consumable",
     "unit_cost": 16.0,   "stockout_penalty": 180.0,  "holding_cost_rate": 0.3, "expiry_penalty": 5.0,
     "avg_daily_demand": 420, "demand_volatility": 60, "expiry_days_min": 365, "expiry_days_max": 730,
     "primary_supplier": "SUP_BIORAD"},

    {"material_id": "CONS_PLT01", "name": "96-Well PCR Plate",
     "category": "Lab Consumable",
     "unit_cost": 55.0,   "stockout_penalty": 500.0,  "holding_cost_rate": 0.8, "expiry_penalty": 25.0,
     "avg_daily_demand": 120, "demand_volatility": 30, "expiry_days_min": 365, "expiry_days_max": 730,
     "primary_supplier": "SUP_ROCHE"},

    # ── Instrument Reagents ──────────────────────────────────────────────────
    {"material_id": "INST_CAL01", "name": "Haematology Analyser Calibrator",
     "category": "Instrument Reagent",
     "unit_cost": 580.0,  "stockout_penalty": 8000.0, "holding_cost_rate": 6.0, "expiry_penalty": 900.0,
     "avg_daily_demand": 12,  "demand_volatility": 4,  "expiry_days_min": 14,  "expiry_days_max": 30,
     "primary_supplier": "SUP_SIEMENS"},

    {"material_id": "INST_CAL02", "name": "Biochemistry Analyser Control",
     "category": "Instrument Reagent",
     "unit_cost": 420.0,  "stockout_penalty": 6500.0, "holding_cost_rate": 5.0, "expiry_penalty": 700.0,
     "avg_daily_demand": 18,  "demand_volatility": 5,  "expiry_days_min": 14,  "expiry_days_max": 28,
     "primary_supplier": "SUP_SIEMENS"},
]

SUPPLIERS = [
    {"supplier_id": "SUP_ABBOTT",  "name": "Abbott Diagnostics India",      "lead_time_mean": 4.0,  "lead_time_std": 1.2, "reliability": 0.96, "cost_multiplier": 1.00},
    {"supplier_id": "SUP_ROCHE",   "name": "Roche Diagnostics India",       "lead_time_mean": 6.0,  "lead_time_std": 1.8, "reliability": 0.93, "cost_multiplier": 1.10},
    {"supplier_id": "SUP_BECTON",  "name": "Becton Dickinson India",        "lead_time_mean": 5.0,  "lead_time_std": 1.5, "reliability": 0.94, "cost_multiplier": 1.05},
    {"supplier_id": "SUP_BIORAD",  "name": "Bio-Rad Laboratories India",    "lead_time_mean": 8.0,  "lead_time_std": 2.5, "reliability": 0.89, "cost_multiplier": 1.08},
    {"supplier_id": "SUP_MERIL",   "name": "Meril Life Sciences",           "lead_time_mean": 3.0,  "lead_time_std": 1.0, "reliability": 0.91, "cost_multiplier": 0.92},
    {"supplier_id": "SUP_SIEMENS", "name": "Siemens Healthineers India",    "lead_time_mean": 10.0, "lead_time_std": 3.0, "reliability": 0.87, "cost_multiplier": 1.20},
]

LOCATIONS = [
    {"location_id": "LOC_MUM", "name": "Mumbai Central Warehouse",    "capacity": 30000, "region": "West"},
    {"location_id": "LOC_DEL", "name": "Delhi NCR Distribution Hub",  "capacity": 28000, "region": "North"},
    {"location_id": "LOC_BLR", "name": "Bangalore South Depot",       "capacity": 22000, "region": "South"},
    {"location_id": "LOC_HYD", "name": "Hyderabad Regional Centre",   "capacity": 20000, "region": "South"},
]

# ─────────────────────────────────────────────────────────────────────────────
#  20 SCENARIOS
# ─────────────────────────────────────────────────────────────────────────────

SCENARIOS = [
    {
        "scenario_id":    "S01_BASELINE",
        "name":           "The Quiet Day — All Products Healthy",
        "category":       "Baseline",
        "difficulty":     "LOW",
        "description":    "All 18 products are above safety stock with healthy coverage. No market events active. A typical stable operating day for the supply chain team.",
        "expected_action":"Agent should recommend Do Nothing across the portfolio and confirm healthy status.",
        "business_impact":"Low risk. Missing this scenario would mean unnecessary procurement spend.",
        "config_json": json.dumps({
            "inventory_overrides": [],
            "market_events": []
        }),
    },
    {
        "scenario_id":    "S02_CRITICAL_LOW",
        "name":           "Critical Reagent Running Low — COVID PCR Mix",
        "category":       "Stock Crisis",
        "difficulty":     "MEDIUM",
        "description":    "COVID-19 PCR Master Mix is down to 25% of safety stock across all warehouses. At current demand rates, stockout will occur in 6 days. Supplier lead time is 4 days — the window is tight.",
        "expected_action":"Agent should auto-execute emergency procurement from Roche Diagnostics India.",
        "business_impact":"Stockout halts all COVID-19 diagnostic testing. Penalty: ₹3,500 per unit short.",
        "config_json": json.dumps({
            "inventory_overrides": [
                {"material_id": "DIAG_CRIT01", "location": "ALL", "quantity_pct_of_safety": 0.25, "expiry_days": None}
            ],
            "market_events": []
        }),
    },
    {
        "scenario_id":    "S03_EXPIRY_CRISIS",
        "name":           "Expiry Crisis — Blood Culture Broth",
        "category":       "Expiry Risk",
        "difficulty":     "MEDIUM",
        "description":    "Blood Culture Broth (Aerobic) has a batch expiring in 3 days across all distribution centres. Current stock is adequate in quantity but will become worthless. Immediate disposal and reorder needed.",
        "expected_action":"Agent should recommend disposal of expiring stock followed by emergency procurement.",
        "business_impact":"Write-off loss of ₹400/unit on expired stock. Microbiology testing halted after expiry.",
        "config_json": json.dumps({
            "inventory_overrides": [
                {"material_id": "DIAG_CRIT04", "location": "ALL", "quantity_pct_of_safety": 1.8, "expiry_days": 3}
            ],
            "market_events": []
        }),
    },
    {
        "scenario_id":    "S04_WAREHOUSE_IMBALANCE",
        "name":           "Warehouse Imbalance — CBC Diluent",
        "category":       "Transfer Opportunity",
        "difficulty":     "LOW",
        "description":    "Mumbai warehouse has 3x excess CBC Diluent Solution while Delhi NCR Hub is critically low at 20% safety stock. A direct inter-warehouse transfer costs far less than new procurement.",
        "expected_action":"Agent should recommend a warehouse transfer from Mumbai to Delhi — no new procurement needed.",
        "business_impact":"If transfer is missed, Delhi will need emergency procurement at full cost. Transfer saves ~40% of procurement cost.",
        "config_json": json.dumps({
            "inventory_overrides": [
                {"material_id": "DIAG_STD02", "location": "LOC_MUM", "quantity_pct_of_safety": 3.5, "expiry_days": None},
                {"material_id": "DIAG_STD02", "location": "LOC_DEL", "quantity_pct_of_safety": 0.15, "expiry_days": None},
                {"material_id": "DIAG_STD02", "location": "LOC_BLR", "quantity_pct_of_safety": 0.2, "expiry_days": None},
                {"material_id": "DIAG_STD02", "location": "LOC_HYD", "quantity_pct_of_safety": 0.2, "expiry_days": None},
            ],
            "market_events": []
        }),
    },
    {
        "scenario_id":    "S05_DENGUE_SEASON",
        "name":           "Monsoon Season Demand Spike — Dengue NS1 Kit",
        "category":       "Demand Surge",
        "difficulty":     "MEDIUM",
        "description":    "Monsoon season has arrived. Dengue NS1 ELISA Kit demand is spiking +80% above baseline for the next 14 days. Current stock was sized for normal demand and now has only 5-day coverage.",
        "expected_action":"Agent should escalate for emergency procurement given the cost and severity of the spike.",
        "business_impact":"Dengue testing backlog builds rapidly in monsoon. Every missed test is a delayed diagnosis. Penalty: ₹1,200/unit short.",
        "config_json": json.dumps({
            "inventory_overrides": [
                {"material_id": "DIAG_STD01", "location": "ALL", "quantity_pct_of_safety": 0.9, "expiry_days": None}
            ],
            "market_events": [
                {"material_id": "DIAG_STD01", "multiplier": 1.8, "duration_days": 14, "event_type": "demand_spike"}
            ]
        }),
    },
    {
        "scenario_id":    "S06_SOLE_SOURCE_DISRUPTION",
        "name":           "Sole-Source Supplier Disruption — Haematology Calibrator",
        "category":       "Supply Shock",
        "difficulty":     "HIGH",
        "description":    "Siemens Healthineers India — the only supplier for Haematology Analyser Calibrator — has announced a 7-day supply disruption due to port congestion. Current stock gives only 8 days of coverage. Zero buffer once disruption hits.",
        "expected_action":"Agent should escalate CRITICAL procurement immediately to build buffer stock before the disruption window.",
        "business_impact":"Haematology analysers go offline without calibrator. All CBC tests halted. Penalty: ₹8,000/unit short.",
        "config_json": json.dumps({
            "inventory_overrides": [
                {"material_id": "INST_CAL01", "location": "ALL", "quantity_pct_of_safety": 1.1, "expiry_days": None}
            ],
            "market_events": [
                {"material_id": "INST_CAL01", "multiplier": 0.0, "duration_days": 7, "event_type": "supply_disruption"}
            ]
        }),
    },
    {
        "scenario_id":    "S07_BUDGET_CONSTRAINED",
        "name":           "Budget Crunch — Multiple Stockouts, Limited Funds",
        "category":       "Budget Constraint",
        "difficulty":     "HIGH",
        "description":    "COVID PCR Mix, Troponin I Antibody, and HbA1c Calibrator are all below safety stock simultaneously. Total procurement cost to fix all three exceeds the remaining budget. Agent must prioritise by stockout penalty.",
        "expected_action":"Agent should prioritise Troponin I (highest penalty ₹5,000) and COVID PCR (₹3,500), escalate HbA1c separately.",
        "business_impact":"If wrong priority chosen, cardiac emergency testing fails first — the highest clinical risk.",
        "config_json": json.dumps({
            "inventory_overrides": [
                {"material_id": "DIAG_CRIT01", "location": "ALL", "quantity_pct_of_safety": 0.35, "expiry_days": None},
                {"material_id": "DIAG_CRIT02", "location": "ALL", "quantity_pct_of_safety": 0.30, "expiry_days": None},
                {"material_id": "DIAG_CRIT03", "location": "ALL", "quantity_pct_of_safety": 0.40, "expiry_days": None},
            ],
            "market_events": [],
            "budget_override": 45000
        }),
    },
    {
        "scenario_id":    "S08_COVID_OUTBREAK_WAVE",
        "name":           "COVID Outbreak Wave — 3 Products Surge Simultaneously",
        "category":       "Multi-Product Crisis",
        "difficulty":     "EXTREME",
        "description":    "A new COVID wave is declared. PCR Mix demand +150%, Nasopharyngeal Swabs +200%, N95 Masks +120% — all for the next 10 days. Three concurrent demand surges with stock sized for normal operations.",
        "expected_action":"Agent should identify all three at risk and recommend sequential procurement with priority on PCR Mix.",
        "business_impact":"Entire COVID testing workflow collapses. Government-mandated testing targets missed. Multi-crore penalty exposure.",
        "config_json": json.dumps({
            "inventory_overrides": [
                {"material_id": "DIAG_CRIT01", "location": "ALL", "quantity_pct_of_safety": 1.0, "expiry_days": None},
                {"material_id": "CONS_SWB01",   "location": "ALL", "quantity_pct_of_safety": 0.9, "expiry_days": None},
                {"material_id": "CONS_PPE02",   "location": "ALL", "quantity_pct_of_safety": 1.1, "expiry_days": None},
            ],
            "market_events": [
                {"material_id": "DIAG_CRIT01", "multiplier": 2.5, "duration_days": 10, "event_type": "demand_spike"},
                {"material_id": "CONS_SWB01",  "multiplier": 3.0, "duration_days": 10, "event_type": "demand_spike"},
                {"material_id": "CONS_PPE02",  "multiplier": 2.2, "duration_days": 10, "event_type": "demand_spike"},
            ]
        }),
    },
    {
        "scenario_id":    "S09_OVERSTOCKED",
        "name":           "Overstocked Low-Priority Items — Hold Position",
        "category":       "Baseline",
        "difficulty":     "LOW",
        "description":    "Filter Tips, Nitrile Gloves, and Vacutainer SST Tubes are massively overstocked at 5x safety stock with 180+ days coverage. No action needed — carrying cost would be higher than risk of stockout.",
        "expected_action":"Agent should recommend Do Nothing. Highlight overstock as a holding cost concern, not a procurement opportunity.",
        "business_impact":"Unnecessary procurement increases holding cost. Correct call is to let overstock naturally deplete.",
        "config_json": json.dumps({
            "inventory_overrides": [
                {"material_id": "CONS_TIP01", "location": "ALL", "quantity_pct_of_safety": 5.2, "expiry_days": None},
                {"material_id": "CONS_PPE01", "location": "ALL", "quantity_pct_of_safety": 4.8, "expiry_days": None},
                {"material_id": "CONS_VAC02", "location": "ALL", "quantity_pct_of_safety": 5.0, "expiry_days": None},
            ],
            "market_events": []
        }),
    },
    {
        "scenario_id":    "S10_DIWALI_SLOWDOWN",
        "name":           "Diwali Holiday Slowdown — Deferred Procurement",
        "category":       "Demand Drop",
        "difficulty":     "LOW",
        "description":    "Diwali holiday period. Lab volumes drop 35% across all tests for 5 days. Products that appeared borderline are now safe. Non-urgent procurement should be deferred to avoid overstocking.",
        "expected_action":"Agent should recognise reduced urgency and defer any borderline procurement decisions.",
        "business_impact":"Premature procurement during holiday creates unnecessary inventory overhang and holding cost.",
        "config_json": json.dumps({
            "inventory_overrides": [
                {"material_id": "DIAG_STD02", "location": "ALL", "quantity_pct_of_safety": 1.1, "expiry_days": None},
                {"material_id": "DIAG_STD05", "location": "ALL", "quantity_pct_of_safety": 1.0, "expiry_days": None},
            ],
            "market_events": [
                {"material_id": mid, "multiplier": 0.65, "duration_days": 5, "event_type": "holiday_slowdown"}
                for mid in ["DIAG_STD02", "DIAG_STD05", "CONS_VAC01", "CONS_PPE01"]
            ]
        }),
    },
    {
        "scenario_id":    "S11_GOVT_MANDATE_SURGE",
        "name":           "Government Mandate — HepB Screening Campaign",
        "category":       "Demand Surge",
        "difficulty":     "MEDIUM",
        "description":    "State government launches mandatory Hepatitis B screening for all healthcare workers. HepB Surface Antigen Kit demand spikes +90% for 21 days. Previously stable product becomes urgent overnight.",
        "expected_action":"Agent should detect the demand spike event and recommend emergency procurement with escalation.",
        "business_impact":"Government mandate compliance failure has regulatory consequences. Testing SLA breached within 3 days if not acted on.",
        "config_json": json.dumps({
            "inventory_overrides": [
                {"material_id": "DIAG_STD04", "location": "ALL", "quantity_pct_of_safety": 1.0, "expiry_days": None}
            ],
            "market_events": [
                {"material_id": "DIAG_STD04", "multiplier": 1.9, "duration_days": 21, "event_type": "demand_spike"}
            ]
        }),
    },
    {
        "scenario_id":    "S12_LEAD_TIME_SHOCK",
        "name":           "Supplier Lead Time Doubles — Roche Port Congestion",
        "category":       "Supply Shock",
        "difficulty":     "MEDIUM",
        "description":    "Roche Diagnostics India announces lead times extending from 6 days to 15 days due to Mumbai port congestion. HbA1c Calibrator and 96-Well PCR Plates need earlier reorder triggers to maintain safety stock.",
        "expected_action":"Agent should bring forward procurement for Roche-supplied items to compensate for longer lead times.",
        "business_impact":"If reorder point not adjusted, stockout occurs during the extended delivery window — invisible until too late.",
        "config_json": json.dumps({
            "inventory_overrides": [
                {"material_id": "DIAG_CRIT03", "location": "ALL", "quantity_pct_of_safety": 1.2, "expiry_days": None},
                {"material_id": "CONS_PLT01",  "location": "ALL", "quantity_pct_of_safety": 1.1, "expiry_days": None},
            ],
            "market_events": [
                {"material_id": "DIAG_CRIT03", "multiplier": 1.0, "duration_days": 10, "event_type": "supply_disruption"},
                {"material_id": "CONS_PLT01",  "multiplier": 1.0, "duration_days": 10, "event_type": "supply_disruption"},
            ]
        }),
    },
    {
        "scenario_id":    "S13_DOUBLE_JEOPARDY",
        "name":           "Double Jeopardy — Low Stock AND Near Expiry",
        "category":       "Compound Crisis",
        "difficulty":     "EXTREME",
        "description":    "Troponin I Antibody (Cardiac): only 4 days of stock remaining AND the current batch expires in 3 days. Both stockout and expiry risk are simultaneous. Most complex single-product scenario — disposal plus emergency reorder needed.",
        "expected_action":"Agent should recommend immediate disposal of expiring stock AND escalate emergency procurement simultaneously.",
        "business_impact":"Cardiac Troponin tests are life-critical in emergency medicine. Any gap in supply directly impacts patient outcomes. Penalty: ₹5,000/unit.",
        "config_json": json.dumps({
            "inventory_overrides": [
                {"material_id": "DIAG_CRIT02", "location": "ALL", "quantity_pct_of_safety": 0.45, "expiry_days": 3}
            ],
            "market_events": []
        }),
    },
    {
        "scenario_id":    "S14_CASCADING_FAILURE",
        "name":           "Cascading Failure — 3 Critical Reagents Depleted",
        "category":       "Multi-Product Crisis",
        "difficulty":     "EXTREME",
        "description":    "A large unexpected diagnostic camp was conducted without inventory planning. COVID PCR Mix, Troponin I, and Blood Culture Broth are all below 30% safety stock simultaneously. Budget covers only 2 of 3 full replenishments.",
        "expected_action":"Agent should prioritise Troponin I first (highest penalty), PCR Mix second. Escalate Blood Culture as separate approval request.",
        "business_impact":"This scenario tests whether the agent can triage correctly under budget constraints. Wrong prioritisation could mean cardiac labs go dark.",
        "config_json": json.dumps({
            "inventory_overrides": [
                {"material_id": "DIAG_CRIT01", "location": "ALL", "quantity_pct_of_safety": 0.28, "expiry_days": None},
                {"material_id": "DIAG_CRIT02", "location": "ALL", "quantity_pct_of_safety": 0.22, "expiry_days": None},
                {"material_id": "DIAG_CRIT04", "location": "ALL", "quantity_pct_of_safety": 0.30, "expiry_days": None},
            ],
            "market_events": [],
            "budget_override": 50000
        }),
    },
    {
        "scenario_id":    "S15_FORECAST_NOISE",
        "name":           "False Alarm — Historical Spike Inflating Forecast",
        "category":       "Forecast Quality",
        "difficulty":     "MEDIUM",
        "description":    "Last month's H3N2 flu outbreak created a 3-week demand spike for Urine Dipstick Strips that has now fully passed. The AI's demand model still shows elevated forecast. Current stock is actually sufficient for real projected demand.",
        "expected_action":"Agent should show moderate caution but NOT over-order. The Monte Carlo scenarios should show high variance, suggesting restraint.",
        "business_impact":"Over-reacting to a passed event wastes procurement budget and creates overstock of a low-value item.",
        "config_json": json.dumps({
            "inventory_overrides": [
                {"material_id": "DIAG_STD05", "location": "ALL", "quantity_pct_of_safety": 1.3, "expiry_days": None}
            ],
            "market_events": [
                {"material_id": "DIAG_STD05", "multiplier": 0.85, "duration_days": 7, "event_type": "demand_spike"}
            ]
        }),
    },
    {
        "scenario_id":    "S16_ANALYSER_AT_RISK",
        "name":           "Analyser at Risk — Biochemistry Control Critical",
        "category":       "Instrument Crisis",
        "difficulty":     "HIGH",
        "description":    "Biochemistry Analyser Control has only 3 days of coverage. If it runs out, the entire biochemistry workflow (liver function, kidney function, glucose, lipids) stops. Highest single-product business impact in the portfolio.",
        "expected_action":"Agent should ESCALATE with CRITICAL flag — cost exceeds autonomous threshold. Requires immediate human approval.",
        "business_impact":"Lab biochemistry goes offline. Estimated revenue loss: ₹8,000+ per hour of downtime. 400+ tests per day affected.",
        "config_json": json.dumps({
            "inventory_overrides": [
                {"material_id": "INST_CAL02", "location": "ALL", "quantity_pct_of_safety": 0.20, "expiry_days": None}
            ],
            "market_events": []
        }),
    },
    {
        "scenario_id":    "S17_TRANSFER_IMPOSSIBLE",
        "name":           "Transfer Not Possible — All Warehouses Uniformly Low",
        "category":       "Stock Crisis",
        "difficulty":     "MEDIUM",
        "description":    "CBC Diluent Solution is uniformly low across ALL four warehouses at 35% safety stock. There is no surplus anywhere to transfer. Only new procurement from Becton Dickinson India can resolve this.",
        "expected_action":"Agent should correctly skip TransferAction (no viable source) and recommend direct procurement.",
        "business_impact":"CBC (Complete Blood Count) is the most ordered lab test in India. Stockout impacts every inpatient admission test.",
        "config_json": json.dumps({
            "inventory_overrides": [
                {"material_id": "DIAG_STD02", "location": "LOC_MUM", "quantity_pct_of_safety": 0.35, "expiry_days": None},
                {"material_id": "DIAG_STD02", "location": "LOC_DEL", "quantity_pct_of_safety": 0.38, "expiry_days": None},
                {"material_id": "DIAG_STD02", "location": "LOC_BLR", "quantity_pct_of_safety": 0.32, "expiry_days": None},
                {"material_id": "DIAG_STD02", "location": "LOC_HYD", "quantity_pct_of_safety": 0.36, "expiry_days": None},
            ],
            "market_events": []
        }),
    },
    {
        "scenario_id":    "S18_ONE_EXCEPTION",
        "name":           "Needle in a Haystack — 17 Healthy, 1 Critical",
        "category":       "Precision Test",
        "difficulty":     "MEDIUM",
        "description":    "17 of 18 products are in excellent health. Only N95 Respirator Masks are critically low at 15% safety stock — buried in a sea of green. Agent must find the single critical item without any false alerts on healthy products.",
        "expected_action":"Agent should pinpoint N95 Masks as the sole action and recommend procurement. No other products should be flagged.",
        "business_impact":"Missed detection means lab staff have no respiratory protection during pathogen handling. Regulatory and safety violation.",
        "config_json": json.dumps({
            "inventory_overrides": [
                {"material_id": "CONS_PPE02", "location": "ALL", "quantity_pct_of_safety": 0.15, "expiry_days": None}
            ],
            "market_events": []
        }),
    },
    {
        "scenario_id":    "S19_POST_RECOVERY",
        "name":           "Post-Crisis Recovery — Day After Emergency Procurement",
        "category":       "Baseline",
        "difficulty":     "LOW",
        "description":    "Yesterday's emergency procurement of COVID PCR Mix has partially arrived. Stock is now back above safety level. Remaining order is in transit. Agent should recognise the improved position and stand down from emergency mode.",
        "expected_action":"Agent should recommend Do Nothing or minor adjustments. Should NOT re-order the same product that was just stocked.",
        "business_impact":"Duplicate ordering after recovery wastes ₹50,000+ and creates overstock that will expire.",
        "config_json": json.dumps({
            "inventory_overrides": [
                {"material_id": "DIAG_CRIT01", "location": "ALL", "quantity_pct_of_safety": 1.4, "expiry_days": None}
            ],
            "market_events": []
        }),
    },
    {
        "scenario_id":    "S20_REGULATORY_MINIMUM",
        "name":           "Regulatory Compliance Stock — Cannot Go Below Minimum",
        "category":       "Compliance",
        "difficulty":     "MEDIUM",
        "description":    "HepB Surface Antigen Kits and N95 Masks have regulatory minimum stock requirements under NABL accreditation standards. Even though demand is currently low, stock must be maintained above the compliance threshold at all times.",
        "expected_action":"Agent should maintain minimum stock levels even if normal analysis would suggest holding. Compliance overrides cost optimisation.",
        "business_impact":"NABL accreditation lapse if minimum stock not maintained. Lab loses certification to operate. Revenue loss: total lab shutdown.",
        "config_json": json.dumps({
            "inventory_overrides": [
                {"material_id": "DIAG_STD04", "location": "ALL", "quantity_pct_of_safety": 0.85, "expiry_days": None},
                {"material_id": "CONS_PPE02", "location": "ALL", "quantity_pct_of_safety": 0.80, "expiry_days": None},
            ],
            "market_events": [
                {"material_id": "DIAG_STD04", "multiplier": 0.5, "duration_days": 7, "event_type": "holiday_slowdown"},
                {"material_id": "CONS_PPE02", "multiplier": 0.5, "duration_days": 7, "event_type": "holiday_slowdown"},
            ]
        }),
    },
]


# ─────────────────────────────────────────────────────────────────────────────
#  GENERATOR
# ─────────────────────────────────────────────────────────────────────────────

def generate_database(db_path: str = "data/inventory.db") -> None:
    os.makedirs("data", exist_ok=True)
    conn = sqlite3.connect(db_path)

    mat_df = pd.DataFrame(MATERIALS)

    # ── 1. Materials ──────────────────────────────────────────────────────────
    mat_df[["material_id","name","unit_cost","stockout_penalty",
            "holding_cost_rate","expiry_penalty"]].to_sql(
        "materials", conn, if_exists="replace", index=False)

    # ── 2. Suppliers ──────────────────────────────────────────────────────────
    pd.DataFrame(SUPPLIERS).to_sql("suppliers", conn, if_exists="replace", index=False)

    # ── 3. Locations ──────────────────────────────────────────────────────────
    pd.DataFrame(LOCATIONS).to_sql("locations", conn, if_exists="replace", index=False)

    # ── 4. Inventory (base state — healthy for all products) ──────────────────
    inv_rows = []
    for _, mat in mat_df.iterrows():
        mid       = mat["material_id"]
        avg_d     = mat["avg_daily_demand"]
        vol       = mat["demand_volatility"]
        safety    = int(avg_d * 2.5 + vol * 1.5)
        exp_min   = mat["expiry_days_min"]
        exp_max   = mat["expiry_days_max"]
        for loc in LOCATIONS:
            inv_rows.append({
                "material_id":  mid,
                "location":     loc["location_id"],
                "quantity":     np.random.randint(safety, int(safety * 2.8)),
                "safety_stock": safety,
                "expiry_days":  np.random.randint(exp_min, exp_max),
            })
    pd.DataFrame(inv_rows).to_sql("inventory", conn, if_exists="replace", index=False)

    # ── 5. Demand History (365 days, seasonal + trend) ────────────────────────
    dem_rows = []
    start    = datetime.now() - timedelta(days=365)
    for _, mat in mat_df.iterrows():
        mid    = mat["material_id"]
        base   = mat["avg_daily_demand"]
        vol    = mat["demand_volatility"]
        # Monsoon peak (July–Sep) for diagnostic products; flat for consumables
        is_seasonal = mid.startswith("DIAG")
        for d in range(365):
            dt     = start + timedelta(days=d)
            season = (1 + 0.25 * np.sin(2 * np.pi * (d - 150) / 365)
                      if is_seasonal else 1.0)
            trend  = 1 + (d / 365) * 0.04   # 4% annual growth
            noise  = np.random.normal(0, vol * 0.45)
            demand = max(0, int(base * season * trend + noise))
            dem_rows.append({
                "material_id":  mid,
                "date":         dt.date().isoformat(),
                "demand_units": demand,
            })
    pd.DataFrame(dem_rows).to_sql("demand_history", conn, if_exists="replace", index=False)

    # ── 6. Market Events (base — none active at startup) ─────────────────────
    # Scenarios inject their own events dynamically; base table is empty
    pd.DataFrame(columns=["material_id","start_day","duration_days",
                           "multiplier","event_type"]).to_sql(
        "market_events", conn, if_exists="replace", index=False)

    # ── 7. Scenarios table ────────────────────────────────────────────────────
    pd.DataFrame(SCENARIOS).to_sql("scenarios", conn, if_exists="replace", index=False)

    conn.close()

    print("✅ Database created:", db_path)
    print(f"   {len(mat_df)} products  |  {len(SUPPLIERS)} suppliers  |  "
          f"{len(LOCATIONS)} DCs  |  {len(inv_rows)} inventory records  |  "
          f"{len(dem_rows)} demand rows  |  {len(SCENARIOS)} scenarios")


if __name__ == "__main__":
    generate_database()