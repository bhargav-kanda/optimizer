from sympy import Expr, Number
import sympy as sp
from collections.abc import Iterable
from datetime import datetime
import optimizer as op
from sympy.core.compatibility import is_sequence


def is_cleanslice(s):
	if isinstance(s, slice):
		start, stop, step = s.start, s.stop, s.step
		if not isinstance(start, Expr) and not isinstance(stop, Expr) and not isinstance(step, Expr):
			return True
		else:
			return False
	else:
		return False


def evaluate_symbol(symbol, context):
	if symbol.name in context:
		return context[symbol.name]
	else:
		raise Exception('Given context does not have the value for Symbol - {}'.format(symbol.name))


def evaluate_expression(expr, context):
	# import pdb
	# pdb.set_trace()
	for e in [x for x in list(expr.atoms()) if not isinstance(x, Number)]:
		if e not in context:
			context.update({e: e.subs(context)})
	value = expr.subs(context)
	# expr_str = str(expr)
	# new_expr_str = str(expr)
	# sorted_keys = sorted(list(context.keys()), key=len, reverse=True)
	# for key in sorted_keys:
	# 	if key in expr_str:
	# 		new_expr_str = new_expr_str.replace(key, 'context["{}"]'.format(key))
	# 		expr_str = expr_str.replace(key, '')
	# value = eval(new_expr_str)
	# value_expr = Expr(value)
	# if len(list(value_expr.atoms())) > 1:
	# 	raise Exception('The giving context does not have these symbols - {} used in the expression'.format(expr.atoms()))
	return value


def evaluate_slice(s, context):
	start, stop, step = s.start, s.stop, s.step
	if isinstance(start, Expr):
		start = int(evaluate_expression(start, context))
	if isinstance(stop, Expr):
		stop = int(evaluate_expression(stop, context))
	if isinstance(step, Expr):
		step = int(evaluate_expression(step, context))
	return slice(start, stop, step)


def evaluate_index(index, context):
	if isinstance(index, slice):
		index = evaluate_slice(index, context)
	elif isinstance(index, Expr):
		index = int(evaluate_expression(index, context))
	elif isinstance(index, list):
		new_index = []
		for ind in index:
			ind = evaluate_index(ind, context)
			new_index.append(ind)
		index = new_index
	return index


def get_max(element):
	from optimizer.core.elements import Variable
	from optimizer.core.expressions import Expression
	if isinstance(element, Variable):
		return element.max
	elif isinstance(element, Expression):
		return element.max_value
	elif isinstance(element, int) or isinstance(element, float):
		return element
	else:
		return None


def get_min(element):
	from optimizer.core.elements import Variable
	from optimizer.core.expressions import Expression
	if isinstance(element, Variable):
		return element.min
	elif isinstance(element, Expression):
		return element.min_value
	elif isinstance(element, int) or isinstance(element, float):
		return element
	else:
		return None


def is_number(number):
	if isinstance(number, int):
		return True
	if 'sympy.' in type(number).__module__:
		return number.is_number
	return False


def is_computable(index):
	if isinstance(index, list):
		return all([is_number(x) for x in index])
	if isinstance(index, op.ArrayIndex):
		return all([is_number(index.lower), is_number(index.upper)])
	return is_number(index)


def is_sympy_object(obj):
	return 'sympy' in type(obj).__module__ or any(['sympy' in c.__module__ for c in type(obj).__bases__])


def return_indexed(base, indeces, **kw_args):
	if is_sequence(indeces):
		# Special case needed because M[*my_tuple] is a syntax error.
		if base.shape and len(base.shape) != len(indeces):
			raise Exception("Rank mismatch.")
		return op.IndexedArray(base, *indeces, **kw_args)
	else:
		if base.shape and len(base.shape) != 1:
			raise sp.Indexed("Rank mismatch.")
		return op.IndexedArray(base, indeces, **kw_args)


def get_slice(array_index, rule={}, base_index=None):
	# import pdb
	# pdb.set_trace()
	stop = None
	if base_index is not None and hasattr(array_index.upper, 'name') and '_length' in array_index.upper.name:
		if is_number(base_index):
			stop = base_index
		elif array_index.upper.name == '{}_{}'.format(base_index.name, 'length') and isinstance(base_index.length, int):
			stop = base_index.length
	if stop is None:
		stop = array_index.upper.xreplace(rule)
	return slice(array_index.lower.xreplace(rule), stop, None)


def flatten_list(args):
	if not isinstance(args, Iterable):
		args = [args]
	new_list = []
	for x in args:
		if isinstance(x, Iterable):
			new_list += flatten_list(list(x))
		# elif isinstance(x, sp.Array):
		# 	new_list += flatten_list(list(x))
		else:
			new_list.append(x)
	return new_list


def remove_chars(string, chars=[' ', '-', ',', '.', ':']):
	string = str(string)
	for char in chars:
		string = string.replace(char, '')
	return string


def get_sp_array_rep(indexed_array):
	base = indexed_array.base
	indeces = indexed_array.indices
	new_indeces = []
	index_bounds = []
	for index in indeces:
		index_bound = None
		if is_sympy_object(index):
			if isinstance(index, op.ArrayIndex):
				index_bound = [(index, index.lower, index.upper)]
			elif [x for x in index._args if isinstance(x, op.ArrayIndex)]:
				index_bound = [(x, x.lower, x.upper) for x in index._args if isinstance(x, op.ArrayIndex)]
		new_indeces.append(index)
		if index_bound:
			index_bounds += index_bound
	return tuple([base[tuple(new_indeces)]] + index_bounds)


def eval_expr(expr, context):
	# import pdb
	# pdb.set_trace()
	sub_exprs = list(expr.expr_free_symbols)
	if len(sub_exprs) == 1 and sub_exprs[0] == expr:
		return expr.xreplace(context)
	new_context = context.copy()
	for e in sub_exprs:
		new_context.update({e: eval_expr(e, context)})
	val = expr.xreplace(new_context)
	return val


def is_excluded(combination_dict, exclude_df):
	return 0


def clean_indeces(indeces, obj):
	new_indeces = []
	for i, index in enumerate(indeces):
		if isinstance(index, slice):
			if index.step not in [1, None]:
				raise Exception('Supports slices with only step 1. Generate a list otherwise.')
			start = index.start if index.start is not None else 0
			stop = index.stop if index.stop is not None else obj.indeces[i].length
			dummy_index = op.ArrayIndex('di_{}'.format(remove_chars(datetime.now()))
			                         , range=(start, stop))
			index = dummy_index
		elif isinstance(index, Iterable):
			index_list = op.OpArray(index)
			dummy_index = sp.Idx('di_' + remove_chars(datetime.now()), range=len(index))
			index = index_list[dummy_index]
		elif isinstance(index, op.OpSet):
			dummy_index = sp.Idx('di_' + remove_chars(datetime.now()), range=index.length)
			index = index[dummy_index]
		# else:
		# 	raise Exception('Unrecognized format for index.')
		new_indeces.append(index)
	return new_indeces


def get_item(indeces, obj, **kw_args):
	if not isinstance(indeces, tuple):
		indeces = (indeces,)
	if len(indeces) != len(obj.indeces):
		if [x for x in indeces if isinstance(x, op.OpSet)]:
			set_indeces = [x for x in indeces if isinstance(x, op.OpSet)]
			other_indeces = [x for x in obj.indeces if not any([x in ind.indeces for ind in set_indeces])]
			if len(other_indeces) != len([x for x in indeces if not isinstance(x, op.OpSet)]):
				raise Exception('Expected indexers for {} are {} (no of ranges)'.format(obj.name, len(obj.indeces)))
		else:
			raise Exception('Expected indexers for {} are {} (no of ranges)'.format(obj.name, len(obj.indeces)))
	if [x for x in indeces if isinstance(x, slice) or isinstance(x, Iterable) or isinstance(x, op.OpSet)]:
		indeces = clean_indeces(indeces, obj)
	if obj.array:
		if all([is_computable(index) for index in indeces]):
			return obj.get_values(indeces)
	return return_indexed(obj, indeces, **kw_args)


