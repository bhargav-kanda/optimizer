"""PuLP solver backend."""
import time

import sympy as sp

from optimizer.core.linearize import extract_linear_components
from optimizer.core.constants import normalize_comparator
from optimizer.solvers.base import SolverBase, SolverResult, SolverStatus


class PulpSolver(SolverBase):
	"""Solve LP/MIP problems via the PuLP library (default backend: CBC)."""

	name = "pulp"

	def __init__(self, msg: bool = False, time_limit: int = 600, threads: int = 1):
		self.msg = msg
		self.time_limit = time_limit
		self.threads = threads

	def solve(self, problem, **kwargs) -> SolverResult:
		import pulp

		start = time.time()

		sense = pulp.LpMaximize if problem.max else pulp.LpMinimize
		lp = pulp.LpProblem(problem.name, sense)

		# Collect all symbols (variables) appearing in the objective and constraints
		all_symbols = set()
		if problem.objective is not None:
			all_symbols |= _collect_symbols(problem.objective)
		for c in problem.constraints:
			all_symbols |= _collect_symbols(c.lhs)
			all_symbols |= _collect_symbols(c.rhs)

		# Map Symbol -> LpVariable
		sym_to_pulp = {}
		for sym in all_symbols:
			lb, ub = _get_bounds(sym)
			cat = _get_category(sym)
			sym_to_pulp[sym] = pulp.LpVariable(str(sym.name), lowBound=lb, upBound=ub, cat=cat)

		# Objective
		if problem.objective is not None:
			obj_coeffs, obj_const = extract_linear_components(problem.objective)
			obj_expr = pulp.lpSum(
				[coef * sym_to_pulp[sym] for sym, coef in obj_coeffs.items()]
			) + obj_const
			lp += obj_expr

		# Constraints
		for c in problem.constraints:
			lhs_expr = _build_pulp_expr(c.lhs, sym_to_pulp)
			rhs_expr = _build_pulp_expr(c.rhs, sym_to_pulp)
			op = normalize_comparator(c.comparator)
			if op == '<=':
				lp += lhs_expr <= rhs_expr
			elif op == '>=':
				lp += lhs_expr >= rhs_expr
			elif op == '==':
				lp += lhs_expr == rhs_expr

		# Apply initial solution (warm start) if present
		initial = getattr(problem, 'initial_solution', None)
		warm_start = False
		if initial and getattr(initial, 'values', None):
			warm_start = True
			for var_name, init_val in initial.values.items():
				for sym, pv in sym_to_pulp.items():
					if sym.name == var_name:
						pv.setInitialValue(init_val)
						break

		cbc_cmd = pulp.PULP_CBC_CMD(
			msg=self.msg,
			timeLimit=self.time_limit,
			threads=self.threads,
			warmStart=warm_start,
		)
		status_code = lp.solve(cbc_cmd)
		elapsed = time.time() - start

		status = _map_pulp_status(status_code)

		result = SolverResult(
			status=status,
			solve_time=elapsed,
			solver_name=self.name,
			raw=lp,
		)
		if status == SolverStatus.OPTIMAL:
			result.objective_value = pulp.value(lp.objective)
			result.variables = {v.name: v.varValue for v in lp.variables()}
		return result


def _collect_symbols(expr):
	"""Return the set of sympy Symbols appearing in ``expr``, or empty for numerics."""
	if isinstance(expr, (int, float)):
		return set()
	if isinstance(expr, sp.Expr):
		return set(expr.free_symbols)
	return set()


def _build_pulp_expr(expr, sym_to_pulp):
	"""Convert a sympy expression (or numeric) to a PuLP linear expression."""
	import pulp
	if isinstance(expr, (int, float)):
		return float(expr)
	if isinstance(expr, sp.Expr) and not expr.free_symbols:
		return float(expr)
	coeffs, const = extract_linear_components(expr)
	return pulp.lpSum([coef * sym_to_pulp[sym] for sym, coef in coeffs.items()]) + const


def _get_bounds(sym):
	"""Extract (lower, upper) bounds from a Variable-like symbol. None means unbounded."""
	lb = getattr(sym, 'min', None)
	ub = getattr(sym, 'max', None)
	lb = None if lb is None or lb == -sp.oo else float(lb)
	ub = None if ub is None or ub == sp.oo else float(ub)
	return lb, ub


def _get_category(sym):
	import pulp
	integer = getattr(sym, 'integer', False)
	lb, ub = _get_bounds(sym)
	if integer and lb == 0 and ub == 1:
		return pulp.LpBinary
	if integer:
		return pulp.LpInteger
	return pulp.LpContinuous


def _map_pulp_status(code):
	import pulp
	mapping = {
		pulp.LpStatusOptimal: SolverStatus.OPTIMAL,
		pulp.LpStatusInfeasible: SolverStatus.INFEASIBLE,
		pulp.LpStatusUnbounded: SolverStatus.UNBOUNDED,
		pulp.LpStatusNotSolved: SolverStatus.NOT_SOLVED,
		pulp.LpStatusUndefined: SolverStatus.ERROR,
	}
	return mapping.get(code, SolverStatus.ERROR)
