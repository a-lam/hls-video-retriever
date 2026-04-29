import importlib.util
import pathlib
import urllib.parse

import config


def _root_domain(hostname: str) -> str:
    parts = hostname.split(".")
    return ".".join(parts[-2:]) if len(parts) >= 2 else hostname


def _load_profile(name: str) -> dict | None:
    root = pathlib.Path(__file__).parent
    path = (root / f"{name}.py") if name == "default" else (root / "site-profiles" / f"{name}.py")
    if not path.exists():
        return None
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return {k: v for k, v in vars(mod).items() if not k.startswith("_")}


if config.URL:
    _hostname = urllib.parse.urlparse(config.URL).hostname or ""
    _file_stem = _root_domain(_hostname).replace(".", "_")
    _profile = _load_profile(_file_stem) or _load_profile("default")
    if _profile is None:
        raise ValueError(
            f"No site profile found for {_hostname!r} and no default.py fallback. "
            f"Add site-profiles/{_file_stem}.py or default.py."
        )
    config.__dict__.update(_profile)
    config.IS_LISTING_MODE = bool(_profile.get("LISTING_PAGE_SELECTOR", ""))
else:
    config.IS_LISTING_MODE = False
