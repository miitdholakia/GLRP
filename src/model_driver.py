"""
Lightweight helpers for driver‑labour reporting.

Currently exposes a single utility:

* extract_driver_route_times(model) → {j: z_j} for last‑visited customer nodes.

All route‑duration logic is built directly into src/model_dukkanci.py, so the
former build_driver_time_model(...) scaffold has been removed.
"""
from pyomo.environ import value

def extract_driver_route_times(driver_model):
    """
    Extract driver route durations for last nodes from the driver model solution.
    Last nodes defined as nodes j where arc (j, k) to depot k is used.
    Returns a dict {j: z_j} for last nodes only.
    """
    last_nodes = []
    for j in driver_model.N:
        for k in driver_model.I:
            if value(driver_model.x[(j, k), k]) > 0.5:
                last_nodes.append(j)
                break
    z_values_last_nodes = {j: value(driver_model.z[j]) for j in last_nodes}
    return z_values_last_nodes

__all__ = ["extract_driver_route_times"]