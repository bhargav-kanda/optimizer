from optimizer.core.elements import *
from optimizer.core.helper_functions import *
from operator import mul
import pandas as pd
import optimizer as op


class Term:

	def __init__(self, expression, coeff=1, power=1):
		if True in [isinstance(expression, Variable), isinstance(expression, Expression),
		            isinstance(expression, int), isinstance(expression, float)]:
			self.expression = expression
		else:
			raise Exception('expression of wrong type.')
		if True in [isinstance(power, Variable), isinstance(power, Expression),
		            isinstance(power, int), isinstance(power, float)]:
			self.power = power
		else:
			raise Exception('power of wrong type')
		if isinstance(coeff, int) or isinstance(coeff, float):
			self.coeff = coeff
		else:
			raise Exception('coefficient of wrong type in term')
		self.max_var = None
		self.max_power = None
		self.min_var = None
		self.min_power = None
		self.computed = False

	def compute_max_and_mins(self):
		self.max_power = get_max(self.power)
		self.max_var = get_max(self.expression)
		self.min_power = get_min(self.power)
		self.min_var = get_min(self.expression)

	@property
	def max_value(self):
		if not self.computed:
			self.compute_max_and_mins()
		if self.max_var is None:
			if self.max_power is not None and self.max_power < 0 and self.min_var is not None:
				return pow(self.min_var, self.max_power)
			else:
				return None
		elif abs(self.max_var) < 1:
			if self.max_var > 0 and self.min_power is not None:
				return pow(self.max_var, self.min_power)
			elif self.max_var < 0:
				return None
			else:
				return 0
		if self.max_power is None:
			if self.max_var is not None and 0 < self.max_var < 1 and self.min_power is not None:
				return pow(self.max_var, self.min_power)
			else:
				return None
		elif self.max_power < 0:
			if Term(self.expression, 1, abs(self.power)).min_value != 0:
				return 1 / Term(self.expression, 1, abs(self.power)).min_value
			else:
				return None
		return pow(self.max_var, self.max_power)

	@property
	def min_value(self):
		# pdb.set_trace()
		if not self.computed:
			self.compute_max_and_mins()
		if self.min_var is None:
			if self.min_power is not None and self.min_power < 0 and self.max_var is not None:
				return pow(self.max_var, self.min_power)
			else:
				return None
		elif abs(self.min_var) < 1:
			if self.min_var > 0 and self.max_power is not None:
				return pow(self.min_var, self.max_power)
			elif self.min_var < 0:
				return None
			else:
				return 0
		if self.min_power is None:
			if self.min_var is not None and 0 < self.min_var < 1 and self.max_power is not None:
				return pow(self.min_var, self.max_power)
			else:
				return None
		elif self.min_power < 0:
			if Term(self.expression, 1, abs(self.power)).min_value != 0:
				return 1 / Term(self.expression, 1, abs(self.power)).min_value
			else:
				return None
		return pow(self.min_var, self.min_power)

	def __str__(self):
		prefix = '{} * '.format(self.coeff) if self.coeff != 1 else ''
		suffix = ' ^ {}'.format(self.power) if self.power != 1 else ''
		return prefix + str(self.expression) + suffix


MULTIPLY = '*'
ADD = '+'


class Expression:

	def __init__(self, terms, operand, constant=0):
		self.terms = terms
		if operand not in [MULTIPLY, ADD]:
			raise Exception('Operand should either be ADD or MULTIPLY')
		self.operand = operand
		if isinstance(constant, int) or isinstance(constant, float):
			self.constant = constant
		else:
			raise Exception('constant should either be int or float')

	def add_term(self, term):
		if not isinstance(term, Term):
			raise Exception('term should be of type Term')
		self.terms.append(term)
		return self

	@property
	def max_value(self):
		if self.operand == ADD:
			return sum([x.max_value for x in self.terms]) + self.constant
		else:
			return mul([x.max_value for x in self.terms]) + self.constant

	@property
	def min_value(self):
		if self.operand == ADD:
			return sum([x.min_value for x in self.terms]) + self.constant
		else:
			return mul([x.max_value for x in self.terms]) + self.constant

	def __str__(self):
		if len(self.terms) > 1:
			if self.operand == ADD:
				string = ' + '.join([str(t) for t in self.terms])
			else:
				string = ' * '.join([str(t) for t in self.terms])
		else:
			string = str(self.terms[0])
		if self.constant != 0:
			if self.constant > 0:
				string += ' + ' + str(self.constant)
			else:
				string += ' - ' + str(abs(self.constant))
		if len(self.terms) > 1 or self.constant != 0:
			string = '(' + string + ')'
		return string

	def __add__(self, other):
		if isinstance(other, Variable) or isinstance(other, Expression):
			return Expression([Term(self.copy(), 1, 1), Term(other.copy(), 1, 1)],
			                  operand=ADD, constant=self.constant)
		elif isinstance(other, int) or isinstance(other, float):
			return Expression([self.terms], operand=self.operand, constant=self.constant + other)
		else:
			raise Exception('Wrong datatype for expression addition')

	def __radd__(self, other):
		return self + other

	def __sub__(self, other):
		return self + -other

	def __rsub__(self, other):
		return other - self

	def __mul__(self, other):
		if isinstance(other, Variable) or isinstance(other, Expression):
			return Expression([Term(self.copy(), 1, 1), Term(other.copy(), 1, 1)],
			                  operand=MULTIPLY, constant=self.constant)
		elif isinstance(other, int) or isinstance(other, float):
			return Expression([Term(self.copy(), other, 1)], operand=self.operand)
		else:
			raise Exception('Wrong datatype for expression addition')

	def __rmul__(self, other):
		return other * self

	def __div__(self, other):
		return self * (1/other)

	def __rdiv__(self, other):
		return other / self

	def __pow__(self, power, modulo=None):
		return Expression([Term(self.copy(), 1, power.copy())], ADD)

	def __neg__(self):
		return Expression([Term(self.copy(), -1, 1)], operand=self.operand)

	def __invert__(self):
		return Expression([Term(self.copy(), 1, -1)], operand=self.operand)


class Product:

	def __init__(self, vector):
		if isinstance(vector, Filter):
			vector = [vector]
		self.vector = vector
		self.terms = None
		if not [x for x in self.vector if isinstance(x, Filter)]:
			self.terms = vector


class OpSum(Expr):

	def __new__(cls, *args, **kwargs):
		args_list = flatten_list(args)
		# args_list = args
		if [x for x in args_list if isinstance(x, op.IndexedArray)]:
			if len(args_list) == 1:
				e = super().__new__(cls, *args_list)
				return e
			new_args = []
			for arg in args_list:
				if isinstance(arg, op.IndexedArray):
					# params = get_sp_array_rep(arg)
					arg = OpSum(arg)
				new_args.append(arg)
			args_list = new_args
		return sp.Add(*args_list)

	def xreplace(self, rule):
		# import pdb
		# pdb.set_trace()
		new_args = [arg.xreplace(rule) for arg in self.args]
		return sp.Add(*flatten_list(new_args))

	def subs(self, *args, **kwargs):
		self.xreplace(args[0])
		return super().subs(self, *args, **kwargs)


# class Sum:
#
# 	def __init__(self, *args):
# 		self.vector = []
# 		self.terms = None
# 		for arg in args:
# 			if isinstance(arg, Filter):
# 				self.vector += [arg]
# 		if not [x for x in self.vector if isinstance(x, Filter)]:
# 			self.terms = self.vector
#
# 	def evaluate(self, context={}):
# 		# pdb.set_trace()
# 		new_vector = []
# 		for el in self.vector:
# 			if isinstance(el, Expr):
# 				el = evaluate_expression(el, context)
# 			if isinstance(el, pd.Series):
# 				new_vector += list(el.values)
# 			else:
# 				new_vector.append(el)
# 		# self.terms = new_vector
# 		# numbers = [x for x in new_vector if isinstance(x, int) or isinstance(x, float)]
# 		# terms = [Term(x, 1, 1) for x in new_vector if isinstance(x, Variable) or isinstance(x, Expression)]
# 		# return Expression(terms, ADD, constant=sum(numbers))
# 		from sympy import Add
# 		return Add(*new_vector)


class DotProduct:

	def __init__(self, *args, constant=None):
		from collections.abc import Iterable
		arrays = [arg for arg in args if isinstance(arg, Iterable)]
		if arrays:
			min_length = min([len(arg) for arg in arrays])
			max_length = max([len(arg) for arg in arrays])
			if min_length != max_length or min_length != 1 or [arg for arg in args if
			                                                   min_length < len(arg) < max_length]:
				raise Exception('Provides sequences should be of the same length')
			if [arg for arg in arrays if type(arg).__name__ not in ['list', 'Series']]:
				raise Exception('Given sequqnces should either be lists or pandas Series')
			if [arg for arg in arrays if type(arg).__name__ == 'list']:
				new_arrays = []
				for arg in [arg for arg in arrays]:
					if type(arg).__name__ == 'list':
						arg = pd.Series(arg)
					new_arrays.append(arg)
				arrays = new_arrays
		non_arrays = [arg for arg in args if not isinstance(arg, Iterable)]
		if non_arrays:
			new_non_arrays = []
			for x in non_arrays:
				new_non_arrays.append(pd.Series([x]))
			non_arrays = new_non_arrays
		args = arrays + non_arrays
		min_length = min([len(arg) for arg in args])
		max_length = max([len(arg) for arg in args])
		if min_length == 1:
			for single in [arg for arg in args if len(arg) == 1]:
				args.remove(single)
				single = single.repeat(max_length, ignore_index=True)
				args.append(single)
		self.arrays = args

	def evaluate(self):
		from operator import mul
		return 0

