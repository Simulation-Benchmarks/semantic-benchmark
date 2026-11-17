"""Read project profiles for main benchmark RO-Crates."""

from pathlib import Path

import yaml

from .semantics.models import MainProfile, ProfilePerson


def _profile_person(value: object, path: Path, field: str) -> ProfilePerson:
    if not isinstance(value, dict) or set(value) != {"name", "orcid"}:
        raise ValueError(f"{field} must contain name and orcid in {path}")
    if any(not isinstance(value[key], str) or not value[key].strip() for key in ("name", "orcid")):
        raise ValueError(f"{field} must contain nonempty text in {path}")
    return ProfilePerson(name=value["name"], orcid=value["orcid"])


def load_main_profile(profile_file: str | Path) -> MainProfile:
    """Return a typed profile from the exact YAML file supplied."""
    path = Path(profile_file)
    with path.open(encoding="utf-8") as stream:
        profile = yaml.safe_load(stream)
    if not isinstance(profile, dict):
        raise ValueError(f"Main profile must be a YAML mapping: {path}")
    try:
        values = {
            "software_name": profile["software-name"],
            "software_version": profile["software-version"],
            "software_url": profile["software-url"],
            "crate_license": profile["crate-license"],
            "crate_name": profile["crate-name"],
            "crate_description": profile["crate-description"],
        }
    except (KeyError, TypeError) as exc:
        raise ValueError(f"Invalid main profile {path}: missing {exc}") from exc
    if any(not isinstance(value, str) or not value.strip() for value in values.values()):
        raise ValueError(f"Main profile contains empty or non-text metadata: {path}")
    authors = profile.get("authors")
    if not isinstance(authors, list) or not authors:
        raise ValueError(f"authors must be a nonempty list in {path}")
    creator = _profile_person(profile.get("creator"), path, "creator")
    return MainProfile(
        **values,
        authors=tuple(_profile_person(person, path, f"authors[{index}]") for index, person in enumerate(authors)),
        creator=creator,
    )


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
