"""Linearization utilities — decompose SymPy expressions into {variable: coefficient} + constant."""
import sympy as sp
from sympy import Symbol, Number, Add, Mul, Expr


class LinearizationError(ValueError):
	"""Raised when an expression cannot be expressed as a linear combination."""


def extract_linear_components(expr):
	"""Decompose a linear SymPy expression into coefficients and a constant.

	Given an expression like ``2*x + 3*y - 1``, returns ``({x: 2.0, y: 3.0}, -1.0)``.

	Args:
		expr: A SymPy expression (or numeric), assumed to be linear in its symbols.

	Returns:
		(coeffs, constant) where coeffs is a dict mapping Symbol -> float,
		and constant is a float.

	Raises:
		LinearizationError: If the expression contains non-linear terms.
	"""
	if isinstance(expr, (int, float)):
		return {}, float(expr)
	if not isinstance(expr, Expr):
		raise LinearizationError(f"Cannot linearize non-SymPy value: {expr!r}")

	expr = sp.expand(expr)

	coeffs = {}
	constant = 0.0

	terms = expr.args if isinstance(expr, Add) else (expr,)

	for term in terms:
		if isinstance(term, Number):
			constant += float(term)
		elif isinstance(term, Symbol):
			coeffs[term] = coeffs.get(term, 0.0) + 1.0
		elif isinstance(term, Mul):
			numeric_factor = 1.0
			symbol = None
			for factor in term.args:
				if isinstance(factor, Number):
					numeric_factor *= float(factor)
				elif isinstance(factor, Symbol):
					if symbol is not None:
						raise LinearizationError(
							f"Non-linear term (product of symbols): {term}"
						)
					symbol = factor
				else:
					raise LinearizationError(
						f"Unsupported factor in term {term}: {factor!r} ({type(factor).__name__})"
					)
			if symbol is None:
				constant += numeric_factor
			else:
				coeffs[symbol] = coeffs.get(symbol, 0.0) + numeric_factor
		else:
			raise LinearizationError(
				f"Unsupported term: {term!r} ({type(term).__name__})"
			)

	return coeffs, constant
