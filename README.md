# optimizer

A Python framework for symbolic optimization modeling, built on SymPy with pandas-native data binding, constraint conflict detection, and partial/initial solution support.

## Why this exists

Existing Python optimization frameworks ([Pyomo](https://www.pyomo.org/), [PuLP](https://coin-or.github.io/pulp/), [Optlang](https://optlang.readthedocs.io/)) cover the core modeling need but leave real pain points unaddressed:

- **Infeasibility diagnosis is hard.** When a Pyomo model returns `INFEASIBLE`, you get zero help narrowing down the cause.
- **Partial solutions are ad-hoc.** Fixing a subset of variables means manually adding equality constraints and hoping nothing breaks.
- **Pandas integration is bolted on.** Most frameworks treat DataFrames as optional data sources rather than first-class citizens.

`optimizer` targets these gaps. It's smaller than Pyomo, less mature, but more opinionated about the workflow.

## Features

- **Multiple solver backends** via a clean `SolverBase` protocol (PuLP/CBC for LP+MIP, SciPy/HiGHS for LP).
- **Constraint conflict detection** — two modes:
  - `lite`: fast heuristic checks (variable bounds, single-constraint feasibility, contradictory equalities). No solver needed.
  - `pro`: runs a feasibility LP to catch multi-constraint infeasibilities that heuristics miss.
- **Partial solutions**: fix a subset of variables to known values via `PartialSolution.apply_to_problem()`.
- **Initial solutions**: warm-start MIP solvers via `InitialSolution` (passed to CBC's warmStart).
- **Constraint pruning**: drop constraints rendered redundant by equalities or variable fixings.
- **Pandas-native data binding**: ranges, values, and variables derived directly from DataFrames.

## Installation

```bash
pip install .[all]   # includes both PuLP and SciPy backends
```

Or for just one backend:

```bash
pip install .[pulp]   # PuLP + CBC (LP/MIP)
pip install .[scipy]  # SciPy + HiGHS (LP only)
```

## Quick start — Diet problem

```python
from optimizer.core.elements import Variable
from optimizer.solvers import PulpSolver, SolverStatus

# Variables
bread = Variable('bread', min=0, max=10)
cheese = Variable('cheese', min=0, max=5)

# Objective and constraints (use sympy arithmetic)
class Problem:
    name = 'diet'
    max = False
    objective = 1.0 * bread + 3.0 * cheese
    # Each constraint has .lhs, .comparator, .rhs
    class C:
        def __init__(self, lhs, op, rhs):
            self.lhs, self.comparator, self.rhs = lhs, op, rhs
    constraints = [
        C(9 * bread + 25 * cheese, '>=', 50),   # protein
        C(50 * bread + cheese,     '>=', 200),  # carbs
    ]

result = PulpSolver(msg=False).solve(Problem)
print(result.status)           # SolverStatus.OPTIMAL
print(result.objective_value)  # total cost
print(result.variables)        # {'bread': ..., 'cheese': ...}
```

For a runnable version with the full formulation, see [`examples/diet_problem/diet.py`](examples/diet_problem/diet.py).

## Architecture

```
OpFormulation  ──►  OpProblem  ──►  SolverBase.solve()  ──►  SolverResult
  (rules,            (concrete       (PulpSolver,               (status,
   ranges,            constraints,    ScipySolver,                objective,
   variables)         objective)      ...)                        variables)
```

Key classes (in `optimizer/core/`):

| Class | Purpose |
|-------|---------|
| `Variable` | Sympy-based symbolic variable with bounds and integer flag |
| `Rule` | Symbolic constraint template (with indices) |
| `Constraint` | Concrete instantiation of a Rule for specific index values |
| `OpFormulation` | Problem definition (ranges, variables, rules, objective) |
| `OpProblem` | Concrete problem with `solve()`, `check_conflicts()`, `prune_constraints()` |
| `PartialSolution` | Fix a subset of variables via injected equality constraints |
| `InitialSolution` | Warm-start values for MIP solvers |

Solvers (in `optimizer/solvers/`):

| Backend | Supports | Notes |
|---------|----------|-------|
| `PulpSolver` | LP, MIP, binary | Default. Uses CBC. Handles warm-start. |
| `ScipySolver` | LP only | HiGHS method. Rejects integer variables. |

## Conflict detection

```python
from optimizer.core.exceptions import ConflictError

try:
    problem.check_conflicts(mode='lite')   # or mode='pro'
except ConflictError as e:
    for c in e.conflicts:
        print(c.severity.value, '-', c.description)
```

`lite` is fast (pure arithmetic). `pro` runs a feasibility LP and catches conflicts that only manifest across multiple constraints.

## Partial solutions

```python
from optimizer.core.solutions import PartialSolution

# Fix movie_03 to air on day 5, slot 1
ps = PartialSolution({'air_movie_03_5_1': 1})
ps.apply_to_problem(problem)

result = PulpSolver().solve(problem)
```

Or from a DataFrame:

```python
ps = PartialSolution.from_dataframe(df, variable_col='dv', value_col='fixed_to')
```

## Examples

- **`examples/diet_problem/diet.py`** — classical diet problem, 4 foods × 4 nutrients, LP.
- **`examples/sm_scheduling/sm_demo.py`** — Star Movies TV scheduling with synthetic data, 10 movies × 7 days × 3 slots, MIP.

Run an example (after `pip install -e .[all]`):

```bash
python examples/diet_problem/diet.py
python examples/sm_scheduling/sm_demo.py
```

## Development

```bash
pip install -e .[dev]
pytest
```

The test suite uses real PuLP and SciPy solvers — no mocks. See `tests/` for 70+ tests covering linearization, solvers, conflict detection, pruning, solutions, and end-to-end integration.

## Status

Version 0.2.0. The core pipeline (define → solve → inspect) is stable and tested. The high-level symbolic API (OpFormulation with indexed arrays and OpSum) has known rough edges and is used most directly through the raw Variable + sympy arithmetic path shown above.

## License

MIT
