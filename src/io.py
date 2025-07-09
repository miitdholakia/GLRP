import json
from pathlib import Path
import pandas as pd
from itertools import product
from math import hypot

def _euclid_distance(p1, p2):
    return hypot(p1[0] - p2[0], p1[1] - p2[1])

def load_data(root=".", capacity=100, wage=20):
    root = Path(root) / "data"

    depots = pd.read_csv(root / "depots.csv")          # id,x,y,open_cost
    cust   = pd.read_csv(root / "customers.csv")       # id,x,y,demand,a,u,service
    cust["t_j"] = cust["a"] + cust["service"]
    speeds = pd.read_csv(root / "speeds.csv")          # id_r,v_r

    shared_ids = set(depots.id) & set(cust.id)
    assert not shared_ids, f"Identifier overlap: {sorted(shared_ids)}"

    # Load distances
    dist_file = root / "distances.csv"
    try:
        dist_raw = pd.read_csv(dist_file)
    except FileNotFoundError:
        dist_raw = pd.DataFrame(columns=["i", "j", "km"])

    d = {(row.i, row.j): float(row.km) for row in dist_raw.itertuples(index=False)}

    all_pts = (
        pd.concat([depots[["id", "x", "y"]], cust[["id", "x", "y"]]], ignore_index=True)
        .set_index("id")
    )

    for i, j in product(all_pts.index, repeat=2):
        if i == j:
            continue
        if (i, j) not in d:
            xi, yi = all_pts.loc[i, ["x", "y"]]
            xj, yj = all_pts.loc[j, ["x", "y"]]
            d[(i, j)] = _euclid_distance((xi, yi), (xj, yj))

    dct = {
        "cust": list(cust.id),
        "depots": list(depots.id),
        "speeds": list(speeds.id_r),      # corrected key
        "depots_df": depots,
        "cust_df": cust,
        "speeds_df": speeds,
        "d": d,
        "Q": capacity,
        "wage_h": wage,                   # pass wage here
        "lam": 1, "omega": 1, "alpha": 1, "beta": 1,
        "gamma": 1, "K": 1, "Upsilon": 1, "V": 1,
        "t_j": cust.set_index("id")["t_j"].to_dict(),
    }

    cmem_file = root / "cmem.json"
    if cmem_file.exists():
        with open(cmem_file) as fh:
            cmem = json.load(fh)
        key_map = {
            "lambda": "lam", "alpha": "alpha", "beta": "beta", "gamma": "gamma",
            "K": "K", "Y": "Upsilon", "Upsilon": "Upsilon", "V": "V", "omega": "omega"
        }
        for k_json, k_model in key_map.items():
            if k_json in cmem:
                dct[k_model] = cmem[k_json]

    return dct