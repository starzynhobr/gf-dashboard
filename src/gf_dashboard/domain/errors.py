class DomainError(Exception):
    """Base error for an invalid business operation."""


class ValidationError(DomainError):
    """Raised when a value does not satisfy a domain invariant."""


class NotFoundError(DomainError):
    """Raised when a required entity is absent from the current workspace."""


class ConflictError(DomainError):
    """Raised when an operation would violate uniqueness or state rules."""


class RuleNotConfirmedError(DomainError):
    """Raised when an informational rule is used for an automatic calculation."""
