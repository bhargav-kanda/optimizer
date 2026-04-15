"""Integration tests for solver backends using real PuLP and SciPy."""
import pytest
from sympy import Symbol

from optimizer.solvers import PulpSolver, ScipySolver, SolverStatus
from optimizer.core.elements import Variable


class _MiniProblem:
	"""Minimal test problem with just what solvers need. Avoids the full OpProblem wiring."""

	def __init__(self, name, max, objective, constraints):
		self.name = name
		self.max = max
		self.objective = objective
		self.constraints = constraints


class _MiniConstraint:
	def __init__(self, lhs, comparator, rhs):
		self.lhs = lhs
		self.comparator = comparator
		self.rhs = rhs


@pytest.fixture
def simple_max_lp():
	"""Maximize 2x + 3y subject to x + y <= 4, x >= 0, y >= 0.

	Optimum: y=4, x=0, objective = 12.
	"""
	x = Variable('x', min=0)
	y = Variable('y', min=0)
	objective = 2 * x + 3 * y
	constraints = [_MiniConstraint(x + y, '<=', 4)]
	return _MiniProblem('simple_max', True, objective, constraints), x, y


@pytest.fixture
def simple_min_lp():
	"""Minimize x + y subject to x + y >= 2, x >= 0, y >= 0.

	Optimum: x + y = 2, objective = 2.
	"""
	x = Variable('x', min=0)
	y = Variable('y', min=0)
	objective = x + y
	constraints = [_MiniConstraint(x + y, '>=', 2)]
	return _MiniProblem('simple_min', False, objective, constraints), x, y


@pytest.fixture
def infeasible_lp():
	"""x >= 5, x <= 1 is infeasible."""
	x = Variable('x', min=0)
	objective = x
	constraints = [
		_MiniConstraint(x, '>=', 5),
		_MiniConstraint(x, '<=', 1),
	]
	return _MiniProblem('infeasible', False, objective, constraints), x


class TestPulpSolver:
	def test_solve_simple_max(self, simple_max_lp):
		problem, x, y = simple_max_lp
		solver = PulpSolver(msg=False)
		result = solver.solve(problem)
		assert result.status == SolverStatus.OPTIMAL
		assert abs(result.objective_value - 12.0) < 1e-6
		assert abs(result.variables['y'] - 4.0) < 1e-6
		assert abs(result.variables['x']) < 1e-6

	def test_solve_simple_min(self, simple_min_lp):
		problem, x, y = simple_min_lp
		solver = PulpSolver(msg=False)
		result = solver.solve(problem)
		assert result.status == SolverStatus.OPTIMAL
		assert abs(result.objective_value - 2.0) < 1e-6

	def test_detects_infeasible(self, infeasible_lp):
		problem, x = infeasible_lp
		solver = PulpSolver(msg=False)
		result = solver.solve(problem)
		assert result.status == SolverStatus.INFEASIBLE

	def test_result_to_dataframe(self, simple_max_lp):
		problem, x, y = simple_max_lp
		solver = PulpSolver(msg=False)
		result = solver.solve(problem)
		df = result.to_dataframe()
		assert set(df.columns) >= {'variable', 'value'}
		assert len(df) == 2

	def test_integer_variable(self):
		x = Variable('x', min=0, max=10, integer=True)
		objective = x
		# maximize x subject to 3x <= 10  -> integer optimal at x=3
		problem = _MiniProblem('int_test', True, objective, [_MiniConstraint(3 * x, '<=', 10)])
		solver = PulpSolver(msg=False)
		result = solver.solve(problem)
		assert result.status == SolverStatus.OPTIMAL
		assert abs(result.variables['x'] - 3.0) < 1e-6


class TestScipySolver:
	def test_solve_simple_max(self, simple_max_lp):
		problem, x, y = simple_max_lp
		solver = ScipySolver()
		result = solver.solve(problem)
		assert result.status == SolverStatus.OPTIMAL
		assert abs(result.objective_value - 12.0) < 1e-5

	def test_solve_simple_min(self, simple_min_lp):
		problem, x, y = simple_min_lp
		solver = ScipySolver()
		result = solver.solve(problem)
		assert result.status == SolverStatus.OPTIMAL
		assert abs(result.objective_value - 2.0) < 1e-5

	def test_detects_infeasible(self, infeasible_lp):
		problem, x = infeasible_lp
		solver = ScipySolver()
		result = solver.solve(problem)
		assert result.status == SolverStatus.INFEASIBLE


class TestSolverResult:
	def test_has_solve_time(self, simple_max_lp):
		problem, x, y = simple_max_lp
		result = PulpSolver(msg=False).solve(problem)
		assert result.solve_time >= 0
