"""Constraint conflict detection — lite (heuristic) and pro (LP-based) modes."""
from dataclasses import dataclass, field
from enum import Enum
from typing import List, Optional

import sympy as sp

from optimizer.core.constants import normalize_comparator
from optimizer.core.linearize import extract_linear_components, LinearizationError


class ConflictSeverity(Enum):
	ERROR = "error"
	WARNING = "warning"


@dataclass
class Conflict:
	"""A detected constraint conflict or warning."""
	description: str
	severity: ConflictSeverity = ConflictSeverity.ERROR
	constraints: List = field(default_factory=list)


def detect_conflicts(constraints) -> List[Conflict]:
	"""Lite conflict detection using heuristic strategies (no solver needed).

	Strategies:
	  1. Variable's own bounds contradict (min > max).
	  2. Simple feasibility: for a >= constraint, check if max achievable LHS
	     (using variable upper bounds) can reach the RHS. For <=, check min.
	  3. Contradictory equalities: same single variable forced to different values.
	  4. Tighter combined bounds: a >= L constraint and <= U constraint where L > U.
	"""
	conflicts: List[Conflict] = []

	# Collect variables referenced across constraints
	all_vars = set()
	for c in constraints:
		all_vars |= _vars_in(c.lhs)
		all_vars |= _vars_in(c.rhs)

	# Strategy 1: variable's own bounds
	for v in all_vars:
		lo, hi = _bounds(v)
		if lo is not None and hi is not None and lo > hi:
			conflicts.append(Conflict(
				description=f"Variable '{v.name}' has lower bound {lo} > upper bound {hi}",
				severity=ConflictSeverity.ERROR,
			))

	# Strategy 2: simple feasibility per constraint
	for c in constraints:
		try:
			issue = _check_simple_feasibility(c)
		except LinearizationError:
			continue
		if issue is not None:
			conflicts.append(issue)

	# Strategy 3: contradictory equalities on a single variable (including after linearization)
	equalities_by_var = {}
	for c in constraints:
		try:
			if normalize_comparator(c.comparator) != '==':
				continue
			coeffs, const = _standardize(c)
			if len(coeffs) == 1:
				var, coef = next(iter(coeffs.items()))
				if coef == 0:
					continue
				value = -const / coef
				if var in equalities_by_var:
					other = equalities_by_var[var]
					if abs(other - value) > 1e-9:
						conflicts.append(Conflict(
							description=(
								f"Variable '{var.name}' is equated to both {other} and {value}"
							),
							severity=ConflictSeverity.ERROR,
						))
				else:
					equalities_by_var[var] = value
		except LinearizationError:
			continue

	# Strategy 4: tightest implied single-variable bounds
	implied_lo = {}
	implied_hi = {}
	for c in constraints:
		try:
			coeffs, const = _standardize(c)
			op = normalize_comparator(c.comparator)
			if len(coeffs) != 1:
				continue
			var, coef = next(iter(coeffs.items()))
			if coef == 0:
				continue
			rhs_effective = -const / coef
			# If coef < 0, flip direction
			if coef < 0:
				op = {'<=': '>=', '>=': '<=', '==': '=='}[op]
			if op == '<=':
				implied_hi[var] = min(implied_hi.get(var, float('inf')), rhs_effective)
			elif op == '>=':
				implied_lo[var] = max(implied_lo.get(var, float('-inf')), rhs_effective)
			else:
				implied_lo[var] = max(implied_lo.get(var, float('-inf')), rhs_effective)
				implied_hi[var] = min(implied_hi.get(var, float('inf')), rhs_effective)
		except LinearizationError:
			continue

	for var in implied_lo.keys() | implied_hi.keys():
		lo_decl, hi_decl = _bounds(var)
		lo = max(implied_lo.get(var, float('-inf')),
		          lo_decl if lo_decl is not None else float('-inf'))
		hi = min(implied_hi.get(var, float('inf')),
		          hi_decl if hi_decl is not None else float('inf'))
		if lo > hi + 1e-9:
			conflicts.append(Conflict(
				description=(
					f"Implied bounds on '{var.name}' are infeasible: "
					f"lower {lo} > upper {hi}"
				),
				severity=ConflictSeverity.ERROR,
			))

	return _dedupe(conflicts)


def detect_conflicts_lp(constraints) -> List[Conflict]:
	"""Pro conflict detection: run a feasibility LP to detect infeasibility that
	heuristics miss (interactions across multiple variables and constraints).

	Uses the PulpSolver with a zero objective function. If the solver reports
	infeasibility, a single ERROR conflict is returned covering all constraints.
	"""
	# Start with lite heuristics
	conflicts = list(detect_conflicts(constraints))

	if not constraints:
		return conflicts

	# Run feasibility LP with zero objective
	from optimizer.solvers import PulpSolver, SolverStatus

	class _FeasibilityProblem:
		pass
	fp = _FeasibilityProblem()
	fp.name = "feasibility_check"
	fp.max = False
	fp.objective = sp.Integer(0)
	fp.constraints = list(constraints)
	fp.partial_solution = None
	fp.initial_solution = None

	try:
		result = PulpSolver(msg=False).solve(fp)
	except Exception as e:
		conflicts.append(Conflict(
			description=f"Feasibility check failed: {e}",
			severity=ConflictSeverity.WARNING,
			constraints=list(constraints),
		))
		return _dedupe(conflicts)

	if result.status == SolverStatus.INFEASIBLE:
		conflicts.append(Conflict(
			description="LP feasibility check: the full constraint system is infeasible",
			severity=ConflictSeverity.ERROR,
			constraints=list(constraints),
		))

	return _dedupe(conflicts)


def _vars_in(expr):
	if isinstance(expr, (int, float)):
		return set()
	if isinstance(expr, sp.Expr):
		return set(expr.free_symbols)
	return set()


def _bounds(var):
	lo = getattr(var, 'min', None)
	hi = getattr(var, 'max', None)
	lo = None if lo is None or lo == -sp.oo else float(lo)
	hi = None if hi is None or hi == sp.oo else float(hi)
	return lo, hi


def _standardize(constraint):
	"""Return (coeffs, rhs_effective_const) moved to LHS with RHS = 0.

	After this, the constraint is: sum(coef_i * var_i) + const <op> 0.
	"""
	lhs_coeffs, lhs_const = extract_linear_components(constraint.lhs)
	rhs_coeffs, rhs_const = extract_linear_components(constraint.rhs)
	combined = dict(lhs_coeffs)
	for sym, coef in rhs_coeffs.items():
		combined[sym] = combined.get(sym, 0.0) - coef
	return combined, lhs_const - rhs_const


def _check_simple_feasibility(constraint) -> Optional[Conflict]:
	coeffs, const = _standardize(constraint)
	op = normalize_comparator(constraint.comparator)

	# Determine the range of LHS = sum(coef * var) + const given each var's bounds
	min_lhs = const
	max_lhs = const
	for var, coef in coeffs.items():
		lo, hi = _bounds(var)
		if coef >= 0:
			min_lhs += coef * (lo if lo is not None else float('-inf'))
			max_lhs += coef * (hi if hi is not None else float('inf'))
		else:
			min_lhs += coef * (hi if hi is not None else float('inf'))
			max_lhs += coef * (lo if lo is not None else float('-inf'))

	# Constraint is lhs_combined <op> 0
	if op == '<=':
		if min_lhs > 1e-9:
			return Conflict(
				description=(
					f"Constraint is infeasible: minimum achievable LHS is {min_lhs:.4g}, "
					f"but constraint requires <= 0"
				),
				severity=ConflictSeverity.ERROR,
				constraints=[constraint],
			)
	elif op == '>=':
		if max_lhs < -1e-9:
			return Conflict(
				description=(
					f"Constraint is infeasible: maximum achievable LHS is {max_lhs:.4g}, "
					f"but constraint requires >= 0"
				),
				severity=ConflictSeverity.ERROR,
				constraints=[constraint],
			)
	elif op == '==':
		if max_lhs < -1e-9 or min_lhs > 1e-9:
			return Conflict(
				description=(
					f"Constraint is infeasible: achievable LHS in [{min_lhs:.4g}, {max_lhs:.4g}] "
					f"doesn't include 0"
				),
				severity=ConflictSeverity.ERROR,
				constraints=[constraint],
			)
	return None


def _dedupe(conflicts):
	seen = set()
	out = []
	for c in conflicts:
		key = (c.description, c.severity)
		if key not in seen:
			seen.add(key)
			out.append(c)
	return out
