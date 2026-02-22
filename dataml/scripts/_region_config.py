"""
Shared region and year config for ETL scripts.
Demo: Sahel region, 2024. Locked for UI consistency (epicenters: BFA, MLI, NER, TCD).
"""

# Sahel and neighboring countries (aligned with dataml.src.graph.SAHEL_ISO3 and UI epicenters)
# UI epicenters: BFA, MLI, NER, TCD (DecisionSandbox.tsx)
SAHEL_ISO3 = frozenset(
    {"MLI", "NER", "BFA", "TCD", "CMR", "NGA", "SEN", "MRT", "GMB", "SDN", "SSD", "CAF"}
)

# Demo epicenters used in UI dropdown
DEMO_EPICENTERS = ("BFA", "MLI", "NER", "TCD")

# ETL year range
YEAR_MIN = 2020
YEAR_MAX = 2024

# Demo year shown in UI (e.g. "Mali (2024)")
DEMO_YEAR = 2024

# Baseline year for map/simulation (latest)
BASELINE_YEAR = 2026
