"""
Security utilities for IQ-MCP.

Provides input validation and security checks to prevent common vulnerabilities.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    pass


def validate_file_path(
    path: str | Path,
    allowed_base: str | Path | None = None,
    must_exist: bool = False,
) -> Path:
    """
    Validate and resolve a file path to prevent path traversal attacks.

    Args:
        path: The path to validate
        allowed_base: Optional base directory - path must be within this directory
        must_exist: If True, raises ValueError if path doesn't exist

    Returns:
        Resolved absolute Path object

    Raises:
        ValueError: If path is invalid, outside allowed_base, or doesn't exist when required

    Example:
        >>> validate_file_path("/data/memory.jsonl", allowed_base="/data")
        PosixPath('/data/memory.jsonl')

        >>> validate_file_path("../../etc/passwd", allowed_base="/data")
        ValueError: Path is outside allowed directory
    """
    try:
        resolved_path = Path(path).resolve()
    except (OSError, RuntimeError) as e:
        raise ValueError(f"Invalid path '{path}': {e}") from e

    # Check if path exists if required
    if must_exist and not resolved_path.exists():
        raise ValueError(f"Path does not exist: {resolved_path}")

    # Validate against allowed base directory
    if allowed_base:
        allowed_base_resolved = Path(allowed_base).resolve()
        try:
            # Check if the path is within the allowed base
            resolved_path.relative_to(allowed_base_resolved)
        except ValueError as e:
            raise ValueError(
                f"Path '{resolved_path}' is outside allowed directory '{allowed_base_resolved}'"
            ) from e

    return resolved_path


def validate_api_key(api_key: str | None) -> bool:
    """
    Validate API key format.

    Args:
        api_key: The API key to validate

    Returns:
        True if valid, False otherwise

    Note:
        Currently checks for:
        - Non-empty string
        - Expected prefix (iqmcp-sk- or iqmcp_sk_)
        - Minimum length (20 chars after prefix)
    """
    if not api_key:
        return False

    if not isinstance(api_key, str):
        return False

    # Check for expected prefix
    valid_prefixes = ["iqmcp-sk-", "iqmcp_sk_"]
    has_valid_prefix = any(api_key.startswith(prefix) for prefix in valid_prefixes)

    if not has_valid_prefix:
        return False

    # Check minimum length (prefix + 20 chars)
    min_length = len("iqmcp-sk-") + 20
    if len(api_key) < min_length:
        return False

    return True


def check_production_security() -> list[str]:
    """
    Check for common production security misconfigurations.

    Returns:
        List of security warnings (empty if all checks pass)

    Example:
        >>> warnings = check_production_security()
        >>> if warnings:
        ...     for warning in warnings:
        ...         print(f"⚠️  {warning}")
    """
    warnings = []

    # Check 1: Authentication configured
    api_key = os.getenv("IQ_API_KEY")
    if not api_key:
        warnings.append("IQ_API_KEY not set - server will run without authentication!")
    elif not validate_api_key(api_key):
        warnings.append("IQ_API_KEY format appears invalid - check your configuration")

    # Check 2: Debug mode in production
    debug = os.getenv("IQ_DEBUG", "false").lower() == "true"
    if debug:
        warnings.append("IQ_DEBUG is enabled - disable for production!")

    # Check 3: Supabase credentials
    supabase_enabled = os.getenv("IQ_ENABLE_SUPABASE", "false").lower() == "true"
    if supabase_enabled:
        if not os.getenv("IQ_SUPABASE_URL"):
            warnings.append("Supabase enabled but IQ_SUPABASE_URL not set")
        if not os.getenv("IQ_SUPABASE_KEY"):
            warnings.append("Supabase enabled but IQ_SUPABASE_KEY not set")

    return warnings


__all__ = ["validate_file_path", "validate_api_key", "check_production_security"]
