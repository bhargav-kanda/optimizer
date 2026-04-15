"""Tests for PartialSolution and InitialSolution."""
import pandas as pd
import pytest

import optimizer as op
from optimizer.core.elements import Variable
from optimizer.core.solutions import PartialSolution, InitialSolution


class _MockProblem:
	def __init__(self, name, max, objective, constraints):
		self.name = name
		self.max = max
		self.objective = objective
		self.constraints = constraints
		self.partial_solution = None
		self.initial_solution = None


class _C:
	def __init__(self, lhs, op, rhs):
		self.lhs, self.comparator, self.rhs = lhs, op, rhs


class TestPartialSolution:
	def test_constructor_with_dict(self):
		ps = PartialSolution({'x': 3.0, 'y': 5.0})
		assert ps.fixed_values == {'x': 3.0, 'y': 5.0}

	def test_default_empty(self):
		ps = PartialSolution()
		assert ps.fixed_values == {}

	def test_from_dataframe(self):
		df = pd.DataFrame({'variable': ['x', 'y'], 'value': [2.5, 7.0]})
		ps = PartialSolution.from_dataframe(df)
		assert ps.fixed_values == {'x': 2.5, 'y': 7.0}

	def test_from_dataframe_custom_cols(self):
		df = pd.DataFrame({'dv': ['a'], 'fixed_at': [1.5]})
		ps = PartialSolution.from_dataframe(df, variable_col='dv', value_col='fixed_at')
		assert ps.fixed_values == {'a': 1.5}

	def test_apply_to_problem_fixes_variables(self):
		"""Fixing x=2 in 'maximize x+y s.t. x+y <= 10, x,y >= 0' should yield y=8."""
		x = Variable('x', min=0, max=100)
		y = Variable('y', min=0, max=100)
		problem = _MockProblem('test', True, x + y, [_C(x + y, '<=', 10)])
		ps = PartialSolution({'x': 2.0})
		ps.apply_to_problem(problem)

		result = op.PulpSolver(msg=False).solve(problem)
		assert result.status == op.SolverStatus.OPTIMAL
		assert abs(result.variables['x'] - 2.0) < 1e-6
		assert abs(result.variables['y'] - 8.0) < 1e-6


class TestInitialSolution:
	def test_constructor(self):
		init = InitialSolution({'x': 5.0})
		assert init.values == {'x': 5.0}
		assert init.cost_to_change == 0

	def test_from_dataframe(self):
		df = pd.DataFrame({'variable': ['x'], 'value': [3.0]})
		init = InitialSolution.from_dataframe(df)
		assert init.values == {'x': 3.0}

	def test_pulp_warm_start_accepts(self):
		"""Verify that PulpSolver accepts an InitialSolution without crashing.

		CBC doesn't always act on warm starts for LP, but we verify the path works.
		"""
		x = Variable('x', min=0, max=10, integer=True)
		problem = _MockProblem('warm_test', True, x, [_C(x, '<=', 7)])
		problem.initial_solution = InitialSolution({'x': 5})
		result = op.PulpSolver(msg=False).solve(problem)
		assert result.status == op.SolverStatus.OPTIMAL
		assert abs(result.variables['x'] - 7.0) < 1e-6
