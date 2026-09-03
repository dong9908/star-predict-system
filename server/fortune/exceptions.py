class FortuneAIError(Exception):
    """Base exception for fortune AI failures."""


class FortuneAIConfigurationError(FortuneAIError):
    pass


class FortuneAIAuthenticationError(FortuneAIError):
    pass


class FortuneAIRateLimitError(FortuneAIError):
    pass


class FortuneAITimeoutError(FortuneAIError):
    pass


class FortuneAIResponseError(FortuneAIError):
    pass


class FortuneAIUnavailableError(FortuneAIError):
    pass


class FortuneConversationError(Exception):
    """Base exception for fortune conversation failures."""


class FortuneConversationNotFoundError(FortuneConversationError):
    """Raised when a conversation is missing or belongs to another user."""
