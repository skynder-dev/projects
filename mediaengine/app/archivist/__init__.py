def _paths_never_raise_on_checks() -> None:
    """Python 3.11's Path.exists()/is_file()/is_dir() raise for some errors instead of answering False: a BitLocker-locked
    or failing card, an unreachable network drive, a folder without permission, a name too long. One such path in the
    Library made a page fail - and the start-up check that renders the pages then refused to start the app at all.
    In this app a path that cannot be read counts as not there (as os.path.exists does)."""
    import functools, pathlib
    if getattr(pathlib.Path, "_mediaengine_safe_checks", False):
        return

    def safe(fn):
        @functools.wraps(fn)
        def check(self, *a, **k):
            try:
                return fn(self, *a, **k)
            except (OSError, ValueError):
                return False
        return check
    for name in ("exists", "is_file", "is_dir"):
        setattr(pathlib.Path, name, safe(getattr(pathlib.Path, name)))
    pathlib.Path._mediaengine_safe_checks = True


_paths_never_raise_on_checks()

from .config import VERSION  # noqa: E402
