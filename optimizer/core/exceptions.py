"""Specific exception types used throughout the optimizer package."""


class OptimizerError(Exception):
	"""Base exception for all optimizer errors."""


class InfeasibleError(OptimizerError):
	"""The problem has no feasible solution."""


class UnboundedError(OptimizerError):
	"""The problem is unbounded."""


class DataBindingError(OptimizerError):
	"""Failed to bind data to a range, variable, or value."""


class LinearizationError(OptimizerError, ValueError):
	"""Expression is not linear and cannot be decomposed into coefficients."""


class ConflictError(OptimizerError):
	"""One or more constraint conflicts were detected."""

	def __init__(self, message, conflicts=None):
		super().__init__(message)
		self.conflicts = conflicts or []

	def __str__(self):
		base = super().__str__()
		if not self.conflicts:
			return base
		lines = [base, "Conflicts:"]
		for c in self.conflicts:
			lines.append(f"  - {c.description}")
		return "\n".join(lines)
