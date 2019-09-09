
class Solution:

	def __init__(self, dvs, values):
		self.dvs = dvs
		self.values = values


class InitialSolution(Solution):

	def __init__(self, dvs, values, cost_to_change):
		self.cost_to_change = cost_to_change
		super().__init__(dvs, values)


class PartialSolution(Solution):

	def __init__(self, dvs, values):
		super().__init__(dvs, values)

