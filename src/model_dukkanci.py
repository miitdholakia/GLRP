from pyomo.environ import (
    ConcreteModel, Set, Param, Var, Binary, NonNegativeReals,
    Objective, Constraint, minimize
)


def build_dukkanci_model(data, name="GLRP"):
    m = ConcreteModel(name=name)

    # Sets
    m.I = Set(initialize=data["depots"], ordered=True)        # depots
    m.N = Set(initialize=data["cust"],   ordered=True)        # customers
    m.R = Set(initialize=data["speeds"], ordered=True)        # speed levels
    m.V = Set(initialize=lambda mdl: list(mdl.I) + list(mdl.N), ordered=True)        # All vertices (depots ∪ customers)

    m.A = Set(
        initialize={(i, j) for i in m.I | m.N for j in m.I | m.N if i != j},
        dimen=2
    )

    # Parameters
    m.d = Param(m.A, initialize=lambda _, i, j: data["d"][(i, j)],
                within=NonNegativeReals)

    dep_df  = data["depots_df"].set_index("id")
    cust_df = data["cust_df"].set_index("id")
    spd_df  = data["speeds_df"].set_index("id_r")

    # Tight Big‑M for time constraints
    big_m = max(data["d"].values()) / min(spd_df["v_r"]) + cust_df["service"].max()

    m.c = Param(m.I, initialize=dep_df["open_cost"].to_dict())
    m.q = Param(m.N, initialize=cust_df["demand"].to_dict())
    m.a = Param(m.N, initialize=cust_df["a"].to_dict())
    m.u = Param(m.N, initialize=cust_df["u"].to_dict())
    m.s = Param(
        m.V,
        initialize=lambda mdl, v: cust_df["service"].get(v, 0.0),
        within=NonNegativeReals
    ) # Service time: look up customer value, default to 0 for depots
    
    # Upper time window for every node (0 for depots, given value at customers)
    planning_horizon = 1e6
    m.u_full = Param(
        m.V,
        initialize=lambda mdl, v: cust_df["u"].get(v, planning_horizon),
        within=NonNegativeReals
    )
    
    # Vehicle capacity (set to 100 to cover aggregate demand)
    m.Q        = Param(initialize=100)
    m.omega    = Param(initialize=data["omega"])
    m.lam      = Param(initialize=data["lam"])
    m.alpha    = Param(initialize=data["alpha"])
    m.beta     = Param(initialize=data["beta"])
    m.gamma    = Param(initialize=data["gamma"])
    m.Kcoef    = Param(initialize=data["K"])
    m.Upsilon  = Param(initialize=data["Upsilon"])
    m.Vcoef    = Param(initialize=data["V"])
    m.v = Param(m.R, initialize=spd_df["v_r"].to_dict())

    # Driver wage parameter
    m.wage_h = Param(initialize=data["wage_h"], mutable=True)

    # Variables
    m.y = Var(m.I, within=Binary)
    m.x = Var(m.A, m.I, within=Binary)
    m.w = Var(m.A, m.I, m.R, within=Binary)
    m.f = Var(m.A, within=NonNegativeReals)
    m.t = Var(m.V, within=NonNegativeReals)
    m.z = Var(m.N, within=NonNegativeReals)


    # ----------------------  CORE CONSTRAINTS  ----------------------

    # (1) visit each customer exactly once
    def one_visit(mdl, j):
        return sum(mdl.x[(i, j), k]
                   for i in mdl.I | mdl.N for k in mdl.I if i != j) == 1
    m.visit_once = Constraint(m.N, rule=one_visit)

    # (2) depot departure / return – one route per open depot
    def depot_depart(mdl, k):
        return sum(mdl.x[(k, j), k] for j in mdl.N) >= mdl.y[k]
    m.depot_depart = Constraint(m.I, rule=depot_depart)

    def depot_return(mdl, k):
        return sum(mdl.x[(j, k), k] for j in mdl.N) >= mdl.y[k]
    m.depot_return = Constraint(m.I, rule=depot_return)

    # (2b) any arc tagged with depot k implies that depot is open
    def arc_implies_open(mdl, i, j, k):
        return mdl.x[(i, j), k] <= mdl.y[k]
    m.arc_open = Constraint(m.A, m.I, rule=arc_implies_open)

    # (3) flow conservation and capacity on every arc
    def flow_balance(mdl, j):
        in_flow  = sum(mdl.f[(i, j)] for i in mdl.I | mdl.N if i != j)
        out_flow = sum(mdl.f[(j, i)] for i in mdl.I | mdl.N if i != j)
        return in_flow - out_flow == mdl.q[j]
    m.flow_bal = Constraint(m.N, rule=flow_balance)

    def cap_arc(mdl, i, j):
        return mdl.f[(i, j)] <= mdl.Q * sum(mdl.x[(i, j), k] for k in mdl.I)
    m.flow_cap = Constraint(m.A, rule=cap_arc)

    # (3b) total supply from depots must exactly cover total customer demand
    def global_supply(mdl):
        return sum(mdl.f[(k, j)] for k in mdl.I for j in mdl.N) == \
               sum(mdl.q[j] for j in mdl.N)
    m.global_supply = Constraint(rule=global_supply)

    # (4) speed choice must match arc selection
    def speed_link(mdl, i, j, k):
        return sum(mdl.w[(i, j), k, r] for r in mdl.R) == mdl.x[(i, j), k]
    m.speed_choice = Constraint(m.A, m.I, rule=speed_link)

    # (5) customer time windows
    m.tw_low  = Constraint(m.N, rule=lambda mdl, j: mdl.t[j] >= mdl.a[j])
    m.tw_high = Constraint(m.N, rule=lambda mdl, j: mdl.t[j] <= mdl.u[j])

    # (6) time propagation along used arcs
    def time_prop(mdl, i, j, k):
        if j in mdl.I:          # skip propagation when the destination is a depot
            return Constraint.Skip
        travel = sum(mdl.d[(i, j)] / mdl.v[r] * mdl.w[(i, j), k, r]
                     for r in mdl.R)
        return mdl.t[j] >= mdl.t[i] + mdl.s[i] + travel \
               - (mdl.u_full[j] + mdl.s[j]) * (1 - mdl.x[(i, j), k])
    m.time_prop = Constraint(m.A, m.I, rule=time_prop)

    # --- route duration bound for last visited customer j
    def link_z(mdl, j):
        travel_back = sum(
            mdl.d[(j, k)] / mdl.v[r] * mdl.w[(j, k), k, r]
            for k in mdl.I for r in mdl.R
        )
        last_arc = sum(mdl.x[(j, k), k] for k in mdl.I)
        return mdl.z[j] >= mdl.t[j] + mdl.s[j] + travel_back \
               - (mdl.u_full[j] + mdl.s[j]) * (1 - last_arc)
    m.link_z = Constraint(m.N, rule=link_z)

    # Objective function components
    empty_vehicle = m.lam * m.alpha * m.gamma * \
        sum(m.d[i, j] * m.omega * m.x[(i, j), k]
            for (i, j) in m.A for k in m.I)

    carried_load  = m.lam * m.alpha * m.gamma * \
        sum(m.d[i, j] * m.f[(i, j)] for (i, j) in m.A)

    speed_module  = m.lam * m.beta * m.gamma * \
        sum(m.d[i, j] * m.v[r] ** 2 * m.w[(i, j), k, r]
            for (i, j) in m.A for k in m.I for r in m.R)

    engine_module = m.lam * m.Kcoef * m.Upsilon * m.Vcoef * \
        sum(m.d[i, j] / m.v[r] * m.w[(i, j), k, r]
            for (i, j) in m.A for k in m.I for r in m.R)

    # additive driver labour cost
    driver_cost = m.wage_h * sum(m.z[j] for j in m.N)

    depot_cost = sum(m.c[k] * m.y[k] for k in m.I)

    m.obj = Objective(
        expr=depot_cost + empty_vehicle + carried_load
             + speed_module + engine_module + driver_cost,
        sense=minimize
    )

    return m