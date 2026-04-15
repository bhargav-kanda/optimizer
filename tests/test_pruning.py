"""Tests for constraint pruning (removal of redundant constraints)."""
import pytest

from optimizer.core.pruning import prune_constraints
from optimizer.core.elements import Variable


class _C:
	def __init__(self, lhs, op, rhs):
		self.lhs, self.comparator, self.rhs = lhs, op, rhs


class TestPruneConstraints:
	def test_no_pruning_when_no_equalities(self):
		x = Variable('x', min=0, max=10)
		y = Variable('y', min=0, max=10)
		constraints = [_C(x, '<=', 5), _C(y, '>=', 2)]
		result = prune_constraints(constraints)
		assert len(result) == 2

	def test_removes_redundant_after_fixing_var(self):
		"""If x == 5 is an equality, then x <= 10 is implied (redundant)."""
		x = Variable('x', min=0, max=100)
		eq = _C(x, '==', 5)
		redundant = _C(x, '<=', 10)  # 5 <= 10 always true
		result = prune_constraints([eq, redundant])
		assert len(result) == 1  # equality kept, redundant removed
		assert result[0] is eq

	def test_keeps_non_redundant(self):
		"""If x == 5 and we have y >= 3, neither is redundant."""
		x = Variable('x', min=0, max=100)
		y = Variable('y', min=0, max=100)
		eq = _C(x, '==', 5)
		non_redundant = _C(y, '>=', 3)
		result = prune_constraints([eq, non_redundant])
		assert len(result) == 2

	def test_substitutes_fixed_var_in_multi_var_constraint(self):
		"""Given x == 2, constraint '3x + y <= 10' becomes 'y <= 4'.

		The multi-var constraint should be kept (not trivially satisfied) but
		it should be substituted. Pruning doesn't have to modify the constraint;
		it only needs to remove the trivially satisfied ones.
		"""
		x = Variable('x', min=0, max=100)
		y = Variable('y', min=0, max=100)
		eq = _C(x, '==', 2)
		keep_me = _C(3 * x + y, '<=', 10)  # 6 + y <= 10, requires y <= 4 — not redundant
		result = prune_constraints([eq, keep_me])
		assert len(result) == 2

	def test_removes_constraint_trivially_violated_by_equality_raises(self):
		"""If x == 5 and constraint x <= 3, that's a CONFLICT not prunable.

		Pruning should leave the conflict intact so that conflict detection
		catches it. Don't silently discard.
		"""
		x = Variable('x', min=0, max=100)
		eq = _C(x, '==', 5)
		conflict = _C(x, '<=', 3)
		result = prune_constraints([eq, conflict])
		# Both should remain so conflict detection can flag the contradiction
		assert len(result) == 2

	def test_returns_empty_for_empty_input(self):
		assert prune_constraints([]) == []
