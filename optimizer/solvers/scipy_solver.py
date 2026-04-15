"""SciPy solver backend (LP only, no MIP)."""
import time

import numpy as np
import sympy as sp

from optimizer.core.linearize import extract_linear_components
from optimizer.core.constants import normalize_comparator
from optimizer.solvers.base import SolverBase, SolverResult, SolverStatus


class ScipySolver(SolverBase):
	"""Solve LP problems via scipy.optimize.linprog (default method: HiGHS).

	Does not support integer variables. Raises ValueError if any variable is integer.
	"""

	name = "scipy"

	def __init__(self, method: str = "highs"):
		self.method = method

	def solve(self, problem, **kwargs) -> SolverResult:
		from scipy.optimize import linprog

		start = time.time()

		# Collect all symbols
		all_symbols = set()
		if problem.objective is not None:
			all_symbols |= _collect_symbols(problem.objective)
		for c in problem.constraints:
			all_symbols |= _collect_symbols(c.lhs)
			all_symbols |= _collect_symbols(c.rhs)

		# Reject integer variables
		for sym in all_symbols:
			if getattr(sym, 'integer', False):
				raise ValueError(
					f"ScipySolver does not support integer variables. "
					f"Variable '{sym.name}' is integer. Use PulpSolver instead."
				)

		sym_list = sorted(all_symbols, key=lambda s: s.name)
		sym_to_idx = {sym: i for i, sym in enumerate(sym_list)}
		n = len(sym_list)

		# Objective: linprog minimizes. Negate if we're maximizing.
		c_vec = np.zeros(n)
		if problem.objective is not None:
			obj_coeffs, _obj_const = extract_linear_components(problem.objective)
			for sym, coef in obj_coeffs.items():
				c_vec[sym_to_idx[sym]] = coef
		if problem.max:
			c_vec = -c_vec

		# Constraints
		A_ub, b_ub = [], []
		A_eq, b_eq = [], []
		for constr in problem.constraints:
			lhs_coeffs, lhs_const = extract_linear_components(constr.lhs)
			rhs_coeffs, rhs_const = extract_linear_components(constr.rhs)
			# Move RHS terms to LHS: (lhs_coeffs - rhs_coeffs) * x op (rhs_const - lhs_const)
			combined = dict(lhs_coeffs)
			for sym, coef in rhs_coeffs.items():
				combined[sym] = combined.get(sym, 0.0) - coef
			rhs_val = rhs_const - lhs_const

			row = np.zeros(n)
			for sym, coef in combined.items():
				row[sym_to_idx[sym]] = coef

			op = normalize_comparator(constr.comparator)
			if op == '<=':
				A_ub.append(row)
				b_ub.append(rhs_val)
			elif op == '>=':
				A_ub.append(-row)
				b_ub.append(-rhs_val)
			else:  # ==
				A_eq.append(row)
				b_eq.append(rhs_val)

		bounds = [_get_bounds(sym) for sym in sym_list]

		kwargs_lp = dict(
			c=c_vec,
			bounds=bounds,
			method=self.method,
		)
		if A_ub:
			kwargs_lp['A_ub'] = np.array(A_ub)
			kwargs_lp['b_ub'] = np.array(b_ub)
		if A_eq:
			kwargs_lp['A_eq'] = np.array(A_eq)
			kwargs_lp['b_eq'] = np.array(b_eq)

		res = linprog(**kwargs_lp)
		elapsed = time.time() - start

		status = _map_scipy_status(res.status)
		result = SolverResult(
			status=status,
			solve_time=elapsed,
			solver_name=self.name,
			raw=res,
		)
		if status == SolverStatus.OPTIMAL:
			obj_val = float(res.fun)
			if problem.max:
				obj_val = -obj_val
			# Add back the objective constant
			if problem.objective is not None:
				_, obj_const = extract_linear_components(problem.objective)
				obj_val += obj_const
			result.objective_value = obj_val
			result.variables = {
				sym.name: float(res.x[i]) for i, sym in enumerate(sym_list)
			}
		return result


def _collect_symbols(expr):
	if isinstance(expr, (int, float)):
		return set()
	if isinstance(expr, sp.Expr):
		return set(expr.free_symbols)
	return set()


def _get_bounds(sym):
	lb = getattr(sym, 'min', None)
	ub = getattr(sym, 'max', None)
	lb = None if lb is None or lb == -sp.oo else float(lb)
	ub = None if ub is None or ub == sp.oo else float(ub)
	return (lb, ub)


def _map_scipy_status(code):
	# scipy.linprog status codes:
	# 0 = optimal, 1 = iteration limit, 2 = infeasible, 3 = unbounded, 4 = numerical
	mapping = {
		0: SolverStatus.OPTIMAL,
		2: SolverStatus.INFEASIBLE,
		3: SolverStatus.UNBOUNDED,
	}
	return mapping.get(code, SolverStatus.ERROR)
