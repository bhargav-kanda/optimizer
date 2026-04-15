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

	def add_rule(self, name, indeces, lhs, comparator, rhs, exclude=None, flexible=False, warn_for_flexing=True,
	             debug=False, talk_to_me=False):
		rule = op.Rule(name, indeces, lhs, comparator, rhs, exclude, flexible, warn_for_flexing, debug, talk_to_me)
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

	def add_constraints(self, constraints):
		self.constraints += constraints
		return self

	# Historical alias (kept for backward compatibility)
	add_contraints = add_constraints

	def check_conflicts(self, mode='lite'):
		"""Check constraints for conflicts and raise if any errors are found.

		Args:
			mode: 'lite' (fast heuristic checks, no solver) or 'pro' (runs a
				feasibility LP to catch interactions across multiple constraints).

		Returns:
			List of Conflict objects (including warnings).

		Raises:
			ConflictError if any conflicts have severity=ERROR.
		"""
		from optimizer.core.conflict_detection import (
			detect_conflicts, detect_conflicts_lp, ConflictSeverity,
		)
		from optimizer.core.exceptions import ConflictError
		if mode == 'pro':
			conflicts = detect_conflicts_lp(self.constraints)
		elif mode == 'lite':
			conflicts = detect_conflicts(self.constraints)
		else:
			raise ValueError(f"Unknown conflict mode: {mode!r}. Use 'lite' or 'pro'.")
		errors = [c for c in conflicts if c.severity == ConflictSeverity.ERROR]
		if errors:
			raise ConflictError(
				f"{len(errors)} constraint conflict(s) detected",
				conflicts=errors,
			)
		return conflicts

	def prune_constraints(self):
		"""Remove constraints that are implied by equality constraints and variable fixings.

		A constraint is considered redundant if it's trivially satisfied once
		variables fixed by equality constraints (or PartialSolution) are substituted.

		Returns:
			Number of constraints pruned.
		"""
		from optimizer.core.pruning import prune_constraints as _prune
		before = len(self.constraints)
		self.constraints = _prune(self.constraints)
		return before - len(self.constraints)

	def solve(self, solver=None, **kwargs):
		"""Solve the optimization problem using the given solver backend.

		Args:
			solver: A SolverBase instance. If None, defaults to PulpSolver.
			**kwargs: Additional keyword arguments passed to solver.solve().

		Returns:
			SolverResult with status, objective value, and variable assignments.
		"""
		if solver is None:
			from optimizer.solvers import PulpSolver
			solver = PulpSolver()
		self.result = solver.solve(self, **kwargs)
		return self.result

	@property
	def status(self):
		return self.result.status if getattr(self, 'result', None) else None

	@property
	def objective_value(self):
		return self.result.objective_value if getattr(self, 'result', None) else None

	def get_result_dataframe(self, **kwargs):
		if getattr(self, 'result', None) is None:
			return None
		return self.result.to_dataframe(**kwargs)

