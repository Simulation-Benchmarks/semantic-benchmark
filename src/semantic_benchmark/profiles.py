"""Read project profiles for aggregate benchmark RO-Crates."""

from pathlib import Path

import yaml

from .semantics.models import AggregateProfile


def load_aggregate_profile(profile_file: str | Path) -> AggregateProfile:
    """Return a typed profile from the exact YAML file supplied."""
    path = Path(profile_file)
    with path.open(encoding="utf-8") as stream:
        profile = yaml.safe_load(stream)
    if not isinstance(profile, dict):
        raise ValueError(f"Aggregate profile must be a YAML mapping: {path}")
    try:
        values = {
            "software_name": profile["software-name"],
            "software_version": profile["software-version"],
            "software_url": profile["software-url"],
            "crate_license": profile["crate-license"],
            "crate_name": profile["crate-name"],
            "crate_description": profile["crate-description"],
            "agent_name": profile["agent-name"],
            "agent_orcid": profile["agent-orcid"],
        }
    except (KeyError, TypeError) as exc:
        raise ValueError(f"Invalid aggregate profile {path}: missing {exc}") from exc
    if any(not isinstance(value, str) or not value.strip() for value in values.values()):
        raise ValueError(f"Aggregate profile contains empty or non-text metadata: {path}")
    return AggregateProfile(**values)


def build_subcrate_args(profile_file: str | Path) -> list[str]:
    """Build Snakemake RO-Crate reporter arguments from a YAML file."""
    path = Path(profile_file)
    with path.open(encoding="utf-8") as stream:
        profile = yaml.safe_load(stream)
    if not isinstance(profile, dict) or not profile:
        raise ValueError(f"Subcrate profile must be a nonempty YAML mapping: {path}")
    args = ["--reporter", "rocrate"]
    for key, value in profile.items():
        if not isinstance(key, str) or not key.startswith("report-rocrate-"):
            raise ValueError(f"Invalid RO-Crate reporter option in {path}: {key}")
        if not isinstance(value, str) or not value.strip():
            raise ValueError(f"RO-Crate reporter values must be nonempty strings: {path}")
        args.extend([f"--{key}", value])
    return args
