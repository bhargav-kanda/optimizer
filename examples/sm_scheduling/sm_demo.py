"""Star Movies scheduling example with synthetic data.

A simplified version of the original scheduling problem:
  - 10 movies, 7 days, 3 time slots
  - Each (date, slot) must air exactly one movie
  - No movie can air twice in the same day
  - Maximize total TVR (TV ratings)

The full version with FOX 1+1, MOTM/MOTW, continuity rules etc. requires
real input data (see main.py) — this demo uses synthetic data and shows
the modeling pattern.
"""
import random

import pandas as pd

from optimizer.core.elements import Variable
from optimizer.solvers import PulpSolver, SolverStatus


# Synthetic inventory
N_MOVIES = 10
N_DAYS = 7
N_SLOTS = 3

MOVIES = [f"movie_{i:02d}" for i in range(N_MOVIES)]
DAYS = list(range(N_DAYS))
SLOTS = list(range(N_SLOTS))


def _make_tvr_table(seed: int = 42) -> pd.DataFrame:
	"""Create synthetic TVR (rating) for each (movie, day, slot) combination."""
	rng = random.Random(seed)
	rows = []
	for m in MOVIES:
		for d in DAYS:
			for s in SLOTS:
				rows.append({
					'movie': m,
					'day': d,
					'slot': s,
					'tvr': round(rng.uniform(0.1, 5.0), 2),
				})
	return pd.DataFrame(rows)


class _Problem:
	def __init__(self, name, max, objective, constraints):
		self.name = name
		self.max = max
		self.objective = objective
		self.constraints = constraints
		self.partial_solution = None
		self.initial_solution = None


class _Constraint:
	def __init__(self, lhs, comparator, rhs):
		self.lhs, self.comparator, self.rhs = lhs, comparator, rhs


def build_sm_problem():
	tvr = _make_tvr_table()
	tvr_lookup = {(r['movie'], r['day'], r['slot']): r['tvr']
	              for _, r in tvr.iterrows()}

	# Binary variable: airings[movie, day, slot] ∈ {0, 1}
	airings = {}
	for m in MOVIES:
		for d in DAYS:
			for s in SLOTS:
				airings[(m, d, s)] = Variable(
					f"air_{m}_{d}_{s}", min=0, max=1, integer=True,
				)

	# Objective: maximize total TVR = sum(tvr[m,d,s] * airings[m,d,s])
	objective = sum(
		tvr_lookup[key] * airings[key] for key in airings
	)

	constraints = []

	# Constraint 1: each (day, slot) has exactly one movie
	for d in DAYS:
		for s in SLOTS:
			expr = sum(airings[(m, d, s)] for m in MOVIES)
			constraints.append(_Constraint(expr, '==', 1))

	# Constraint 2: each movie airs at most once per day
	for m in MOVIES:
		for d in DAYS:
			expr = sum(airings[(m, d, s)] for s in SLOTS)
			constraints.append(_Constraint(expr, '<=', 1))

	# Constraint 3: each movie has a weekly airing cap (3 total)
	for m in MOVIES:
		expr = sum(airings[(m, d, s)] for d in DAYS for s in SLOTS)
		constraints.append(_Constraint(expr, '<=', 3))

	problem = _Problem('sm_demo', max=True, objective=objective, constraints=constraints)
	return problem, airings


def print_schedule(airings, result):
	"""Pretty-print the optimal schedule."""
	schedule = {}
	for key, var in airings.items():
		val = result.variables.get(var.name, 0)
		if val > 0.5:
			movie, day, slot = key
			schedule.setdefault((day, slot), movie)

	print(f"\nOptimal schedule (total TVR: {result.objective_value:.2f}):")
	print(f"{'Day':<6}" + "".join([f"Slot {s:<4}" for s in SLOTS]))
	for d in DAYS:
		line = f"{d:<6}"
		for s in SLOTS:
			line += f"{schedule.get((d, s), '-'):<9}"
		print(line)


if __name__ == '__main__':
	problem, airings = build_sm_problem()
	print(f"Solving Star Movies scheduling with {N_MOVIES} movies, "
	      f"{N_DAYS} days, {N_SLOTS} slots...")
	result = PulpSolver(msg=False, time_limit=60).solve(problem)
	print(f"Status: {result.status.value}")
	if result.status == SolverStatus.OPTIMAL:
		print_schedule(airings, result)
