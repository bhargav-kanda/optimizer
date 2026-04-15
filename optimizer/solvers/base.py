"""Base abstractions for solver backends."""
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, Optional

import pandas as pd


class SolverStatus(Enum):
	OPTIMAL = "optimal"
	INFEASIBLE = "infeasible"
	UNBOUNDED = "unbounded"
	ERROR = "error"
	NOT_SOLVED = "not_solved"


@dataclass
class SolverResult:
	"""Result of a solver run."""
	status: SolverStatus
	objective_value: Optional[float] = None
	variables: Optional[Dict[str, float]] = None
	solve_time: float = 0.0
	solver_name: str = ""
	raw: object = field(default=None, repr=False)

	def to_dataframe(self, parse_variable_names: bool = False, separator: str = "_") -> pd.DataFrame:
		"""Return results as a pandas DataFrame with columns 'variable' and 'value'.

		Args:
			parse_variable_names: If True, split variable names by ``separator`` and add
				columns index_0, index_1, ... for each component.
			separator: Separator to use when splitting variable names.
		"""
		if not self.variables:
			return pd.DataFrame(columns=['variable', 'value'])
		df = pd.DataFrame(
			[(name, val) for name, val in self.variables.items()],
			columns=['variable', 'value'],
		)
		if parse_variable_names:
			parts = df['variable'].astype(str).str.split(separator, expand=True)
			for i in range(parts.shape[1]):
				df[f'index_{i}'] = parts[i]
		return df


class SolverBase(ABC):
	"""Abstract base class for solver backends."""

	name: str = "base"

	@abstractmethod
	def solve(self, problem, **kwargs) -> SolverResult:
		"""Solve the given problem and return a SolverResult."""
		raise NotImplementedError
