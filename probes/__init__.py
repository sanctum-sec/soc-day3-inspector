from typing import Callable, List

_registry: List[Callable] = []
_slow_registry: List[Callable] = []  # probes that run once per hour (e.g. rate-limit test)


def register(fn: Callable) -> Callable:
    _registry.append(fn)
    return fn


def register_slow(fn: Callable) -> Callable:
    """Register a probe that should run at most once per hour."""
    _slow_registry.append(fn)
    return fn


def get_probes() -> List[Callable]:
    return list(_registry)


def get_slow_probes() -> List[Callable]:
    return list(_slow_registry)
