"""Constraint pruning: remove constraints that are redundant given equality fixings."""
from optimizer.core.constants import normalize_comparator
from optimizer.core.linearize import extract_linear_components, LinearizationError


def prune_constraints(constraints):
	"""Remove constraints that are trivially satisfied given single-variable equalities.

	Algorithm:
	  1. Collect all 'var == value' equalities into a fixings dict.
	  2. For each non-equality constraint, substitute fixings into its expression.
	  3. If the resulting numeric inequality is trivially true, drop it.
	  4. If it's trivially false (a conflict), keep it so conflict detection catches it.

	Args:
		constraints: iterable of Constraint-like objects (have .lhs, .rhs, .comparator).

	Returns:
		List of surviving constraints. Equality constraints are always kept.
	"""
	if not constraints:
		return []

	# Step 1: collect single-variable equalities as fixings
	fixings = {}  # Symbol -> float
	for c in constraints:
		try:
			op = normalize_comparator(c.comparator)
			if op != '==':
				continue
			lhs_coeffs, lhs_const = extract_linear_components(c.lhs)
			rhs_coeffs, rhs_const = extract_linear_components(c.rhs)
			combined = dict(lhs_coeffs)
			for s, v in rhs_coeffs.items():
				combined[s] = combined.get(s, 0.0) - v
			net_const = lhs_const - rhs_const
			# Filter out zero coefficients
			combined = {s: v for s, v in combined.items() if abs(v) > 1e-12}
			if len(combined) == 1:
				sym, coef = next(iter(combined.items()))
				fixings[sym] = -net_const / coef
		except LinearizationError:
			continue

	if not fixings:
		return list(constraints)

	kept = []
	for c in constraints:
		try:
			op = normalize_comparator(c.comparator)
			# Always keep equality constraints
			if op == '==':
				kept.append(c)
				continue

			# Substitute fixings into LHS and RHS and check if trivially satisfied
			lhs_coeffs, lhs_const = extract_linear_components(c.lhs)
			rhs_coeffs, rhs_const = extract_linear_components(c.rhs)
			combined = dict(lhs_coeffs)
			for s, v in rhs_coeffs.items():
				combined[s] = combined.get(s, 0.0) - v
			net_const = lhs_const - rhs_const

			remaining_vars = {}
			for sym, coef in combined.items():
				if sym in fixings:
					net_const += coef * fixings[sym]
				else:
					remaining_vars[sym] = coef

			if remaining_vars:
				# Still has free variables — keep
				kept.append(c)
				continue

			# All variables are fixed — check if trivially true or false
			trivially_true = False
			trivially_false = False
			tol = 1e-9
			if op == '<=':
				trivially_true = net_const <= tol
				trivially_false = net_const > tol
			elif op == '>=':
				trivially_true = net_const >= -tol
				trivially_false = net_const < -tol

			if trivially_true:
				continue  # prune
			if trivially_false:
				kept.append(c)  # keep so conflict detection catches it
				continue
			kept.append(c)
		except LinearizationError:
			kept.append(c)

	return kept
