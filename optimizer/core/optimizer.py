import datetime
from optimizer.sm_input.sm_functions import *
import optimizer.sm_input.sm_globals as globals
import optimizer as op
import sympy as sp


class OpFormulation:

	def __init__(self, name, max=True):
		self.name = name
		self._objective = None
		self.data = None
		self._rules = []
		self.max = max
		self._prob = None
		self._context = {}
		self._variables = []
		self._values = []
		self._ranges = []
		self._sets = []
		# if objective_function is not None:
		# 	self.set_objective(objective_function)

	def set_objective(self, obj):
		self._objective = obj

	@property
	def objective(self):
		return self._objective

	@property
	def rules(self):
		return self._rules

	@property
	def prob(self):
		return self._prob

	@property
	def context(self):
		return self._context

	@property
	def values(self):
		return self._values

	@property
	def variables(self):
		return self._variables

	@property
	def ranges(self):
		return self._ranges

	@property
	def sets(self):
		return self._sets

	def create_range(self, name, index, data=None, ranges=None, order=None):
		r, i = op.Range(name, index, data, ranges, order)
		self._ranges.append(r)
		return r, i

	def create_set(self, name, indeces=None, ranges=None, values=None):
		if indeces is None and ranges is None:
			raise Exception('One of indeces or ranges should be non null.')
		ref_range = False
		if indeces is None:
			indeces = [r.index for r in ranges]
			ref_range = True
		s = op.OpSet(name, indeces, values_ref=values, ref_range=ref_range)
		self._sets.append(s)
		return s

	def create_variables(self, indeces, data=None, prefix=None, suffix=None, type=None,
	                     integer=False, min=-sp.oo, max=sp.oo, equal=None):
		if type == op.BINARY:
			variables = op.OpVariables(indeces, data=data, prefix=prefix, suffix=suffix, min=0, max=1, integer=True, equal=equal)
		elif type == op.NON_NEGATIVE:
			variables = op.OpVariables(indeces, data=data, prefix=prefix, suffix=suffix, min=0, max=max, integer=True, equal=equal)
		else:
			variables = op.OpVariables(indeces, data, prefix, suffix, integer, min, max, equal)
		self._variables.append(variables)
		return variables

	def create_values(self, name, indeces, data=None, values_col=None):
		values = op.Values(name, indeces, data=data, values_col=values_col)
		self._values.append(values)
		return values

	def add_rule(self, name, indeces, lhs, comparator, rhs, flexible=False, warn_for_flexing=True,
	             debug=False, talk_to_me=False):
		rule = op.Rule(name, indeces, lhs, comparator, rhs, flexible, warn_for_flexing, debug, talk_to_me)
		self._rules.append(rule)
		return rule

	def remove_rule(self, index):
		self._rules.pop(index)

	def _create_objective(self):
		return op.eval_expr(self.objective, self.context)

	def create_problem(self, data):
		prob = OpProblem(name=self.name, formulation=self, max=self.max)
		for variable in self.variables:
			variable.set_values(data=data)
			self.context.update({variable: variable.array})
		for r in self.ranges:
			self.context.update({r.index.length_var: r.index.length})
		if [x for x in self.values if x.values is None]:
			raise Exception('Some values in the formulation - {} are not set yet.'.format(
				[x for x in self.values if x.values is None]))
		for rule in self.rules:
			rule.create_constraints(self.context)
			prob.add_contraints(list(rule.constraints))
		prob.set_objective_function(self._create_objective())
		self._prob = prob
		return self


class OpProblem:

	def __init__(self, name, formulation, max=True, partial_solution=None, initial_solution=None):
		self.name = name
		self.objective = None
		self.max = max
		self.partial_solution = partial_solution
		self.initial_solution = initial_solution
		self.optimal = None
		self.formulated = False
		self.constraints = []

	def set_objective_function(self, exp):
		self.objective = exp
		return self

	def add_contraints(self, constraints):
		self.constraints += constraints
		return self

	def prune_constraints(self):
		new_constraints = []
		for index, constraint in enumerate(self.constraints):
			new_constraint = constraint.prune(self.constraints, index)
			if new_constraint:
				new_constraints.append(new_constraint)
		self.constraints = new_constraints

	def check_conflicts(self):
		conflict_counter = 0
		for index, constraint in enumerate(self.constraints):
			result = constraint.evaluate_for_fixed_rules()
			if not result:
				conflict_counter += 1
		if conflict_counter:
			raise Exception('{} conflicts found! Stopping.'.format(conflict_counter))

	def create_objective_function(self):
		total_tvr = ''
		for row in globals.dv_df.iterrows():
			row = row[1]
			formula = row.TVR * row.DV
			total_tvr += formula
		all_days = get_all_of('dates')
		break_points = get_all_of('dates', {'week_day': ['Saturday']})
		if break_points[0] > all_days[0]:
			break_points = [all_days[0]] + break_points
		if break_points[-1] < all_days[-1]:
			break_points.append(all_days[-1] + 1)
		sum_of_slacks = ''
		constraints = []
		for i, start in enumerate(break_points[:-1]):
			var1, var2 = define_tvr_slacks(break_points[i], break_points[i + 1] - 1)
			sum_of_slacks += var1 + var2
			constraints.append(create_uniform_tvr_constraint(break_points[i], break_points[i + 1] - 1, var1, var2))
		self.prob += total_tvr - sum_of_slacks
		print(datetime.datetime.now().isoformat() + ' Objective Function')
		for constraint in constraints:
			self.prob += constraint

	def create_constraints_from_rules(self):
		if 'ContinuityRule' in [type(rule).__name__ for rule in self.rules]:
			globals.reference_slot = get_reference_slot()
		for rule in self.rules:
			constraints = rule.create_constraints()
			self.constraints += constraints
			print('Added {} constraints for "{}" rule'.format(len(constraints), rule.name))

	def add_lp_constraint(self, weights, dvs, rhs, comparator, rule):
		dvs_str = [str(dv) for dv in dvs]
		filter = (self.data['DV'].astype(str).isin(dvs_str))
		if filter.sum() > 0:
			existing_dvs = self.data.loc[filter, 'DV']
			indices = [index for index, dv_str in enumerate(dvs_str) if dv_str in existing_dvs.astype(str).tolist()]
			try:
				lhs = pulp.lpSum([weights[index] * dvs[index] for index in indices])
			except:
				raise Exception('Could not create lp ')
			if comparator == 'lesser':
				self.prob += lhs <= rhs
			elif comparator == 'greater':
				self.prob += lhs >= rhs
			elif comparator == 'equal':
				self.prob += lhs == rhs
			else:
				raise Exception('Incorrect value for comparator')
		elif comparator in ['equal', 'greater'] and rhs > 0:
			import pdb
			pdb.set_trace()
			raise Exception(
				'Conflict in {} rule. Rhs is {} but lhs is 0. Could not find dvs - {}'.format(rule, rhs, dvs))

	def create_lp_problem(self):
		self.create_objective_function()
		for constraint in self.constraints:
			self.add_lp_constraint(constraint.coeffs, constraint.dvs, constraint.rhs,
			                       constraint.comparator, constraint.rule)

	def formulate(self):
		try:
			self.create_constraints_from_rules()
			self.prune_constraints()
			self.check_conflicts()
			self.create_lp_problem()
			self.formulated = True
			return True
		except Exception as e:
			return False

	def save(self, input_path):
		if not self.constraints or not self.formulated:
			self.formulate()
		self.prob.writeLP(input_path + '/lp_output/' + self.name + '.lp')

	def create_pulp_problem(self):
		pulp_prob = PulpProb(self)
		return pulp_prob

	def solve(self, max_lp_execution_in_sec=6000, ncpus=1):
		if not self.constraints or not self.formulated:
			self.formulate()
		print(datetime.datetime.now().isoformat() + ' LP Start')
		self.prob.solve(PULP_CBC_CMD(msg=True, maxSeconds=max_lp_execution_in_sec, threads=ncpus, keepFiles=1))
		print(datetime.datetime.now().isoformat() + ' LP End')
		print(datetime.datetime.now().isoformat() + ' LP Status: %s' % LpStatus[self.prob.status])
		print(datetime.datetime.now().isoformat() + ' LP Optimal value: %.2f' % pulp.value(self.prob.objective))
		# reorder results
		variable_name = []
		variable_value = []
		for v in self.prob.variables():
			variable_name.append(v.name)
			variable_value.append(v.varValue)
		self.optimal = pd.DataFrame({'DV': variable_name, 'value': variable_value})
		return self.optimal

