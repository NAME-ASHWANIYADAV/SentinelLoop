"""Shared error types. Role violations in any service subclass PermissionDenied so every interface (API, UI, CLI)
can report them consistently (HTTP 403) without parsing messages."""


class PermissionDenied(ValueError):
    pass
