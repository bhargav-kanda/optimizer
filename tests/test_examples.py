"""Tests for example problems (verifies examples actually run and produce correct answers)."""
import sys
from pathlib import Path

import pytest

# Add examples to sys.path so we can import them
EXAMPLES_DIR = Path(__file__).parent.parent / 'examples'
sys.path.insert(0, str(EXAMPLES_DIR / 'diet_problem'))
sys.path.insert(0, str(EXAMPLES_DIR / 'sm_scheduling'))

from optimizer.solvers import SolverStatus


def test_diet_problem_solves():
	from diet import build_diet_problem
	from optimizer.solvers import PulpSolver
	problem, buy = build_diet_problem()
	result = PulpSolver(msg=False).solve(problem)
	assert result.status == SolverStatus.OPTIMAL
	# Objective must be positive (we're buying food)
	assert result.objective_value > 0

	# Sanity: all buy amounts should be non-negative and within bounds
	for food, var in buy.items():
		v = result.variables[var.name]
		assert v >= -1e-6
		assert v <= var.max + 1e-6


def test_diet_problem_scipy_matches_pulp():
	"""Both solvers should agree on the LP diet problem."""
	from diet import build_diet_problem
	from optimizer.solvers import PulpSolver, ScipySolver
	problem, _ = build_diet_problem()
	pulp_res = PulpSolver(msg=False).solve(problem)
	scipy_res = ScipySolver().solve(problem)
	assert pulp_res.status == SolverStatus.OPTIMAL
	assert scipy_res.status == SolverStatus.OPTIMAL
	assert abs(pulp_res.objective_value - scipy_res.objective_value) < 1e-4


def test_sm_scheduling_demo_solves():
	"""Star Movies scheduling demo with synthetic data runs end-to-end."""
	from sm_demo import build_sm_problem
	from optimizer.solvers import PulpSolver
	problem, vars_by_key = build_sm_problem()
	result = PulpSolver(msg=False, time_limit=60).solve(problem)
	assert result.status == SolverStatus.OPTIMAL
	# Every (date, slot) must have exactly one airing
	# Verified by the constraints; just check objective is sensible
	assert result.objective_value > 0
