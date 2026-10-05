"""
FakeSushiController: an in-memory stand-in for elkpy's SushiController.

Code written against guru (mappings, presets, sushi_client) targets elkpy's
async SushiController interface (``sc.audio_graph``, ``sc.parameters``,
``sc.system``, ...). Rather than mocking that interface ad hoc per test, this
module provides a small fake that actually implements it: it resolves real
track/processor names to ids and raises ``sushierrors.SushiNotFoundError`` for
unknown ones, exactly like the real thing.

Seed it from a real Sushi config file (see ``FakeSushiController.from_config``)
so tests fail when a mapping or preset references a track/plugin that doesn't
exist in that config - the same class of bug ``SushiClient._initialize_mappings``
guards against at runtime.

Parameter names/ids aren't in the static config (Sushi only learns them from
the plugin itself once loaded), so parameter ids are assigned the first time a
name is requested for a given processor. Pass ``parameters_by_processor`` if a
test needs to assert that only specific parameter names are valid.
"""

from __future__ import annotations

import itertools
import json
from pathlib import Path

from elkpy import sushierrors


class _IdAllocator:
    """Assigns a stable, unique id the first time a given key is seen."""

    def __init__(self, start: int = 0) -> None:
        self._counter = itertools.count(start)
        self._ids: dict[object, int] = {}

    def id_for(self, key: object) -> int:
        if key not in self._ids:
            self._ids[key] = next(self._counter)
        return self._ids[key]


class FakeAudioGraphController:
    def __init__(self, sushi: "FakeSushiController") -> None:
        self._sushi = sushi

    async def get_track_id(self, track_name: str) -> int:
        if track_name not in self._sushi.tracks:
            raise sushierrors.SushiNotFoundError(f"No such track: {track_name}")
        return self._sushi.tracks[track_name]

    async def get_processor_id(self, processor_name: str) -> int:
        if processor_name not in self._sushi.processors:
            raise sushierrors.SushiNotFoundError(f"No such processor: {processor_name}")
        return self._sushi.processors[processor_name]

    async def get_processor_bypass_state(self, processor_identifier: int) -> bool:
        return self._sushi.bypass_states.get(processor_identifier, False)

    async def set_processor_bypass_state(self, processor_identifier: int, value: bool) -> None:
        self._sushi.bypass_states[processor_identifier] = value
        self._sushi.calls.append(("set_processor_bypass_state", processor_identifier, value))

    async def get_processor_state(self, processor_identifier: int):
        return self._sushi.processor_states.get(processor_identifier)

    async def set_processor_state(self, processor_identifier: int, state) -> None:
        self._sushi.processor_states[processor_identifier] = state
        self._sushi.calls.append(("set_processor_state", processor_identifier, state))


class FakeParameterController:
    def __init__(self, sushi: "FakeSushiController") -> None:
        self._sushi = sushi

    async def get_parameter_id(self, processor_identifier: int, parameter_name: str) -> int:
        allowed = self._sushi.parameters_by_processor.get(processor_identifier)
        if allowed is not None and parameter_name not in allowed:
            raise sushierrors.SushiNotFoundError(
                f"No such parameter '{parameter_name}' on processor {processor_identifier}"
            )
        return self._sushi._parameter_ids.id_for((processor_identifier, parameter_name))

    async def get_parameter_value(self, processor_identifier: int, parameter_identifier: int) -> float:
        return self._sushi.parameter_values.get((processor_identifier, parameter_identifier), 0.0)

    async def set_parameter_value(self, processor_identifier: int, parameter_identifier: int, value: float) -> None:
        self._sushi.parameter_values[(processor_identifier, parameter_identifier)] = value
        self._sushi.calls.append(("set_parameter_value", processor_identifier, parameter_identifier, value))


class FakeSystemController:
    """Mirrors elkpy's SystemController, which is sync, not async."""

    def __init__(self, version: str = "1.0 (fake)") -> None:
        self._version = version

    def get_sushi_version(self) -> str:
        return self._version


class FakeNotificationController:
    def __init__(self) -> None:
        self.parameter_update_cb = None

    def subscribe_to_parameter_updates(self, cb) -> None:
        self.parameter_update_cb = cb


class FakeSushiController:
    def __init__(
        self,
        tracks: dict[str, int] | None = None,
        processors: dict[str, int] | None = None,
        parameters_by_processor: dict[int, set[str]] | None = None,
    ) -> None:
        self.tracks = tracks or {}
        self.processors = processors or {}
        self.parameters_by_processor = parameters_by_processor or {}

        self.bypass_states: dict[int, bool] = {}
        self.parameter_values: dict[tuple[int, int], float] = {}
        self.processor_states: dict[int, object] = {}
        self.calls: list[tuple] = []
        self._parameter_ids = _IdAllocator(start=1000)

        self.system = FakeSystemController()
        self.audio_graph = FakeAudioGraphController(self)
        self.parameters = FakeParameterController(self)
        self.notifications = FakeNotificationController()

    @classmethod
    def from_config(cls, config_path: Path | str) -> "FakeSushiController":
        """Seed tracks/processors from a real sushi_config.json."""
        config = json.loads(Path(config_path).read_text())
        tracks: dict[str, int] = {}
        processors: dict[str, int] = {}
        track_ids = itertools.count(0)
        processor_ids = itertools.count(0)
        for track in config.get("tracks", []):
            tracks[track["name"]] = next(track_ids)
            for plugin in track.get("plugins", []):
                processors[plugin["name"]] = next(processor_ids)
        return cls(tracks=tracks, processors=processors)
