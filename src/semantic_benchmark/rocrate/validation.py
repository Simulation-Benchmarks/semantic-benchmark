"""Validation helpers for RO-Crate benchmark outputs."""

from __future__ import annotations

import logging

from rocrate_validator import models, services

LOGGER = logging.getLogger(__name__)


def validate_rocrate(rocrate_path: str, profile: str) -> None:
    """Validate an RO-Crate folder against the specified profile."""
    settings = services.ValidationSettings(
        rocrate_uri=rocrate_path,
        profile_identifier=profile,
        requirement_severity=models.Severity.REQUIRED,
    )
    result = services.validate(settings)
    assert not result.has_issues(), "RO-Crate is invalid!\n" + "\n".join(
        f"Detected issue of severity {issue.severity.name} with check "
        f'"{issue.check.identifier}": {issue.message}'
        for issue in result.get_issues()
    )
    LOGGER.info("RO-Crate is valid.")
