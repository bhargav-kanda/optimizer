from pulp import *
import datetime
import pandas as pd


class PulpProblem:

	def __init__(self, optimizer):
		pulp.LpSolverDefault.msg = 1
		if max:
			self.problem = pulp.LpProblem(optimizer.name, pulp.LpMaximize)
		else:
			self.problem = pulp.LpProblem(optimizer.name, pulp.LpMinimize)

	def create_objective_function(self, optimizer):
		self.problem += total_tvr - sum_of_slacks
		print(datetime.datetime.now().isoformat() + ' Objective Function')
		for constraint in optimizer.constraints:
			self.problem += constraint

	def add_constraint(self, weights, dvs, rhs, comparator, rule):
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
				self.problem += lhs <= rhs
			elif comparator == 'greater':
				self.problem += lhs >= rhs
			elif comparator == 'equal':
				self.problem += lhs == rhs
			else:
				raise Exception('Incorrect value for comparator')
		elif comparator in ['equal', 'greater'] and rhs > 0:
			import pdb
			pdb.set_trace()
			raise Exception(
				'Conflict in {} rule. Rhs is {} but lhs is 0. Could not find dvs - {}'.format(rule, rhs, dvs))

	def solve(self, max_lp_execution_in_sec=6000, ncpus=1):
		if not self.constraints:
			self.formulate()
		self.opt_problem = self.create_lp_problem()
		self.opt_problem.solve()
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

