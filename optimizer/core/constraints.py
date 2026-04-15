from optimizer.core.helper_functions import *
from datetime import datetime
import itertools
import pandas as pd


class Rule:

	def __init__(self, name, indeces, lhs, comparator, rhs, exclude=None, flexible=False, warn_for_flexing=True,
	             debug=False, talk_to_me=False):
		self.name = name
		self.indeces = indeces
		self.lhs = lhs
		self.comparator = comparator
		self.rhs = rhs
		if exclude is not None and not isinstance(exclude, op.OpSet):
			raise Exception('exclude parameter should be of type OpSet.')
		self.exclude = exclude
		self.flexible = flexible
		self.warn_for_flexing = warn_for_flexing
		self.debug = debug
		self.talk_to_me = talk_to_me
		self.constraints = []

	def create_constraint(self, context, index=None):
		if hasattr(self.lhs, 'evaluate'):
			lhs = self.lhs.evaluate(context)
		elif isinstance(self.lhs, Expr):
			lhs = eval_expr(self.lhs, context)
		else:
			lhs = self.lhs
		if hasattr(self.rhs, 'evaluate'):
			rhs = self.rhs.evaluate(context)
		elif isinstance(self.rhs, Expr):
			rhs = eval_expr(self.rhs, context)
		else:
			rhs = self.rhs
		return Constraint(rule=self, lhs=lhs, rhs=rhs, comparator=self.comparator)

	def create_constraints(self, base_context):
		if [x for x in self.indeces if x.values is None or len(x.values) == 0]:
			raise Exception('Ranges - {} do not have values'.format([x.refers_to for x in self.indeces if not x.refers_to.values]))
		if not self.indeces:
			# Scalar constraint (no indexing)
			self.constraints = pd.Series([self.create_constraint(dict(base_context), 0)], name=self.name)
			return
		values_list = [x.values for x in self.indeces]
		cp = list(itertools.product(*values_list))
		index_names = [x.name for x in self.indeces]
		self.constraints = pd.DataFrame(columns=index_names + [self.name])
		for index, combination in enumerate(cp):
			if self.exclude is not None and getattr(self.exclude, 'values', None) is not None \
					and is_excluded(dict(zip(self.indeces, list(combination))), self.exclude.values):
				continue
			context = dict(zip(self.indeces, list(combination)))
			context.update(base_context)
			self.constraints.loc[len(self.constraints)] = list(combination) + [self.create_constraint(context, index)]
		self.constraints = self.constraints.set_index(index_names)[self.name]


class Constraint:

	def __init__(self, rule, lhs, rhs, comparator):
		self.rule = rule
		self.lhs = lhs
		self.rhs = rhs
		self.comparator = comparator
		# Populated in Phase 2 by extract_linear_components when needed
		self.coeffs = None
		self.dvs = None
		self.rhs_value = None

	def type(self):
		return type(self.rule).__name__
