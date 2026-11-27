class PersistenceError(Exception):
    """Base exception for application persistence failures."""


class PersistenceValidationError(PersistenceError):
    """Raised when data cannot safely be stored in the database."""


class RecordNotFoundError(PersistenceError):
    """Raised when a required database record does not exist."""


class PersistenceConflictError(PersistenceError):
    """Raised when a persistence operation encounters a conflict."""
