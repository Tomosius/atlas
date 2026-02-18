"""Error codes and result helpers for Atlas operations."""


class AtlasError(Exception):
    """Base exception for Atlas errors. Used for truly exceptional cases only."""

    def __init__(self, code: str, detail: str = "") -> None:
        self.code = code
        self.detail = detail
        super().__init__(f"{code}: {detail}" if detail else code)


ERROR_CODES: dict[str, str] = {
    "NOT_INITIALIZED": "Project not initialized — run atlas init first",
    "ALREADY_INITIALIZED": "Project already initialized — use force=True to reinit",
    "MODULE_NOT_FOUND": "Module not found in registry",
    "MODULE_ALREADY_INSTALLED": "Module is already installed",
    "MODULE_NOT_INSTALLED": "Module is not installed",
    "MODULE_CONFLICT": "Module conflicts with an installed module",
    "MODULE_REQUIRED": "Cannot remove — another module requires it",
    "DETECTION_FAILED": "Could not detect project type",
    "CONFIG_PARSE_ERROR": "Failed to parse configuration file",
    "WAREHOUSE_NOT_FOUND": "Module warehouse directory not found",
    "INVALID_ARGUMENT": "Invalid argument provided",
    "REGISTRY_NOT_FOUND": "Module registry file not found",
}


def ok_result(**kwargs: object) -> dict[str, object]:
    """Build a success result dict."""
    return {"ok": True, **kwargs}


def error_result(code: str, detail: str = "", **kwargs: object) -> dict[str, object]:
    """Build an error result dict."""
    message = ERROR_CODES.get(code, code)
    if detail:
        message = f"{message}: {detail}"
    return {"ok": False, "error": code, "detail": message, **kwargs}
