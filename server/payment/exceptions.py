class PaymentError(Exception):
    """Base exception for payment failures."""


class PaymentConfigurationError(PaymentError):
    """Raised when required KakaoPay configuration is invalid or missing."""


class PaymentAuthenticationError(PaymentError):
    """Raised when KakaoPay rejects the configured credentials."""


class PaymentProviderUnavailableError(PaymentError):
    """Raised when KakaoPay cannot be reached or is temporarily unavailable."""


class PaymentProviderResponseError(PaymentError):
    """Raised when KakaoPay returns an invalid or unexpected response."""


class PaymentReadyError(PaymentError):
    """Raised when a payment-ready request fails."""


class PaymentApprovalError(PaymentError):
    """Raised when a payment approval request fails."""


class PaymentCancellationError(PaymentError):
    """Raised when an approved payment cannot be cancelled."""


class PaymentNotFoundError(PaymentError):
    """Raised when a payment is missing or belongs to another user."""


class PaymentInvalidStateError(PaymentError):
    """Raised when a payment operation is not allowed in its current state."""


class PaymentAmountMismatchError(PaymentError):
    """Raised when the approved amount differs from the server-side price."""


class PaymentConflictError(PaymentError):
    """Raised when an order or transaction has already been processed."""
