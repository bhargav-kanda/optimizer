from optimizer.core.helper_functions import *
from datetime import datetime
import itertools
import numpy as np
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

	def set_applicability(self, include, exclude=None):
		if type(include).__name__ == 'dict':
			self.apply_for['include'].append(include)
		elif type(include).__name__ == 'list':
			self.apply_for['include'] += include
		else:
			raise Exception("'include' parameter should be either dict or list")
		if exclude is not None:
			self.apply_for['exclude'] = exclude
		return self

	def create_applicability_space(self, data):
		space = {}
		dict = self.apply_for['include_dict']
		for key in dict:
			if type(dict[key]).__name__ == 'function':
				values = dict[key]()
			elif len(dict[key]) == 0:
				values = data[key].tolist()
			else:
				values = dict[key]
			space.update({key: values})
		return space

	def create_constraint(self, context, index=None):
		# pdb.set_trace()
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
		# if index:
		# 	print('Created {} constraint'.format(index))
		return Constraint(rule=self, lhs=lhs, rhs=rhs, comparator=self.comparator)

	def create_constraints(self, base_context):
		# if self.debug:
		import pdb
		pdb.set_trace()
		if [x for x in self.indeces if x.values is None or len(x.values) == 0]:
			raise Exception('Ranges - {} do not have values'.format([x.refers_to for x in self.indeces if not x.refers_to.values]))
		values_list = [x.values for x in self.indeces]
		cp = list(itertools.product(*values_list))
		index_names = [x.name for x in self.indeces]
		self.constraints = pd.DataFrame(columns=index_names + [self.name])
		start_time = datetime.now()
		print('Starting creation of {} constraints for {} rule at {}'.format(len(cp), self.name, start_time))
		for index, combination in enumerate(cp):
			if self.exclude.values and is_excluded(dict(zip(self.indeces, list(combination))), self.exclude.values):
				continue
			context = dict(zip(self.indeces, list(combination)))
			context.update(base_context)
			self.constraints.loc[len(self.constraints)] = list(combination) + [self.create_constraint(context, index)]
		# for index in self.indeces:
		# 	self.values = self.values.merge(index.refers_to.values.reset_index(), on=index.refers_to.name)
		self.constraints = self.constraints.set_index(index_names)[self.name]
		end_time = datetime.now()
		time_taken = (end_time-start_time).seconds
		print('Finished creation of {} constraints for {} rule in {} seconds'.format(len(cp), self.name, time_taken))


class Constraint:

	def __init__(self, rule, lhs, rhs, comparator):
		self.rule = rule
		self.lhs = lhs
		self.rhs = rhs
		self.comparator = comparator

	def type(self):
		return type(self.rule).__name__

	def evaluate_for_fixed_rules(self):
		weights, dvs, rhs, comparator, rule = self.coeffs, self.dvs, self.rhs, self.comparator, self.rule
		original_dv_count = len(dvs)
		lhs = 0
		dvs_str = [str(dv) for dv in dvs]
		affected_fixed_constraints = []
		if comparator in ['lesser', 'equal']:  # Original constraint is max constraint
			# for f_index, fixed_constraint in enumerate(globals.fixed_constraints + globals.business_constraints):     # Only min constraints can conflict with max
			# 	if fixed_constraint.comparator == 'lesser' or f_index == c_index:
			# 		continue
			for fixed_constraint in [fc for fc in globals.fixed_constraints if
			                         fc.comparator != 'lesser']:  # Only min constraints can conflict with max
				fixed_constraint_dvs_str = [str(dv) for dv in fixed_constraint.dvs]
				different_dvs = [dv for dv in fixed_constraint_dvs_str if dv not in dvs_str]
				if not different_dvs:  # all dvs are present in both
					common_indices = [dvs_str.index(fixed_dv) for fixed_dv in fixed_constraint_dvs_str]
					fixed_weights = [weight for index, weight in enumerate(weights) if index in common_indices]
					ratio = fixed_weights[0] / fixed_constraint.coeffs[0]
					if fixed_weights == [x for x in (ratio * np.asarray(fixed_constraint.coeffs))]:
						dvs = [dv for index, dv in enumerate(dvs) if index not in common_indices]
						weights = [weight for index, weight in enumerate(weights) if index not in common_indices]
						dvs_str = [str(dv) for dv in dvs]
						lhs += (ratio * fixed_constraint.rhs)
						affected_fixed_constraints.append(fixed_constraint)
					else:
						if lhs + sum(sorted(fixed_weights)[:fixed_constraint.rhs]) > rhs:
							affected_fixed_constraints.append(fixed_constraint)
							print('Conflict between standard constraint "{}" and fixed constraints - {}'.
							      format(rule,
							             ['{} for {}'.format(c.rule, c.dvs) for c in affected_fixed_constraints]))
							return False
					if lhs + sum([w for w in weights if w < 0]) <= rhs:
						return True
					else:
						import pdb
						pdb.set_trace()
						print('Conflict between standard constraint "{}" and fixed constraints - {}'.
						      format(rule,
						             ['{} for {}'.format(c.rule, c.dvs) for c in affected_fixed_constraints]))
						return False
			if lhs == rhs and len(dvs) > 0 and min(weights) > 0:  # No negative weights should be present
				removable_dvs = dvs
				message = 'Removing {} dvs because of {} rule and fixed constraints - {}.'.format(len(removable_dvs),
				                                                                                  rule,
				                                                                                  ['{} for {}'.format(
					                                                                                  c.rule,
					                                                                                  c.dvs) for c in
				                                                                                   affected_fixed_constraints])
				prune_dv_space(removable_dvs, message)
			return True
		if comparator in ['greater', 'equal']:  # Original constraint is min constraint
			# for f_index, fixed_constraint in enumerate(globals.fixed_constraints + globals.business_constraints):     # Only min constraints can conflict with max
			# 	if fixed_constraint.comparator == 'greater' or f_index == c_index:
			# 		continue
			for fixed_constraint in [fc for fc in globals.fixed_constraints if
			                         fc.comparator != 'greater']:  # Only max constraints can conflict with min
				fixed_constraint_dvs_str = [str(dv) for dv in fixed_constraint.dvs]
				different_dvs = [dv for dv in fixed_constraint_dvs_str if dv not in dvs_str]
				if not different_dvs:  # all dvs are present in both
					common_indices = [dvs_str.index(fixed_dv) for fixed_dv in fixed_constraint_dvs_str]
					fixed_weights = [weight for index, weight in enumerate(weights) if index in common_indices]
					ratio = fixed_weights[0] / fixed_constraint.coeffs[0]
					if fixed_weights == [x for x in (ratio * np.asarray(fixed_constraint.coeffs))]:
						dvs = [dv for index, dv in enumerate(dvs) if index not in common_indices]
						dvs_str = [str(dv) for dv in dvs]
						weights = [weight for index, weight in enumerate(weights) if index not in common_indices]
						lhs += (ratio * fixed_constraint.rhs)
						affected_fixed_constraints.append(fixed_constraint)
			if lhs + sum([w for w in weights if w > 0]) >= rhs:
				return True
			else:
				import pdb
				pdb.set_trace()
				print('Conflict between standard constraint "{}" and fixed constraints - {}'.
				      format(rule, ['{} for {}'.format(c.rule, c.dvs) for c in affected_fixed_constraints]))
				return False
		return True

	def prune(self, all_constraints, c_index):
		(weights, dvs, rhs, comparator, rule) = (self.coeffs, self.dvs, self.rhs,
		                                         self.comparator, self.rule)
		rule_type = self.type()
		dvs_str = [str(dv) for dv in self.dvs]
		affected_fixed_constraints = []
		for o_index, other_constraint in enumerate(all_constraints):
			if other_constraint.comparator != 'equal' or c_index == o_index:
				continue
			other_constraint_dvs_str = [str(dv) for dv in other_constraint.dvs]
			different_dvs = [dv for dv in other_constraint_dvs_str if dv not in dvs_str]
			if not different_dvs:
				common_indices = [dvs_str.index(fixed_dv) for fixed_dv in other_constraint_dvs_str]
				fixed_weights = [weight for index, weight in enumerate(weights) if index in common_indices]
				ratio = fixed_weights[0] / other_constraint.coeffs[0]
				if fixed_weights == [x for x in (ratio * np.asarray(other_constraint.coeffs))]:
					dvs = [dv for index, dv in enumerate(dvs) if index not in common_indices]
					weights = [weight for index, weight in enumerate(weights) if index not in common_indices]
					dvs_str = [str(dv) for dv in dvs]
					rhs -= (ratio * other_constraint.rhs)
					if rule_type == 'ContinuityRule':  # Change dummy coefficient also correspondingly
						if 'dummy' in dvs[-1]:
							weights[-1] = rhs
						else:
							print('Could not find the location of dummy variable')
					affected_fixed_constraints.append(other_constraint)
				else:
					if comparator in ['lesser', 'equal'] and \
							(self.rhs - rhs + sum(sorted(fixed_weights)[:other_constraint.rhs])) > \
							self.rhs:
						affected_fixed_constraints.append(other_constraint)
						import pdb
						pdb.set_trace()
						print('Conflict between constraint "{}" and constraints - {}'.
						      format(rule,
						             ['{} for {}'.format(c.rule, c.dvs) for c in affected_fixed_constraints]))
						return False
				if rhs <= 0 and (len(weights) == 0 or min(weights) >= 0):
					if comparator in ['lesser', 'equal']:
						if rhs == 0:
							if len(dvs) > 0:
								message = 'Removing {} dvs because of {} rule and fixed constraints - {}.'.format(
									len(dvs), rule,
									['{} for {}'.format(c.rule, c.dvs) for c in affected_fixed_constraints])
								prune_dv_space(dvs, message=message)
							# print('Dropping {} constraint for {}'.format(rule, dvs))
							return None
						else:
							import pdb
							pdb.set_trace()
							raise Exception('Conflict between constraint "{}" and constraints - {}'.
							                format(rule, ['{} for {}'.format(c.rule, c.dvs) for c in
							                              affected_fixed_constraints]))
					else:
						# print('Dropping {} constraint for {}'.format(rule, dvs))
						return None
		# if rhs < constraint.rhs:
		# print('Reduced rhs for {} rule from {} to {} because of {} constraints.'.format(rule, constraint.rhs, rhs,
		#                                                                             affected_fixed_constraints))
		(self.coeffs, self.dvs, self.rhs, self.comparator,
		 self.rule) = (weights, dvs, rhs, comparator, rule)
		return self

