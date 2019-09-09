from optimizer.core.elements import *
import pandas as pd
from optimizer.core.helper_functions import *
from optimizer.core.expressions import Expression
from optimizer.core.constraints import Rule
import itertools
from sympy import IndexedBase, Array
import sympy as sp
# import optimizer as op


class Range(IndexedBase):

	def __new__(cls, name, index, data=None, *args, **kwargs):
		if data is not None and name not in data:
			raise Exception('{} not one of the columns in data DataFrame'.format(name))
		if name == index:
			raise Exception('Range name and index name cannot be the same')
		if data is not None:
			length = len(list(data[name].unique()))
			index_object = OpIndex(index, length)
		else:
			index_object = OpIndex(index, None)
		object = super().__new__(cls, name, shape=(index_object.length,))
		index_object.refers_to = object
		object.__init__(name, index_object, data, *args, **kwargs)
		return object, index_object

	def __init__(self, name, index, data=None, ranges=None, order=None):
		# import pdb
		# pdb.set_trace()
		self.index = index
		self.values = None
		if data is not None:
			self.set_values(data)
		# self.values.name = self.name
		# self.values.index.name = index.name
		if order:
			self.set_order(order)

	def set_values(self, data):
		values = list(pd.Series(data[self.name].unique()))
		self.values = values
		self.index.set_values(len(self.values))
		self._shape = sp.Tuple(*(len(self.values),))

	# def __getitem__(self, item, **kw_args):
	# 	if isinstance(item, Expr):
	# 		return Filter(self, item)
	# 	elif isinstance(item, slice):
	# 		if isinstance(item.start, Expr) or isinstance(item.start, Expr) or isinstance(item.start, Expr):
	# 			return Filter(self, item)
	# 		else:
	# 			return self.values.loc[item]
	# 	else:
	# 		return self.values.loc[item]

	def get_index(self, value):
		# import pdb
		# pdb.set_trace()
		if not self.values:
			raise Exception('Values for the Range are not set yet')
		return self.values.index(value)

	def set_order(self, order):
		if not self.values:
			print('Order for a Range cannot be set without values')
			return
		if type(order).__name__ == 'str':
			if order == op.ASCENDING:
				self.values = sorted(self.values)
			elif order == op.DESCENDING:
				self.values = sorted(self.values, reverse=True)
			return
		elif type(order).__name__ == 'list':
			if not [x for x in self.values if x not in order]:
				self.values = [x for x in order if x in self.values]
				return
		elif type(order).__name__ == 'dict':
			values = [x for x in order.keys()]
			if not [x for x in self.values if x not in values]:
				self.values = [x for x in values if x in self.values]
				return
		raise Exception('order should be of the minimum length as values')

	def filter(self, filter_by):
		# if not self.values:
		# 	raise Exception('Values for the Range are not set yet')
		if isinstance(filter_by, list) or callable(filter_by):
			return OpSet('{}_filtered_{}'.format(self.name, remove_chars(datetime.now())), [self.index], filter_by,
			             ref_range=True)
		else:
			raise Exception('filter_by should either be a function or an Iterable')


class OpSet(IndexedBase):

	def __new__(cls, name, indeces, values_ref=None, ref_range=False, *args, **kwargs):
		if [x for x in indeces if not isinstance(x, OpIndex)]:
			raise Exception('Indeces should be of type OpIndex')
		if isinstance(values_ref, list):
			length = len(values_ref)
			object = super().__new__(cls, name, shape=(length,))
		else:
			object = super().__new__(cls, name)
		return object

	def __init__(self, name, indeces, values_ref=None, ref_range=False):
		self.indeces = indeces
		self.length_var = sp.Symbol('{}_{}'.format(name, 'length'), integer=True)
		self.length = self.length_var
		self.ref_range = ref_range
		if values_ref is not None:
			self.set_values(values_ref, ref_range)

	def set_values(self, values_ref, ref_range=None):
		# import pdb
		# pdb.set_trace()
		if isinstance(values_ref, pd.DataFrame):
			values_ref = [tuple(x[1]) for x in values_ref.iterrows()]
		if ref_range is not None:
			self.ref_range = ref_range
		if callable(values_ref):
			self.values_ref = values_ref
		elif isinstance(values_ref, list) and len(values_ref) > 0:
			first_element = values_ref[0]
			if (isinstance(first_element, tuple) and len(self.indeces) == len(first_element)) or len(
					self.indeces) == 1:
				self.values_ref = pd.DataFrame(values_ref)
				if self.ref_range:
					self.values_ref = self.values_ref.rename(
						columns=dict(zip(range(len(self.indeces)), [x.refers_to.name for x in self.indeces])))
				else:
					self.values_ref = self.values_ref.rename(
						columns=dict(zip(range(len(self.indeces)), [x.name for x in self.indeces])))
				self.length = len(self.values_ref)
			else:
				raise Exception('The no of indeces in set and values do not match')
		else:
			raise Exception('values should be of type function or a list with length > 0')

	@property
	def super_set(self):
		if [x for x in self.indeces if x.values is None]:
			raise Exception('Indeces - {} do not have values yet.'.format([x for x in self.indeces if x.values is None]))
		if self.ref_range:
			values_list = [x.refers_to.values for x in self.indeces]
		else:
			values_list = [x.values for x in self.indeces]
		cp = list(itertools.product(*values_list))
		values = pd.DataFrame(cp)
		if self.ref_range:
			values = values.rename(columns=dict(zip(list(values.columns), [x.refers_to.name for x in self.indeces])))
		else:
			values = values.rename(columns=dict(zip(list(values.columns), [x.name for x in self.indeces])))
		return values
		# else:
		# 	return values[values.columns[0]]

	@property
	def values(self):
		import pdb
		pdb.set_trace()
		if self.values_ref is None:
			raise Exception('Values for set {} are not set yet'.format(self.name))
		if [x for x in self.indeces if x.values is None]:
			raise Exception(
				'Indeces - {} do not have values yet.'.format([x for x in self.indeces if x.values is None]))
		if isinstance(self.values_ref, pd.DataFrame):
			if self.ref_range:
				filtered_values = self.values_ref[
					sum([self.values_ref[ind.refers_to.name].isin(ind.refers_to.values) for ind in self.indeces]) ==
					len([self.values_ref[ind.refers_to.name].isin(ind.refers_to.values) for ind in self.indeces])]
			else:
				filtered_values = self.values_ref[
					sum([self.values_ref[ind.name].isin(ind.values) for ind in self.indeces]) ==
					len([self.values_ref[ind.name].isin(ind.values) for ind in self.indeces])]
		elif callable(self.values_ref):
			values = self.super_set
			if len(values.columns) == 1:
				filtered_values = values[values[values.columns[0]].apply(lambda s: self.values_ref(s))]
			else:
				filtered_values = values[values.apply(lambda s: self.values_ref(s), axis=1)]
		else:
			raise Exception('values of OpSet are neither function nor a DataFrame')
		if self.ref_range:
			for index, col in enumerate(filtered_values.columns):
				filtered_values[col] = filtered_values[col].apply(
					lambda val: self.indeces[index].refers_to.get_index(val))
			filtered_values = filtered_values.rename(columns=dict(zip(list(filtered_values.columns),
			                                                          [x.name for x in self.indeces])))
		self.length = len(filtered_values)
		return filtered_values.reset_index(drop=True)

	@property
	def array(self):
		return [x[1] for x in self.values.iterrows()]


class Values(IndexedBase):

	def __new__(cls, name, indeces, data=None, values_col=None, *args, **kwargs):
		return super().__new__(cls, name, tuple([x.length for x in indeces]))

	def __init__(self, name, indeces, data=None, values_col=None):
		self.indeces = indeces
		self.values = None
		self.array = None
		if data is not None:
			if not values_col:
				raise Exception('Need values column')
			else:
				self.set_values(data, values_col)

	def set_values(self, data, values_col):
		if values_col not in data:
			raise Exception('{} not in data DataFrame'.format(values_col))
		if [r for r in self.indeces if r.refers_to.name not in data]:
			raise Exception('Indeces - {} not present in data'.format([r for r in self.indeces if r.name not in data]))
		if [x for x in self.indeces if not x.values]:
			for r in [x.refers_to for x in self.indeces if not x.values]:
				r.set_values(data=data)
			if [x for x in self.indeces if not x.values]:
				raise Exception('Ranges - {} do not have values'.format([x.refers_to for x in
			                                                         self.indeces if not x.refers_to.values]))
		df = data[[r.refers_to.name for r in self.indeces] + [values_col]]
		values_list = [x.refers_to.values for x in self.indeces]
		cp = list(itertools.product(*values_list))
		values = pd.DataFrame(cp)
		rename_dict = {}
		for i, col in enumerate(values.columns):
			rename_dict.update({col: self.indeces[i].refers_to.name})
		values = values.rename(columns=rename_dict)
		values = values.merge(df, how='left', on=[x.refers_to.name for x in self.indeces])
		if [col for col in df.columns if col in [r.name for r in self.indeces]]:
			raise Exception('Indeces names and range names cannot overlap - {}'.
			                format([col for col in df.columns if col in [r.name for r in self.indeces]]))
		for index in self.indeces:
			range_df = pd.DataFrame()
			range_df[index.refers_to.name] = index.refers_to.values
			range_df[index.name] = index.values
			values = values.merge(range_df, on=index.refers_to.name)
		self.values = values[[r.name for r in self.indeces] + [values_col]]
		self.values = self.values[values_col].fillna(0)
		self.values = values.set_index([r.name for r in self.indeces])[values_col].sort_index()
		self.array = OpArray(list(self.values), shape=tuple([x.length for x in self.indeces]))
		self._shape = sp.Tuple(*[x.length for x in self.indeces])

	def get_values(self, indeces):
		indeces = [slice(x.lower, x.upper, None) if isinstance(x, ArrayIndex) else x for x in indeces]
		if [x for x in indeces if isinstance(x, list)]:
			new_indeces = [[x] if not isinstance(x, list) else x for x in indeces]
			cp = list(itertools.product(*new_indeces))
			return OpArray([self.array[tuple(x)] for x in cp])
		else:
			return self.array[tuple(indeces)]

	def __getitem__(self, indeces, **kw_args):
		# import pdb
		# pdb.set_trace()
		return get_item(indeces, self, **kw_args)


class OpVariables(IndexedBase):

	def __new__(cls, indeces, data=None, prefix=None, suffix=None, *args, **kwargs):
		prefix = (prefix + '_') if prefix else ''
		suffix = (suffix + '_') if suffix else ''
		try:
			range_name = '_'.join([r.refers_to.name for r in indeces])
		except Exception as e:
			import pdb
			pdb.set_trace()
			raise Exception(e)
		name = '{}{}{}'.format(prefix, range_name, suffix)
		# if all([x.length for x in indeces]):
		return super().__new__(cls, name, tuple([x.length for x in indeces]))
		# else:
		# 	return super().__new__(cls, name)

	def __init__(self, indeces, data=None, prefix=None, suffix=None, integer=False, min=None, max=None, equal=None):
		if [r for r in indeces if not isinstance(r, OpIndex)]:
			raise Exception('Type of indeces should be OpIndex')
		self.indeces = indeces
		self.ranges = [x.refers_to for x in self.indeces]
		self.prefix = (prefix + '_') if prefix else ''
		self.suffix = (suffix + '_') if suffix else ''
		# self.symbol = OpSymbol(self.name, self)
		self.integer = integer
		self.min = min
		self.max = max
		self.equal = equal
		self.rules = []
		self.values = None
		self.array = None
		if isinstance(self.min, Expression):
			self.rules.append(Rule(name='min_of_{}_rule'.format(self.name)))
		if isinstance(self.max, Expression):
			self.rules.append(Rule(name='max_of_{}_rule'.format(self.name)))
		if isinstance(self.equal, Expression):
			self.rules.append(Rule(name='{}_equalto_rule'.format(self.name)))
		if data is not None:
			self.set_values(data)

	def create_variable_for_row(self, row):
		strings = ([self.prefix] if self.prefix else []) + [self.indeces[idx].refers_to.values[c] for idx, c in
		                                          enumerate(row)] + ([self.suffix] if self.suffix else [])
		return self.create_variable('_'.join([str(x) for x in strings]))

	def get_values(self, indeces):
		indeces = [slice(x.lower, x.upper, None) if isinstance(x, ArrayIndex) else x for x in indeces]
		if [x for x in indeces if isinstance(x, list)]:
			new_indeces = [[x] if not isinstance(x, list) else x for x in indeces]
			cp = list(itertools.product(*new_indeces))
			return OpArray([self.array[tuple(x)] for x in cp])
		else:
			return self.array[tuple(indeces)]

	def set_values(self, data):
		if self.values is None:
			self.create(data)
		if not all([x.refers_to.name in data or x.name in data for x in self.indeces]):
			raise Exception('All indeces are not present in the given data')
		df = pd.DataFrame()
		for index in self.indeces:
			if index.name in data:
				df[index.name] = data[index.name]
			else:
				range_df = pd.DataFrame()
				range_df[index.refers_to.name] = index.refers_to.values
				range_df[index.name] = index.values
				df[index.name] = data.merge(range_df, how='left', on=index.refers_to.name)[index.name]
		df['ones'] = 1
		if [col for col in df.columns if (col in [r.name for r in self.indeces] and col in [r.name for r in self.ranges])]:
			raise Exception('Indeces names and range names cannot overlap - {}'.
			                format([col for col in df.columns if col in [r.name for r in self.indeces]]))
		self.values = self.values.reset_index().merge(df, how='left', on=[x.name for x in self.indeces])
		self.values.loc[self.values['ones'].isna(), self.name] = 0
		self.values = self.values.set_index([r.name for r in self.indeces])[self.name].sort_index()
		self.array = OpArray(list(self.values), shape=tuple([x.length for x in self.indeces]))
		self._shape = sp.Tuple(*[x.length for x in self.indeces])

	def __getitem__(self, indeces, **kw_args):
		import pdb
		pdb.set_trace()
		return get_item(indeces, self, **kw_args)

	def create(self, data=None):
		if [x for x in self.indeces if not x.values]:
			for r in [x.refers_to for x in self.indeces if not x.values]:
				r.set_values(data=data)
			if [x for x in self.indeces if not x.values]:
				raise Exception('Ranges - {} do not have values'.format([x.refers_to for x in
			                                                         self.indeces if not x.refers_to.values]))
		values_list = [x.values for x in self.indeces]
		cp = list(itertools.product(*values_list))
		values = pd.DataFrame(cp)
		rename_dict = {}
		for i, col in enumerate(values.columns):
			rename_dict.update({col: self.indeces[i].name})
		values = values.rename(columns=rename_dict)
		values[self.name] = values.apply(lambda s: self.create_variable_for_row(s), axis=1)
		# for index in indeces:
		# 	self.values = self.values.merge(index.refers_to.values.reset_index(), on=index.refers_to.name)
		self.values = values
		self.values = self.values.set_index([r.name for r in self.indeces])[self.name].sort_index()
		self.array = OpArray(list(self.values), shape=tuple([x.length for x in self.indeces]))

	def create_variable(self, name):
		name = remove_chars(name)
		variable = Variable(name)
		variable.integer = self.integer
		if self.min is not None:
			if type(self.min).__name__ in ['float', 'int']:
				variable.min = self.min
		if self.max is not None:
			if type(self.max).__name__ in ['float', 'int']:
				variable.max = self.max
		if self.equal is not None:
			if type(self.equal).__name__ in ['float', 'int']:
				variable.value = self.equal
		return variable


class IntegerVariables(OpVariables):

	def __init__(self, indeces, data=None, prefix=None, suffix=None, min=None, max=None, equal=None):
		super().__init__(indeces, data=data, prefix=prefix, suffix=suffix, min=min, max=max, integer=True, equal=equal)


class BinaryVariables(OpVariables):

	def __init__(self, indeces, data=None, prefix=None, suffix=None, equal=None):
		super().__init__(indeces, data=data, prefix=prefix, suffix=suffix, min=0, max=1, integer=True, equal=equal)


class NonNegativeVariables(OpVariables):

	def __init__(self, indeces, data=None, prefix=None, suffix=None, max=None, equal=None, integer=False):
		super().__init__(indeces, data=data, prefix=prefix, suffix=suffix, min=0, max=max, integer=integer, equal=equal)

