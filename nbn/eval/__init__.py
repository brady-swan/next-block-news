"""Isolated, read-only model evaluation support for Plan 0057.

Nothing in this package is imported by the production worker.  The evaluator accepts only
evaluation-specific credentials and owns a separate artifact directory and SQLite ledger.
"""

from .core import EvaluationError

__all__ = ["EvaluationError"]
