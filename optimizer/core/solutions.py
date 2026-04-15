"""Solution types — partial and initial solutions for warm-starting and fixing variables."""
from typing import Dict, Optional

import pandas as pd


class Solution:
	"""Base class for solution types."""

	def __init__(self, fixed_values: Optional[Dict[str, float]] = None):
		self.fixed_values = fixed_values or {}


class PartialSolution(Solution):
	"""Fix a subset of variables to known values by adding equality constraints.

	Example:
		>>> ps = PartialSolution({'x_1': 5.0, 'x_2': 3.0})
		>>> ps.apply_to_problem(problem)
	"""

	def __init__(self, fixed_values: Optional[Dict[str, float]] = None):
		super().__init__(fixed_values)

	@classmethod
	def from_dataframe(cls, df: pd.DataFrame,
	                   variable_col: str = 'variable',
	                   value_col: str = 'value') -> 'PartialSolution':
		if variable_col not in df.columns:
			raise ValueError(f"Column {variable_col!r} not in DataFrame (have: {list(df.columns)})")
		if value_col not in df.columns:
			raise ValueError(f"Column {value_col!r} not in DataFrame (have: {list(df.columns)})")
		return cls(fixed_values=dict(zip(df[variable_col], df[value_col])))

	def apply_to_problem(self, problem) -> None:
		"""Add equality constraints to the problem fixing each named variable.

		Looks up the Variable/Symbol object in existing constraints or objective,
		then adds `var == value` equality constraints.
		"""
		import sympy as sp

		# Build a map from variable name -> Symbol by scanning all expressions
		name_to_symbol = {}
		def _collect(expr):
			if isinstance(expr, sp.Expr):
				for sym in expr.free_symbols:
					name_to_symbol.setdefault(sym.name, sym)
		if problem.objective is not None:
			_collect(problem.objective)
		for c in problem.constraints:
			_collect(c.lhs)
			_collect(c.rhs)

		# Create a simple constraint-like shim and append
		class _FixConstraint:
			def __init__(self, lhs, rhs, comparator='=='):
				self.lhs = lhs
				self.rhs = rhs
				self.comparator = comparator
				self.rule = None

		for var_name, value in self.fixed_values.items():
			sym = name_to_symbol.get(var_name)
			if sym is None:
				# Variable doesn't appear in problem — skip silently or warn?
				# We skip: a partial solution may reference variables that don't exist yet.
				continue
			problem.constraints.append(_FixConstraint(lhs=sym, rhs=value, comparator='=='))

		# Also register the partial solution on the problem for reference
		problem.partial_solution = self


class InitialSolution(Solution):
	"""Provide an initial guess to the solver for warm-starting.

	Used by PulpSolver's warmStart option. The solver begins from these values
	instead of computing an initial feasible point from scratch.

	Args:
		values: Dict mapping variable name -> initial value.
		cost_to_change: Optional penalty for deviating from the initial solution
			(not yet implemented across all solvers).
	"""

	def __init__(self, values: Optional[Dict[str, float]] = None, cost_to_change: float = 0):
		super().__init__(values)
		self.values = values or {}
		self.cost_to_change = cost_to_change

	@classmethod
	def from_dataframe(cls, df: pd.DataFrame,
	                   variable_col: str = 'variable',
	                   value_col: str = 'value',
	                   cost_to_change: float = 0) -> 'InitialSolution':
		if variable_col not in df.columns:
			raise ValueError(f"Column {variable_col!r} not in DataFrame (have: {list(df.columns)})")
		if value_col not in df.columns:
			raise ValueError(f"Column {value_col!r} not in DataFrame (have: {list(df.columns)})")
		return cls(values=dict(zip(df[variable_col], df[value_col])),
		           cost_to_change=cost_to_change)
