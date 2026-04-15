"""Tests for conflict detection (lite and pro modes)."""
import pytest

from optimizer.core.conflict_detection import (
	Conflict, ConflictSeverity, detect_conflicts, detect_conflicts_lp,
)
from optimizer.core.elements import Variable


class _C:
	def __init__(self, lhs, op, rhs):
		self.lhs, self.comparator, self.rhs = lhs, op, rhs


class TestDetectConflictsLite:
	def test_no_conflicts(self):
		x = Variable('x', min=0, max=10)
		conflicts = detect_conflicts([_C(x, '<=', 5), _C(x, '>=', 1)])
		assert conflicts == []

	def test_single_variable_bound_conflict(self):
		x = Variable('x', min=0, max=10)
		# x >= 8 AND x <= 3 — infeasible
		conflicts = detect_conflicts([_C(x, '>=', 8), _C(x, '<=', 3)])
		assert any(c.severity == ConflictSeverity.ERROR for c in conflicts)

	def test_variable_own_bounds_conflict(self):
		# Variable itself has min > max
		x = Variable('x', min=5, max=3)
		conflicts = detect_conflicts([_C(x, '<=', 10)])
		assert any(c.severity == ConflictSeverity.ERROR for c in conflicts)

	def test_geq_infeasible_via_max(self):
		# x <= 5 but we require 3x >= 20  -> max LHS = 15 < 20
		x = Variable('x', min=0, max=5)
		conflicts = detect_conflicts([_C(3 * x, '>=', 20)])
		assert any(c.severity == ConflictSeverity.ERROR for c in conflicts)

	def test_leq_infeasible_via_min(self):
		# x >= 10 but we require x <= 5 — min LHS = 10 > 5
		x = Variable('x', min=10, max=100)
		conflicts = detect_conflicts([_C(x, '<=', 5)])
		assert any(c.severity == ConflictSeverity.ERROR for c in conflicts)

	def test_contradictory_equalities(self):
		x = Variable('x', min=0, max=100)
		conflicts = detect_conflicts([_C(x, '==', 3), _C(x, '==', 7)])
		assert any(c.severity == ConflictSeverity.ERROR for c in conflicts)

	def test_empty_constraint_list(self):
		assert detect_conflicts([]) == []


class TestDetectConflictsLP:
	"""Pro mode: run a feasibility LP to detect infeasibility that heuristics miss."""

	def test_feasible_problem_returns_no_conflicts(self):
		x = Variable('x', min=0, max=10)
		y = Variable('y', min=0, max=10)
		conflicts = detect_conflicts_lp([_C(x + y, '<=', 5)])
		assert conflicts == []

	def test_infeasible_intersection_detected(self):
		# x + y >= 10, x + y <= 3 — individually feasible but together not
		x = Variable('x', min=0, max=10)
		y = Variable('y', min=0, max=10)
		conflicts = detect_conflicts_lp([
			_C(x + y, '>=', 10),
			_C(x + y, '<=', 3),
		])
		assert any(c.severity == ConflictSeverity.ERROR for c in conflicts)

	def test_lp_conflicts_catch_what_lite_misses(self):
		"""A case where heuristics can't detect infeasibility but LP can."""
		x = Variable('x', min=0, max=100)
		y = Variable('y', min=0, max=100)
		# Neither constraint alone is infeasible; together they are.
		constraints = [
			_C(x + y, '>=', 50),
			_C(x, '<=', 10),
			_C(y, '<=', 10),
		]
		lite = detect_conflicts(constraints)
		pro = detect_conflicts_lp(constraints)
		# Lite misses this; pro should catch
		assert not any(c.severity == ConflictSeverity.ERROR for c in lite)
		assert any(c.severity == ConflictSeverity.ERROR for c in pro)
