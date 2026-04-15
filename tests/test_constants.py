"""Tests for comparator normalization and constant helpers."""
import pytest

from optimizer.core.constants import (
	normalize_comparator, LESSTHAN, GREATERTHAN, EQUALTO,
)


class TestNormalizeComparator:
	def test_canonical_passthrough(self):
		assert normalize_comparator('<=') == '<='
		assert normalize_comparator('>=') == '>='
		assert normalize_comparator('==') == '=='

	def test_sm_aliases(self):
		assert normalize_comparator('lesser') == '<='
		assert normalize_comparator('greater') == '>='
		assert normalize_comparator('equal') == '=='

	def test_constants(self):
		# The module constants are themselves the canonical form
		assert normalize_comparator(LESSTHAN) == '<='
		assert normalize_comparator(GREATERTHAN) == '>='
		assert normalize_comparator(EQUALTO) == '=='

	def test_case_insensitive(self):
		assert normalize_comparator('LESSTHAN') == '<='
		assert normalize_comparator('Equal') == '=='

	def test_single_equals_becomes_double(self):
		assert normalize_comparator('=') == '=='

	def test_unknown_raises(self):
		with pytest.raises(ValueError):
			normalize_comparator('foo')
