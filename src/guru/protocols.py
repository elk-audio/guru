from __future__ import annotations

from typing import Awaitable, Callable, NotRequired, Protocol, TypedDict

from elkpy.sushicontroller import SushiController


# --- Callable type aliases ---

Preprocessor = Callable[[float], float]
ControlCallback = Callable[[float], Awaitable[None]]


# --- Event payload TypedDicts ---

class SushiPluginEvent(TypedDict):
    track_id: int
    plugin_id: int
    param_id: int
    value: float


class SushiTrackEvent(TypedDict):
    track_id: int
    param_id: int
    value: float


class PluginBypassEvent(TypedDict):
    plugin_id: int


# --- Preset initial_state TypedDict ---

class PluginState(TypedDict):
    processor: str
    parameters: NotRequired[dict[str, float]]
    bypassed: NotRequired[bool]


# --- Mapping Protocols ---

class Mapping(Protocol):
    """Structural interface every mapping class must satisfy."""
    controller_name: str | None

    async def init(self, sc: SushiController) -> None: ...


class ValueMapping(Mapping, Protocol):
    """A mapping that tracks a current numeric value (encoders, analog inputs)."""
    value: float
    preprocessor: Preprocessor | None
    parameter_label: str
    track_id: int
    param_id: int
