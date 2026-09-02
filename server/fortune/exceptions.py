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
