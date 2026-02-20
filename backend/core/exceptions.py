"""
Custom Exceptions
Application-specific exception hierarchy
"""


class QuorumException(Exception):
    """Base exception for all Quorum errors"""
    pass


class DatabaseError(QuorumException):
    """Database operation errors"""
    pass


class ParserError(QuorumException):
    """Log parsing errors"""
    pass


class ValidationError(QuorumException):
    """Input validation errors"""
    pass


class SecurityError(QuorumException):
    """Security and cryptographic errors"""
    pass


class AIEngineError(QuorumException):
    """AI/ML operation errors"""
    pass


class ConfigurationError(QuorumException):
    """Configuration errors"""
    pass


class NetworkError(QuorumException):
    """Network operation errors"""
    pass


class UpdateError(QuorumException):
    """Update system errors"""
    pass