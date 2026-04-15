"""Diet problem example — classical optimization tutorial.

Given a set of foods with costs and nutrient amounts, find the cheapest
combination that satisfies nutritional requirements.

This example uses the direct Variable + Constraint API. For a higher-level
formulation with data-driven ranges, see the Star Movies scheduling example.
"""
import pandas as pd

from optimizer.core.elements import Variable
from optimizer.solvers import PulpSolver, SolverStatus


# Data: foods with per-unit cost and buy limits
FOODS = pd.DataFrame({
	'food':   ['bread', 'cheese', 'milk',  'potato'],
	'cost':   [    1.0,     3.0,    2.0,     0.8],
	'f_min':  [    0.0,     0.0,    0.0,     0.0],
	'f_max':  [   10.0,     5.0,    8.0,    20.0],
})

# Data: nutrients with daily min/max requirements
NUTRIENTS = pd.DataFrame({
	'nutrient': ['protein', 'carbs', 'fat',  'fiber'],
	'n_min':    [     50.0,   200.0,  30.0,    15.0],
	'n_max':    [    200.0,   500.0, 100.0,   100.0],
})

# Data: amount of each nutrient in each unit of each food
AMT = pd.DataFrame({
	'food':    ['bread', 'cheese', 'milk', 'potato'] * 4,
	'nutrient': (['protein'] * 4 + ['carbs'] * 4
	             + ['fat'] * 4 + ['fiber'] * 4),
	'amount':  [
		# protein
		9.0,  25.0,  8.0,  2.0,
		# carbs
		50.0, 1.0,  12.0, 17.0,
		# fat
		3.0,  30.0, 9.0,  0.1,
		# fiber
		3.0,  0.0,  0.0,  2.2,
	],
})


class _Problem:
	"""Minimal adapter object the solver expects."""
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


def build_diet_problem():
	# Create one Variable per food with its bounds
	buy = {}
	for _, row in FOODS.iterrows():
		buy[row['food']] = Variable(
			f"buy_{row['food']}",
			min=row['f_min'],
			max=row['f_max'],
		)

	# Objective: minimize total cost = sum(cost[f] * buy[f])
	objective = sum(row['cost'] * buy[row['food']] for _, row in FOODS.iterrows())

	# Constraints: each nutrient's total must fall within [n_min, n_max]
	constraints = []
	for _, n_row in NUTRIENTS.iterrows():
		nutrient = n_row['nutrient']
		total = sum(
			AMT[(AMT['food'] == f_row['food']) & (AMT['nutrient'] == nutrient)]['amount'].iloc[0]
			* buy[f_row['food']]
			for _, f_row in FOODS.iterrows()
		)
		constraints.append(_Constraint(total, '>=', n_row['n_min']))
		constraints.append(_Constraint(total, '<=', n_row['n_max']))

	return _Problem('diet', max=False, objective=objective, constraints=constraints), buy


def solve_and_print():
	problem, buy = build_diet_problem()
	result = PulpSolver(msg=False).solve(problem)
	print(f"Status: {result.status.value}")
	if result.status == SolverStatus.OPTIMAL:
		print(f"Total cost: ${result.objective_value:.2f}")
		print("Diet plan:")
		for food, var in buy.items():
			amount = result.variables[var.name]
			if amount > 1e-6:
				print(f"  {food}: {amount:.2f} units")
	return result


if __name__ == '__main__':
	solve_and_print()
