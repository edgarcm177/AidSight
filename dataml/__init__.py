"""
Aftershock Data/ML layer.

Owns: dataml/data/, dataml/models/, dataml/src/
Backend calls: from dataml.src.simulate_aftershock import simulate_aftershock
"""

from .src.simulate_aftershock import simulate_aftershock

__all__ = ["simulate_aftershock"]
