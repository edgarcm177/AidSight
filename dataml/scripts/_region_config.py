"""
Shared region and year config for ETL scripts.
Lock: Sahel region, 2020–2024 (or 2026 for baseline).
"""

# Sahel and neighboring countries (aligned with dataml.src.graph.SAHEL_ISO3)
SAHEL_ISO3 = frozenset(
    {"MLI", "NER", "BFA", "TCD", "CMR", "NGA", "SEN", "MRT", "GMB", "SDN", "SSD", "CAF"}
)

# ETL year range
YEAR_MIN = 2020
YEAR_MAX = 2024

# Baseline year for map/simulation (latest)
BASELINE_YEAR = 2026
