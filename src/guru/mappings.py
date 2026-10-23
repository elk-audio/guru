"""
User configuration file for mapping hardware controllers to Sushi parameters.

Define your mappings here using the Mapping and SwitchMapping classes from presets.py.
The controller_name should match the name field from PotState or SwitchState
returned by RefreshAllStates().
"""

import asyncio
import time
from elkpy.sushicontroller import SushiController
from . import observer
from .protocols import (
    ControlCallback,
    Mapping,
    Preprocessor,
    PluginBypassEvent,
    SushiPluginEvent,
    SushiTrackEvent,
)
import logging

logger = logging.getLogger("MAPPINGS")


class MappingMode:
    """This wraps around a list of mappings to provide more data"""

    def __init__(
        self,
        mappings: list,
        mode: int = 0,
    ) -> None:
        self.mode = mode
        self.mappings = mappings

    async def init(self, sc: SushiController) -> None:
        for m in self.mappings:
            await m.init(sc)


class Control:
    """This mapping triggers an arbitrary callback. Useful for switching modes or emitting a specific signal"""

    def __init__(self, controller_name: str, cb: ControlCallback | None):
        self.controller_name = controller_name
        self.callback = cb

    def __repr__(self) -> str:
        return "Control mapping on %s -> cb: %s" % (self.controller_name, self.callback)

    async def init(self, sc) -> None: ...


class MultiSwitch:
    """Assigns a mapping to a combination of switches when they are pressed at the same time"""

    def __init__(self, controller_names: list, mapping) -> None:
        self.controller_names = controller_names
        self.controller_name = controller_names
        self.mapping = mapping

    async def init(self, sc) -> None:
        await self.mapping.init(sc)


class TrackParameterMapping:
    """Mapping to a track parameter (gain, pan, ...)"""

    def __init__(
        self,
        track_name: str,
        parameter_name: str,
        controller_name: str | None = None,
        preprocessor: Preprocessor | None = None,
        parameter_label: str | None = None,
    ) -> None:
        self.track_name = track_name
        self.parameter_name = parameter_name
        self.controller_name = controller_name
        self.preprocessor = preprocessor
        self.parameter_label = parameter_label if parameter_label else parameter_name

    async def init(self, sc: SushiController) -> None:
        self.track_id = await sc.audio_graph.get_track_id(self.track_name)
        self.param_id = await sc.parameters.get_parameter_id(
            self.track_id, self.parameter_name
        )
        self.value = await sc.parameters.get_parameter_value(
            self.track_id, self.param_id
        )

    def __repr__(self) -> str:
        return "TrackParameterMapping: track=%s, parameter=%s, controller_name=%s" % (
            self.track_name,
            self.parameter_name,
            self.controller_name,
        )


class PluginParameterMapping:
    """Mapping to a plugin parameter"""

    def __init__(
        self,
        track_name: str,
        plugin_name: str,
        parameter_name: str,
        controller_name: str | None = None,
        preprocessor: Preprocessor | None = None,
        parameter_label: str | None = None,
    ):
        self.track_name = track_name
        self.plugin_name = plugin_name
        self.parameter_name = parameter_name
        self.controller_name = controller_name
        self.preprocessor = preprocessor
        self.parameter_label = parameter_label if parameter_label else parameter_name

    async def init(self, sc: SushiController) -> None:
        self.track_id = await sc.audio_graph.get_track_id(self.track_name)
        self.plugin_id = await sc.audio_graph.get_processor_id(self.plugin_name)
        self.param_id = await sc.parameters.get_parameter_id(
            self.plugin_id, self.parameter_name
        )
        self.value = await sc.parameters.get_parameter_value(
            self.plugin_id, self.param_id
        )

    def __repr__(self) -> str:
        return "PluginParameterMapping: plugin=%s, parameter=%s, controller_name=%s" % (
            self.plugin_name,
            self.parameter_name,
            self.controller_name,
        )


class PluginSwitchMapping(PluginParameterMapping):
    """Mapping for those special cases where a plugin parameter must be toggled between 2 values"""

    def __init__(
        self,
        track_name: str,
        plugin_name: str,
        parameter_name: str,
        controller_name: str,
        value_A: float = 0.0,
        value_B: float = 1.0,
        preprocessor: Preprocessor | None = None,
    ):
        super().__init__(
            track_name, plugin_name, parameter_name, controller_name, preprocessor
        )
        self.values = (value_A, value_B)
        self._current_value_idx = 0


class TrackSwitchMapping(TrackParameterMapping):
    """Mapping for those special cases where a plugin parameter must be toggled between 2 values"""

    def __init__(
        self,
        track_name: str,
        parameter_name: str,
        controller_name: str,
        value_A: float = 0.0,
        value_B: float = 1.0,
        preprocessor: Preprocessor | None = None,
    ):
        super().__init__(track_name, parameter_name, controller_name, preprocessor)
        self.values = (value_A, value_B)
        self._current_value_idx = 0


class BypassMapping(PluginParameterMapping):
    def __init__(
        self,
        plugin_name: str,
        controller_name: str,
        preprocessor: Preprocessor | None = None,
    ):
        self.plugin_name = plugin_name
        self.controller_name = controller_name
        self.preprocessor = preprocessor

    async def init(self, sc: SushiController) -> None:
        self.plugin_id = await sc.audio_graph.get_processor_id(self.plugin_name)

    def __repr__(self) -> str:
        return "BypassMapping: plugin=%s, controller=%s}" % (
            self.plugin_name,
            self.controller_name,
        )


class ComboMapping:
    """This holds a list of Mappings. Useful when you need to trigger several mappings from the same controller event"""

    def __init__(
        self,
        mappings: list[Mapping],
        controller_name: str,
        parameter_label: str = "Combo",
        initial_value: float = 0.0,
    ) -> None:
        self.mappings = mappings
        self.controller_name = controller_name
        self.parameter_label = parameter_label
        self.value = initial_value

    def __repr__(self) -> str:
        return "ComboMapping - %s" % self.mappings

    async def init(self, sc: SushiController) -> None:
        for m in self.mappings:
            await m.init(sc)


class AcceleratedEncoder:
    def __init__(
        self, min_val=0.0, max_val=1.0, base_step=0.01, max_step=0.1, accel_window=0.1
    ):
        self.min_val = min_val
        self.max_val = max_val
        self.base_step = base_step
        self.max_step = max_step
        self.accel_window = accel_window  # seconds — faster than this = accelerate
        self.last_time = None

    def tick(self, delta: int, base_value: float) -> float:
        now = time.monotonic()

        if self.last_time is None:
            step = self.base_step
        else:
            dt = now - self.last_time
            # Faster turns = smaller dt = bigger step
            if dt < self.accel_window:
                factor = 1.0 - (dt / self.accel_window)  # 0..1
                step = self.base_step + factor * (self.max_step - self.base_step)
            else:
                step = self.base_step

        self.last_time = now
        value = min(max(base_value + delta * step, self.min_val), self.max_val)
        return value


class MappingManager:
    """This class consumes UiEvents and maps them to Sushi controls or other internal settings."""

    def __init__(self) -> None:
        observer.subscribe(event="UiEvent", cb=self._dispatch_ui_event)
        observer.subscribe(
            event="SushiParameterUpdate", cb=self._handle_sushi_param_update
        )
        observer.subscribe(event="NewControllerMap", cb=self._update_controller_map)
        observer.subscribe(event="ModeSwitch", cb=self._switch_mode)
        observer.subscribe(event="CycleMode", cb=self._cycle_mode)
        observer.subscribe(
            event="MappingsInitialized", cb=self._handle_mappings_initialized
        )
        self._accelerators: dict[int, AcceleratedEncoder] = {}
        self._mappings_initialized: bool = False
        self.mappings_by_controller_id: list[dict[int, Mapping]] = []
        self.controller_map: dict | None = None
        self._mode = 0
        self._pressed: set[str] = set()
        self._pending_press_events: list = []
        self._multipress_detection_task: asyncio.Task | None = None
        self._multipress_mappings: dict[frozenset[str], object] = {}

    async def initialize_mappings(self, mappings: list[MappingMode]) -> None:
        all_mappings = []
        for mode in mappings:
            map = [m for m in mode.mappings if not isinstance(m, Control)]
            if map == []:
                logger.warning("There are no mappings specified.")
            all_mappings.extend(map)
        await observer.emit(signal="InitMapping", mappings=all_mappings)

    def _cycle_mode(self) -> None:
        self._mode = (self._mode + 1) % len(self.mappings_by_controller_id)
        logger.debug("Cycled mode to mode %s", self._mode)

    def _switch_mode(self, new_mode: int) -> None:
        if new_mode > len(self.mappings_by_controller_id) - 1:
            logger.warning(
                f"No mappings for new mode! Sticking to current mode {self._mode}."
            )
            return
        self._mode = new_mode
        logger.debug("Switched mode to mode %s", self._mode)

    def _update_controller_map(self, controller_map):
        self.controller_map = controller_map
        logger.debug("Updated controller map")

    def _handle_mappings_initialized(self):
        self._mappings_initialized = True

    async def _handle_sushi_param_update(self, notification) -> None:
        # await observer.emit("UpdateParameter", mapping.parameter_label)
        logger.debug("Sushi parameter update: %s", notification)

    def register_mappings(self, mappings: list[MappingMode]) -> bool:
        """
        Register mappings and resolve controller names to IDs.
        Builds an internal dict of k, v where k is a controller ID gotten
        from Sensei.

        Args:
            mappings: List of Mapping objects
            controller_name_map: Dictionary mapping controller names to IDs

        Raises:
            ValueError: If a controller_name is not found in the map
        """
        if not self.controller_map:
            logger.error("Controller map not yet initialized!")
            return False

        logger.info(f"Registering {len(mappings)} mappings")

        # Clearing existing mappings
        self.mappings_by_controller_id = []

        for i, mode in enumerate(mappings):
            self.mappings_by_controller_id.append({})
            for mapping in mode.mappings:
                self._register_single_mapping(
                    mapping, self.mappings_by_controller_id[i]
                )

        logger.debug("all mappings registered successfully")
        return True

    def _register_single_mapping(
        self,
        mapping: Mapping | MultiSwitch,
        mapping_dict_for_mode: dict[int, Mapping],
    ) -> None:
        assert self.controller_map is not None

        match mapping:
            case MultiSwitch():
                self._multipress_mappings[frozenset(set(mapping.controller_names))] = (
                    mapping.mapping
                )
            case _:
                controller_id = self.controller_map.get(mapping.controller_name)
                if controller_id is None:
                    raise ValueError(
                        f"Controller '{mapping.controller_name}' not found in available controllers. "
                        f"Available: {list(self.controller_map.keys())}"
                    )

                mapping_dict_for_mode[controller_id] = mapping

        match mapping:
            case MultiSwitch():
                logger.debug(
                    f"Registered: controllers {', '.join(name for name in mapping.controller_names)} -> mapping = {mapping.mapping}"
                )
            case Control():
                logger.debug(
                    f"Registered: controller '{mapping.controller_name}' -> control -> cb = {mapping.callback}"
                )
            case ComboMapping():
                logger.debug(
                    f"Registered: controller '{mapping.controller_name}' (ID {controller_id}) -> ComboMapping: {mapping.mappings}"
                )
            case _:
                logger.debug(
                    f"Registered: controller '{mapping.controller_name}' (ID {controller_id}) -> "
                    f"{getattr(mapping, 'track_name', '')}/{getattr(mapping, 'plugin_name', '-')}/{getattr(mapping, 'parameter_name', 'BYPASS')}"
                )

    def _get_value_from_event(self, event) -> int | float | None:
        event_type = event.WhichOneof("event")
        match event_type:
            case "analog_ev":
                return event.analog_ev.value
            case "toggle_ev":
                return event.toggle_ev.value
            case "relative_ev":
                return event.relative_ev.value
            case "range_ev":
                return event.range_ev.value
            case _:
                raise

    def _get_multi_switch_mapping(self, pressed: frozenset, event):
        logger.debug("Getting multi mapping...")
        if len(pressed) == 1:
            return self.mappings_by_controller_id[self._mode].get(event.controller_id)
        elif len(pressed) > 1:
            return self._multipress_mappings.get(pressed)

    async def _dispatch_ui_event(self, event) -> None:
        """
        Process an incoming event and route it to the appropriate sushi parameter.

        Args:
            event: event message from Sensei
        """

        event_type = event.WhichOneof("event")

        if event_type == "toggle_ev":
            mapping = self.mappings_by_controller_id[self._mode].get(
                event.controller_id
            )
            name = next(
                (
                    n
                    for n, id in self.controller_map.items()
                    if id == event.controller_id
                ),
                None,
            )
            pressed = bool(event.toggle_ev.value)
            if pressed and name is not None:
                self._pressed.add(name)

            # A Control hands the raw value to a user callback, which can only tell a
            # press from a release if it sees both edges. It is never resolved as part
            # of a combination either, so holding one down while another switch is
            # pressed still delivers every edge of both.
            if isinstance(mapping, Control):
                if not pressed:
                    self._pressed.discard(name)
            elif pressed:
                return
            else:
                mapping = self._get_multi_switch_mapping(
                    frozenset(self._pressed), event
                )
                self._pressed = set()
        else:
            mapping = self.mappings_by_controller_id[self._mode].get(
                event.controller_id
            )
            if not mapping:
                return

            if event_type == "relative_ev" and hasattr(mapping, "value"):
                if event.controller_id not in self._accelerators:
                    self._accelerators[event.controller_id] = AcceleratedEncoder()

                mapping.value = self._accelerators[event.controller_id].tick(
                    event.relative_ev.value, mapping.value
                )

        await self.run_mapping(mapping, event, event_type)

    async def run_mapping(self, mapping, event, event_type) -> None:
        if not mapping:
            logger.debug("No mapping for controller id %s", event.controller_id)
            return

        match mapping:
            case Control():
                await self._handle_control_event(mapping, event)
                return
            case BypassMapping():
                await self._handle_bypass_event(mapping, event)
                return
            case ComboMapping():
                logger.debug("Running Combo!")
                await self._run_combo_mapping(mapping, event, event_type)
                await observer.emit("UpdateParameter", mapping.parameter_label)
                return
            case _:
                if event_type == "analog_ev":
                    await self._handle_analog_event(event, mapping)
                elif event_type == "toggle_ev":
                    await self._handle_toggle_event(event, mapping)
                elif event_type == "relative_ev":
                    await self._handle_relative_event(event, mapping)
                elif event_type == "range_ev":
                    await self._handle_range_event(event, mapping)
                else:
                    logger.warning("Unknown event type: %s", event_type)

    async def _run_combo_mapping(self, combo_mapping, event, event_type) -> None:
        for m in combo_mapping.mappings:
            m.value = combo_mapping.value
            await self.run_mapping(m, event, event_type)

    async def _handle_analog_event(self, event, mapping) -> None:
        """handle analog controller events (pots, faders)."""
        await self._create_sushi_event(event, mapping, event.analog_ev.value)

    async def _handle_toggle_event(self, event, mapping) -> None:
        """handle toggle/switch events."""
        # toggling value between A and B
        if isinstance(mapping, TrackSwitchMapping) or isinstance(
            mapping, PluginSwitchMapping
        ):
            mapping._current_value_idx = (mapping._current_value_idx + 1) % 2
            value = mapping.values[mapping._current_value_idx]
        else:
            # for regular mappings, treat as binary 1.0/0.0
            value = 1.0 if event.toggle_ev.value else 0.0

        await self._create_sushi_event(event, mapping, value)

        logger.debug(
            "Toggle event: controller=%s, pressed=%s", event.controller_id, value
        )

    async def _create_sushi_event(self, event, mapping, value) -> None:
        # apply preprocessor if defined
        if mapping.preprocessor:
            value = mapping.preprocessor(value)

        logger.debug(
            "Analog event: controller=%s, value=%s", event.controller_id, value
        )

        # mapping.value = value

        if isinstance(mapping, PluginParameterMapping):
            await self._emit_sushi_plugin_event(
                track_id=mapping.track_id,
                plugin_id=mapping.plugin_id,
                param_id=mapping.param_id,
                value=value,
            )
        elif isinstance(mapping, TrackParameterMapping):
            await self._emit_sushi_track_event(
                track_id=mapping.track_id,
                param_id=mapping.param_id,
                value=value,
            )

        await observer.emit("UpdateParameter", mapping.parameter_label)

    async def _handle_relative_event(self, event, mapping) -> None:
        """
        handle relative events (encoders).

        note: this is a basic implementation. for production use, you may want to:
        - track current parameter values
        - apply scaling/acceleration
        - clamp values to parameter ranges
        """
        logger.debug(
            "Relative event: controller=%s, New value=%s",
            event.controller_id,
            mapping.value,
        )
        await self._create_sushi_event(event, mapping, mapping.value)

    async def _handle_range_event(self, event, mapping) -> None:
        """
        handle range events (discrete position controllers).

        maps discrete range values to parameter values.
        """
        # basic implementation: use the range value directly
        value = float(event.range_ev.value)

        # apply preprocessor if defined
        if mapping.preprocessor:
            value = mapping.preprocessor(value)

        await self._emit_sushi_plugin_event(
            track_id=mapping.track_id,
            plugin_id=mapping.plugin_id,
            param_id=mapping.param_id,
            value=value,
        )

        logger.debug("Range event: controller=%s, Range=%s", event.controller_id, value)

    async def _handle_control_event(self, mapping, event) -> None:
        logger.debug("Received control event: %s -> cb: %s", event, mapping.callback)
        await mapping.callback(self._get_value_from_event(event))

    async def _handle_bypass_event(self, mapping, event) -> None:
        logger.debug("Toggling bypass state for plugin %s", mapping.controller_name)
        await self._emit_sushi_bypass_event(mapping.plugin_id)

    async def _emit_sushi_plugin_event(
        self, track_id: int, plugin_id: int, param_id: int, value: float
    ) -> None:
        event: SushiPluginEvent = {
            "track_id": track_id,
            "plugin_id": plugin_id,
            "param_id": param_id,
            "value": value,
        }
        await observer.emit("SushiPluginEvent", event)

    async def _emit_sushi_track_event(
        self, track_id: int, param_id: int, value: float
    ) -> None:
        event: SushiTrackEvent = {
            "track_id": track_id,
            "param_id": param_id,
            "value": value,
        }
        await observer.emit("SushiTrackEvent", event)

    async def _emit_sushi_bypass_event(self, plugin_id: int) -> None:
        event: PluginBypassEvent = {"plugin_id": plugin_id}
        await observer.emit("PluginBypassEvent", event)
