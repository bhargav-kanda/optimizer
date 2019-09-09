from sympy import oo
from optimizer.core.helper_functions import *
from datetime import datetime
import sympy as sp
from sympy.core.compatibility import is_sequence
import itertools


class ArrayIndex(sp.Idx):

	def __new__(cls, *args, **kwargs):
		return super().__new__(cls, *args, **kwargs)


class OpIndex(sp.Idx):

	def __new__(cls, name, range=None, reference=None, *args, **kwargs):
		return super().__new__(cls, name, range)

	def __init__(self, name, range=None, reference=None):
		self.refers_to = reference
		self.length_var = sp.Symbol('{}_{}'.format(self.name, 'length'), integer=True)
		self.length = self.length_var

	def __index__(self):
		return 1

	@property
	def min(self):
		return self.lower

	@property
	def max(self):
		return self.upper

	@property
	def values(self):
		if self.lower is not None and self.upper is not None:
			if all([self.lower.is_number, self.upper.is_number]):
				return list(range(self.lower, self.upper+1))
		return None

	def set_values(self, length):
		Warning('Index values are being set. Make sure the values are right.')
		label, range = list(map(sp.sympify, (self.label, length)))
		if is_sequence(range):
			if len(range) != 2:
				raise ValueError(sp.filldedent("""
			            Idx range tuple must have length 2, but got %s""" % len(range)))
			for bound in range:
				if bound.is_integer is False:
					raise TypeError("Idx object requires integer bounds.")
			args = label, sp.Tuple(*range)
		elif isinstance(range, Expr):
			if not (range.is_integer or range is sp.S.Infinity):
				raise TypeError("Idx object requires an integer dimension.")
			args = label, sp.Tuple(0, range - 1)
		elif range:
			raise TypeError(sp.filldedent("""
					        The range must be an ordered iterable or
					        integer SymPy expression."""))
		else:
			args = label,
		self.range = (length, )
		self._args = args
		self.length = length

	def filter(self, filter_by):
		# if self.values:
		if isinstance(filter_by, list) or isinstance(filter_by, function):
			# values = [x for x in self.values if filter_by(x)]
			return op.OpSet('{}_filtered_{}'.format(self.name, remove_chars(datetime.now())), self, filter_by)
		else:
			raise Exception('filter_by should either be a function or an Iterable')
		# else:
		# 	raise Exception('values for the index {} are not set yet'.format(self.name))


class OpSymbol(sp.Symbol):

	def __new__(cls, name, *args, **kwargs):
		return super().__new__(cls, name)

	def __init__(self, name, reference):
		self.refers_to = reference

	def evaluate(self, context):
		return evaluate_symbol(self, context)

	def filter(self, values):
		return 0

	@property
	def values(self):
		return self.refers_to.values.index.values.tolist()


class Variable(sp.Symbol):

	def __new__(cls, name, *args, **kwargs):
		return super().__new__(cls, name)

	def __init__(self, name, min=-oo, max=oo, integer=False):
		self.min = min
		self.max = max
		self.integer = integer
		self.value = None


class Filter(sp.Symbol):

	def __new__(cls, series, *args, **kwargs):
		return super().__new__(cls, '{}_{}'.format(series.name, str(datetime.now()).replace(' ', '')
		                                           .replace('-', '').replace('.', '').replace(':', '_')))

	def __init__(self, series, indeces):
		self.data = series
		self.indeces = indeces

	def subs(self, context={}):
		# pdb.set_trace()
		values = self.data.values
		indeces = self.indeces
		if isinstance(indeces, tuple):
			new_indeces = []
			for index in indeces:
				index = evaluate_index(index, context)
				new_indeces.append(index)
			values.sort_index(inplace=True)
			return values.loc[tuple(new_indeces)]
		elif values.index.nlevels == 1:
			if isinstance(indeces, Expr):
				indeces = evaluate_expression(indeces, context)
			elif isinstance(indeces, slice):
				indeces = evaluate_slice(indeces, context)
			values.sort_index(inplace=True)
			return values.loc[indeces]
		elif isinstance(indeces, int):
			return values.iloc[indeces]
		else:
			raise Exception('Error in indexing of {} with {}'.format(self.data.name, self.indeces))


class OpArray(sp.Array):

	def __new__(cls, iterable, shape=None, **kwargs):
		return super().__new__(cls, iterable, shape=shape, **kwargs)

	def __getitem__(self, index):
		# import pdb
		# pdb.set_trace()
		if not isinstance(index, tuple):
			return sp.Array.__getitem__(self, index=index)
		indeces = index
		if [x for x in indeces if isinstance(x, Iterable)]:
			new_indeces = [[x] if not isinstance(x, Iterable) else x for x in indeces]
			cp = list(itertools.product(*new_indeces))
			return OpArray([self[combination] for combination in cp])
		indeces = [get_slice(x) if isinstance(x, ArrayIndex) else x for x in indeces]
		return sp.Array.__getitem__(self, index=tuple(indeces))


class IndexedArray(sp.Indexed):

	def __new__(cls, *args, **kwargs):
		return super().__new__(cls, *args, **kwargs)

	def xreplace(self, rule):
		# import pdb
		# pdb.set_trace()
		if isinstance(self.base, sp.Array):
			values = self.base
			base_indeces = None
		else:
			if self.base in rule:
				values = rule[self.base]
			else:
				values = None
			base_indeces = self.base.indeces
		if values is None:
			new_indeces = []
			for index in self.indices:
				if is_sympy_object(index):
					index = index.xreplace(rule)
				elif isinstance(index, Iterable):
					index = [x.xreplace(rule) if is_sympy_object(x) else x for x in index]
				new_indeces.append(index)
			return return_indexed(self.base, new_indeces)
		else:
			indeces = self.indices
			if [x for x in indeces if isinstance(x, Iterable)]:
				new_indeces = [[x] if not isinstance(x, Iterable) else x for x in indeces]
				cp = list(itertools.product(*new_indeces))
				return OpArray([values[combination].xreplace(rule) for combination in cp]).xreplace(rule)
			indeces = [get_slice(x, rule, base_indeces[ind] if base_indeces else None)
			           if isinstance(x, ArrayIndex) else x.xreplace(rule) if is_sympy_object(x) else x
			           for ind, x in enumerate(indeces)]
			return values[tuple(indeces)]

	def subs(self, *args, **kwargs):
		self.xreplace(args[0])
		return super().subs(self, *args, **kwargs)

