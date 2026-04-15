
ASCENDING = 'asc'
DESCENDING = 'desc'


LESSTHAN = '<='
EQUALTO = '=='
GREATERTHAN = '>='


BINARY = 'binary'
NON_NEGATIVE = 'non_negative'
INTEGER = 'integer'


_COMPARATOR_ALIASES = {
	'<=': '<=', 'lesser': '<=', 'lessthan': '<=', 'leq': '<=',
	'>=': '>=', 'greater': '>=', 'greaterthan': '>=', 'geq': '>=',
	'==': '==', '=': '==', 'equal': '==', 'equalto': '==', 'eq': '==',
}


def normalize_comparator(comp):
	"""Normalize a comparator alias to one of '<=', '>=', '=='."""
	if comp in ('<=', '>=', '=='):
		return comp
	key = comp.lower() if isinstance(comp, str) else comp
	result = _COMPARATOR_ALIASES.get(key)
	if result is None:
		raise ValueError(f"Unknown comparator: {comp!r}")
	return result
