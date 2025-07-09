
# GLRP-DC — Green Location-Routing with Driver Cost  
**Strategic freight-network optimisation that balances depot siting, routing, speed choice, fuel burn, emissions and driver wages.**

## Table of contents
- [Project overview](#project-overview)  
- [Key features](#key-features)  
- [Quick start](#quick-start)  
- [Repository layout](#repository-layout)  
- [Reproducing the paper’s results](#reproducing-the-papers-results)  
- [Contributing](#contributing)  
- [License](#license)  
- [Citation](#citation)  
- [Contact](#contact)  

## Project overview
This repository accompanies the seminar paper **“Integrating Driver Labour Costs into the Green Location-Routing Problem”** (OvGU, 2025).  
It provides:

* a **mixed-integer linear model (GLRP-DC)** encoded in Pyomo that extends the classical GLRP with a time-based wage term;  
* **exact and heuristic solvers** (two-phase decomposition + iterated local search) capable of handling instances up to 100 customers on a laptop;  
* **synthetic data generators** and **CSV instances** used in the experiments;  
* scripts to run the model, collect solver logs and generate plots/tables for the paper.

## Key features
| Feature | Description |
|---------|-------------|
| **Driver-time cost** | Adds a linear wage component so slower eco-speeds trade fuel for duty hours. |
| **CMEM integration** | Uses the four linear modules of the Comprehensive Modal Emissions Model to estimate fuel/CO₂. |
| **Two-phase exact solver** | Solves medium instances (≤ 50 customers) to optimality within seconds. |
| **Iterated Local Search** | Scales to larger instances; achieves < 1 % gap for 100 customers in < 2 min. |
| **Reproducible experiments** | `generate_results.py` rebuilds all paper tables and logs in one command. |

## Quick start

```bash
# 1. Clone and create a fresh environment
git clone https://github.com/<your-user>/glrp-dc.git
cd glrp-dc
python -m venv venv && source venv/bin/activate

# 2. Install dependencies
pip install -r requirements.txt          # Pyomo ≥6.7, pandas, numpy, etc.

# 3. Ensure a MIP solver is available
export GUROBI_HOME=/path/to/gurobi
python -m pip install gurobipy           # academic license recommended

# 4. Reproduce small & medium experiments
PYTHONPATH=. python src/generate_results.py
```

## Repository layout
```
├── data/                 # CSV instances
├── src/
│   ├── model_dukkanci.py
│   ├── model_driver.py
│   ├── io.py
│   └── generate_results.py
├── docs/                 # paper, figures, logs
└── requirements.txt
```

## Reproducing the paper’s results
Two instances: small (`2×5`) and medium (`4×50`) can be reproduced with

```bash
PYTHONPATH=. python src/generate_results.py --instance small
PYTHONPATH=. python src/generate_results.py --instance medium
```

## Contributing
Fork, create feature branch, add tests, run `flake8`/`black`, open PR.  See `CONTRIBUTING.md`.

## License
Released under the **MIT License** (`LICENSE`).

## Citation
```
@misc{dholakia2025glrpdc,
  author    = {Miit Dholakia},
  title     = {Integrating Driver Labour Costs into the Green Location-Routing Problem},
  year      = {2025},
  institution = {Otto-von-Guericke University Magdeburg},
  note      = {M.Sc. Seminar Paper},
  url       = {https://github.com/<your-user>/glrp-dc}
}
```

## Contact
Maintainer: **Miit Dholakia** · miit.dholakia@st.ovgu.de
