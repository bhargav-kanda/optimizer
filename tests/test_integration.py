"""End-to-end integration tests for the full pipeline."""
import pandas as pd
import pytest
import sympy as sp

import optimizer as op
from optimizer.core.elements import Variable


class _MockProblem:
	"""Minimal problem object matching the interface solvers expect.

	Real problems are created via OpFormulation; this is a shortcut for testing
	the solver path without the symbolic expression layer.
	"""
	def __init__(self, name, max, objective, constraints):
		self.name = name
		self.max = max
		self.objective = objective
		self.constraints = constraints
		self.partial_solution = None
		self.initial_solution = None


class _MockConstraint:
	def __init__(self, lhs, op, rhs):
		self.lhs, self.comparator, self.rhs = lhs, op, rhs


def test_diet_problem_direct_api():
	"""Diet problem solved by building expressions directly with sympy + Variable.

	Minimize: 2*bread + 3*cheese
	Subject to: bread + 2*cheese >= 10, 3*bread + cheese >= 12, bread,cheese >= 0

	Expected optimum: bread=2.8, cheese=3.6, objective=16.4.
	"""
	bread = Variable('bread', min=0)
	cheese = Variable('cheese', min=0)

	problem = _MockProblem(
		'diet', max=False,
		objective=2 * bread + 3 * cheese,
		constraints=[
			_MockConstraint(bread + 2 * cheese, '>=', 10),
			_MockConstraint(3 * bread + cheese, '>=', 12),
		],
	)

	result = op.PulpSolver(msg=False).solve(problem)
	assert result.status == op.SolverStatus.OPTIMAL
	assert abs(result.objective_value - 16.4) < 1e-4
	assert abs(result.variables['bread'] - 2.8) < 1e-4
	assert abs(result.variables['cheese'] - 3.6) < 1e-4


def test_diet_problem_scipy_matches_pulp():
	"""Both solvers should produce the same answer for LP problems."""
	bread = Variable('bread', min=0)
	cheese = Variable('cheese', min=0)

	problem = _MockProblem(
		'diet', max=False,
		objective=2 * bread + 3 * cheese,
		constraints=[
			_MockConstraint(bread + 2 * cheese, '>=', 10),
			_MockConstraint(3 * bread + cheese, '>=', 12),
		],
	)

	pulp_result = op.PulpSolver(msg=False).solve(problem)
	scipy_result = op.ScipySolver().solve(problem)
	assert pulp_result.status == op.SolverStatus.OPTIMAL
	assert scipy_result.status == op.SolverStatus.OPTIMAL
	assert abs(pulp_result.objective_value - scipy_result.objective_value) < 1e-4


def test_mip_via_pulp():
	"""Integer programming: maximize x + y subject to x + y <= 4.5, both integer."""
	x = Variable('x', min=0, max=10, integer=True)
	y = Variable('y', min=0, max=10, integer=True)
	problem = _MockProblem('mip', max=True,
		objective=x + y,
		constraints=[_MockConstraint(x + y, '<=', 4.5)])
	result = op.PulpSolver(msg=False).solve(problem)
	assert result.status == op.SolverStatus.OPTIMAL
	assert abs(result.objective_value - 4.0) < 1e-4  # Integer optimum


def test_opproblem_check_conflicts_lite_raises_on_error():
	"""OpProblem.check_conflicts(mode='lite') should raise ConflictError when infeasible."""
	from optimizer.core.optimizer import OpProblem, OpFormulation
	from optimizer.core.exceptions import ConflictError
	x = Variable('x', min=0, max=100)
	f = OpFormulation('bad', max=False)
	problem = OpProblem(name='bad', formulation=f, max=False)
	problem.objective = x
	problem.constraints = [
		_MockConstraint(x, '<=', 3),
		_MockConstraint(x, '>=', 8),
	]
	with pytest.raises(ConflictError) as exc_info:
		problem.check_conflicts(mode='lite')
	assert len(exc_info.value.conflicts) >= 1


def test_opproblem_check_conflicts_pro_catches_multi_var():
	from optimizer.core.optimizer import OpProblem, OpFormulation
	from optimizer.core.exceptions import ConflictError
	x = Variable('x', min=0, max=10)
	y = Variable('y', min=0, max=10)
	f = OpFormulation('bad', max=False)
	problem = OpProblem(name='bad', formulation=f, max=False)
	problem.objective = x + y
	# Lite would miss this combined infeasibility; pro catches it
	problem.constraints = [
		_MockConstraint(x + y, '>=', 50),
		_MockConstraint(x, '<=', 10),
		_MockConstraint(y, '<=', 10),
	]
	with pytest.raises(ConflictError):
		problem.check_conflicts(mode='pro')


def test_opproblem_prune_constraints():
	"""prune_constraints() should remove redundant inequalities given fixings."""
	from optimizer.core.optimizer import OpProblem, OpFormulation
	x = Variable('x', min=0, max=100)
	y = Variable('y', min=0, max=100)
	f = OpFormulation('prune', max=True)
	problem = OpProblem(name='prune', formulation=f, max=True)
	problem.objective = x + y
	problem.constraints = [
		_MockConstraint(x, '==', 2),        # fixing
		_MockConstraint(x, '<=', 10),       # redundant (2 <= 10)
		_MockConstraint(y, '<=', 5),        # not redundant
	]
	pruned_count = problem.prune_constraints()
	assert pruned_count == 1
	assert len(problem.constraints) == 2


def test_opformulation_solve_delegation():
	"""OpProblem.solve() should delegate to PulpSolver by default."""
	bread = Variable('bread', min=0)
	cheese = Variable('cheese', min=0)

	# Build a bare OpProblem to test the solve() delegation path
	from optimizer.core.optimizer import OpProblem, OpFormulation
	f = OpFormulation('test', max=False)
	problem = OpProblem(name='test', formulation=f, max=False)
	problem.objective = 2 * bread + 3 * cheese
	problem.constraints = [
		_MockConstraint(bread + 2 * cheese, '>=', 10),
		_MockConstraint(3 * bread + cheese, '>=', 12),
	]

	result = problem.solve(solver=op.PulpSolver(msg=False))
	assert result.status == op.SolverStatus.OPTIMAL
	assert abs(problem.objective_value - 16.4) < 1e-4
	assert problem.status == op.SolverStatus.OPTIMAL
	df = problem.get_result_dataframe()
	assert len(df) == 2
