"""Validation helpers for RO-Crate benchmark outputs."""

from __future__ import annotations

import logging

from rocrate_validator import models, services

LOGGER = logging.getLogger(__name__)


def validate_rocrate(rocrate_path: str, profile: str) -> None:
    """Log validation results for an RO-Crate folder against the specified profile."""
    try:
        settings = services.ValidationSettings(
            rocrate_uri=rocrate_path,
            profile_identifier=profile,
            requirement_severity=models.Severity.REQUIRED,
        )
        result = services.validate(settings)
        if result.has_issues():
            for issue in result.get_issues():
                LOGGER.warning(
                    'RO-Crate validation issue of severity %s with check "%s": %s',
                    issue.severity.name,
                    issue.check.identifier,
                    issue.message,
                )
        else:
            LOGGER.info("RO-Crate is valid.")
    except Exception:
        LOGGER.exception("RO-Crate validation failed for %s", rocrate_path)
