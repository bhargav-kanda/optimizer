"""Tests for optimizer.core.linearize.extract_linear_components."""
import pytest
import sympy as sp
from sympy import Symbol, Rational, Float, Integer

from optimizer.core.linearize import extract_linear_components, LinearizationError


class TestExtractLinearComponents:
	def test_pure_number_int(self):
		coeffs, const = extract_linear_components(sp.Integer(5))
		assert coeffs == {}
		assert const == 5.0

	def test_pure_number_python_int(self):
		coeffs, const = extract_linear_components(3)
		assert coeffs == {}
		assert const == 3.0

	def test_pure_number_float(self):
		coeffs, const = extract_linear_components(sp.Float(2.5))
		assert coeffs == {}
		assert const == 2.5

	def test_single_variable(self):
		x = Symbol('x')
		coeffs, const = extract_linear_components(x)
		assert coeffs == {x: 1.0}
		assert const == 0.0

	def test_coefficient_times_variable(self):
		x = Symbol('x')
		coeffs, const = extract_linear_components(3 * x)
		assert coeffs == {x: 3.0}
		assert const == 0.0

	def test_sum_of_variables(self):
		x, y = Symbol('x'), Symbol('y')
		coeffs, const = extract_linear_components(x + y)
		assert coeffs == {x: 1.0, y: 1.0}
		assert const == 0.0

	def test_linear_combination(self):
		x, y = Symbol('x'), Symbol('y')
		coeffs, const = extract_linear_components(2 * x + 3 * y - 1)
		assert coeffs == {x: 2.0, y: 3.0}
		assert const == -1.0

	def test_negation(self):
		x = Symbol('x')
		coeffs, const = extract_linear_components(-x)
		assert coeffs == {x: -1.0}
		assert const == 0.0

	def test_subtraction(self):
		x, y = Symbol('x'), Symbol('y')
		coeffs, const = extract_linear_components(x - y)
		assert coeffs == {x: 1.0, y: -1.0}
		assert const == 0.0

	def test_rational_coefficient(self):
		x = Symbol('x')
		coeffs, const = extract_linear_components(Rational(1, 2) * x)
		assert coeffs == {x: 0.5}
		assert const == 0.0

	def test_float_coefficient(self):
		x = Symbol('x')
		coeffs, const = extract_linear_components(sp.Float(1.5) * x)
		assert coeffs == {x: 1.5}
		assert const == 0.0

	def test_zero(self):
		coeffs, const = extract_linear_components(sp.Integer(0))
		assert coeffs == {}
		assert const == 0.0

	def test_combined_same_variable(self):
		x = Symbol('x')
		coeffs, const = extract_linear_components(2 * x + 3 * x)
		# After expand(), should combine to 5*x
		assert coeffs == {x: 5.0}
		assert const == 0.0

	def test_nonlinear_product_raises(self):
		x, y = Symbol('x'), Symbol('y')
		with pytest.raises(LinearizationError):
			extract_linear_components(x * y)

	def test_nonlinear_square_raises(self):
		x = Symbol('x')
		with pytest.raises(LinearizationError):
			extract_linear_components(x ** 2)

	def test_many_variables(self):
		vars = [Symbol(f'x{i}') for i in range(5)]
		expr = sum((i + 1) * v for i, v in enumerate(vars))  # 1*x0 + 2*x1 + ... + 5*x4
		coeffs, const = extract_linear_components(expr)
		for i, v in enumerate(vars):
			assert coeffs[v] == float(i + 1)
		assert const == 0.0

	def test_constant_only_expression(self):
		coeffs, const = extract_linear_components(sp.Integer(7) - sp.Integer(3))
		assert coeffs == {}
		assert const == 4.0

	def test_variable_minus_constant(self):
		x = Symbol('x')
		coeffs, const = extract_linear_components(x - 5)
		assert coeffs == {x: 1.0}
		assert const == -5.0

	def test_constant_minus_variable(self):
		x = Symbol('x')
		coeffs, const = extract_linear_components(5 - x)
		assert coeffs == {x: -1.0}
		assert const == 5.0

	def test_negative_one_coefficient(self):
		x = Symbol('x')
		coeffs, const = extract_linear_components(-1 * x)
		assert coeffs == {x: -1.0}

	def test_fraction_constant(self):
		x = Symbol('x')
		coeffs, const = extract_linear_components(x + Rational(1, 3))
		assert coeffs == {x: 1.0}
		assert abs(const - 1/3) < 1e-10
