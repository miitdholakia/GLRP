"""
generate_results.py – runs GLRP, writes IIS if infeasible
"""

import sys
from pyomo.environ import SolverFactory, value
from src.io import load_data
from src.model_dukkanci import build_dukkanci_model


def solve_model(model, tee=False):
    solver = SolverFactory("gurobi")
    return solver.solve(model, tee=tee)


def main():
    data = load_data()
    print(
        f"Loaded data: Depots={len(data['depots'])}, "
        f"Customers={len(data['cust'])}, Speeds={len(data['speeds'])}"
    )

    model = build_dukkanci_model(data)
    result = solve_model(model, tee=True)

    term_cond = str(result.solver.termination_condition).lower()
    if term_cond == "infeasible":
        print("Model infeasible. Writing IIS files …")
        model.write("infeasible.lp", io_options={"symbolic_solver_labels": True})
        solver = SolverFactory("gurobi")
        solver.options["InfUnbdInfo"] = 1          # turn on feasibility analysis
        solver.options["IISMethod"]   = 1          # deterministic IIS search
        solver.options["ResultFile"]  = "infeasible.ilp"
        solver.solve(model, tee=True, load_solutions=False)
        print("\nIIS written to `infeasible.ilp`. "
              "Open that file (and `infeasible.lp`) in VS Code to see the "
              "constraints Gurobi marked as mutually conflicting.")
        sys.exit(0)
    elif term_cond != "optimal":
        print(f"Model status: {result.solver.termination_condition}")
        sys.exit(0)

    obj_val = value(model.obj)
    total_labour = value(model.wage_h) * sum(value(model.z[j]) for j in model.N)

    print("\n--- GLRP MODEL RESULTS ---")
    print(f"Objective value (incl. driver cost): {obj_val:.4f}")
    print(f"Total driver labour cost (Σ wage·z_j): {total_labour:.4f}")

    open_depots = [k for k in model.I if value(model.y[k]) > 0.5]
    print(f"Open depots: {open_depots}")


if __name__ == "__main__":
    main()