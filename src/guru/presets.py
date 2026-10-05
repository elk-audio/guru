"""
Preset management system for the topo-pedal controller.

This module handles loading, switching, and managing audio effect presets,
including plugin bypass states.
"""

from typing import Optional, Any
import logging
import time

from elkpy.sushicontroller import SushiController

from . import observer
from .protocols import PluginState

PRESET_LOADING_MIN_WAIT_S = 2


class Preset:
    def __init__(
        self,
        name: str,
        initial_state: list[PluginState] | None = None,
        mode: int | None = None,
        label: str | None = None
    ) -> None:
        self.name = name
        self.initial_state: list[PluginState] = initial_state if initial_state else []
        self.parameter_states: list[tuple[int, int, float]] = []
        self.bypass_states: list[tuple[int, bool]] = []
        self.mode = mode
        self.label = label if label else name
        self._is_initialized: bool = False

    async def init(self, sc: SushiController) -> None:
        for state in self.initial_state:
            proc_id = await sc.audio_graph.get_processor_id(state["processor"])
            if "parameters" in state.keys():
                for param_name, value in state["parameters"].items():
                    param_id = await sc.parameters.get_parameter_id(proc_id, param_name)
                    self.parameter_states.append((proc_id, param_id, value))
            if "bypassed" in state.keys():
                self.bypass_states.append((proc_id, state["bypassed"]))
        self._is_initialized = True

    def __repr__(self) -> str:
        initialized_str = 'Initialized' if self._is_initialized else 'Not initialized yet.'
        return "%s: %s => %s" % (self.name, self.initial_state, self._is_initialized)        


class PresetManager:
    """
    Manages audio effect presets and handles dynamic switching.

    Coordinates with the Sushi audio host to apply preset configurations
    including plugin bypass states.
    """

    def __init__(self) -> None:
        """
        Initialize preset manager.

        Args:
            event_bus: Event bus for listening to preset switch events
            sushi_controller: Sushi controller for audio graph manipulation
        """
        self._logger = logging.getLogger('PRESETS')

        self.preset_list: list[Preset] = []
        self.current_preset_index: int = 0
        self._last_preset_loading = time.time()
        observer.subscribe("LoadPreset", self._handle_load_preset)
        observer.subscribe("LoadNextPreset", self.load_next_preset)
        observer.subscribe("LoadPresetByName", self.load_preset_by_name)

    async def _handle_load_preset(self, preset: Preset) -> bool:
        return await self.load_preset(preset)

    def add_presets(self, presets: list[Preset]) -> None:
        for p in presets:
            self.add_preset(p)

    def add_preset(self, preset: Preset) -> None:
        """
        Add a preset to the preset list.

        Args:
            preset: Preset instance to add
        """
        self.preset_list.append(preset)
        self._logger.info(
            f"Added preset '{preset.name}' (total: {len(self.preset_list)})"
        )

    async def initialize_presets(self) -> None:
        for preset in self.preset_list:
            await observer.emit("InitPreset", preset)

    def remove_preset(self, index: int) -> bool:
        """
        Remove a preset by index.

        Args:
            index: Index of preset to remove

        Returns:
            True if preset was removed, False if index invalid
        """
        if 0 <= index < len(self.preset_list):
            preset = self.preset_list.pop(index)
            self._logger.info(f"Removed preset '{preset.name}'")

            # Adjust current preset index if needed
            if self.current_preset_index >= len(self.preset_list):
                self.current_preset_index = max(0, len(self.preset_list) - 1)

            return True
        else:
            self._logger.warning(f"Invalid preset index: {index}")
            return False

    def build_preset_diff(self, old_preset: Preset, new_preset: Preset) -> Preset:
        """Builds a new Preset with only the diff between 2 other presets"""
        p1 = old_preset.initial_state
        p2 = new_preset.initial_state
        filtered_state = [d for d in p2 if d not in p1]
        filtered_bypass_states = [d for d in new_preset.bypass_states if d not in old_preset.bypass_states]
        filtered_parameter_states = [d for d in new_preset.parameter_states if d not in old_preset.parameter_states]
        filtered_preset = Preset(name=new_preset.name, initial_state=filtered_state, mode=new_preset.mode)
        filtered_preset.bypass_states = filtered_bypass_states
        filtered_preset.parameter_states = filtered_parameter_states
        return filtered_preset


    async def load_preset_by_name(self, name: str) -> bool:
        return await self.load_preset_by_index(
            self.preset_list.index(next(preset for preset in self.preset_list if preset.name == name))
        )

    async def load_preset(self, preset: Preset) -> bool:
        try:
            self._logger.debug("Loading preset %s", preset.name)

            # Set plugin bypass states
            await self._apply_initial_state(preset)
            return True

        except Exception as e:
            self._logger.error("Failed to load preset %s: %s", preset.name, e)
            return False


    async def load_preset_by_index(self, index: int) -> bool:
        """
        Load a specific preset by index.

        Args:
            index: Index of preset to load

        Returns:
            True if preset loaded successfully, False otherwise
        """
        if not (0 <= index < len(self.preset_list)):
            self._logger.error(f"Invalid preset index: {index}")
            return False

        self._last_preset_loading = time.time()
        preset = self.preset_list[index]
        current_preset = self.get_current_preset()

        filtered_preset = self.build_preset_diff(current_preset, preset)

        try:
            self._logger.debug("Loading preset %s %s", preset.name, index)

            # Set plugin bypass states
            await self._apply_initial_state(filtered_preset)

            # Update current preset index
            old_index = self.current_preset_index
            self.current_preset_index = index

            self._logger.debug(
                "Successfully loaded preset '%s' (switched from '%s' at index %s)", preset.name, current_preset.name, old_index
            )
            await observer.emit("DrawText", f"Preset {preset.name} loaded successfully")
            return True

        except Exception as e:
            self._logger.error(f"Failed to load preset '{preset.name}': {e}")
            return False

    async def load_next_preset(self, value=None) -> bool:
        """
        Load the next preset in the list (cycles back to first).

        Returns:
            True if preset loaded successfully, False otherwise
        """
        if not self.preset_list:
            self._logger.warning("No presets available")
            return False

        if (time.time() - self._last_preset_loading) <= PRESET_LOADING_MIN_WAIT_S:
            self._logger.debug("Preset switch pressed - ignoring because too early")
            return False

        self._logger.debug("Preset switch pressed - switching to next preset")
        next_index = (self.current_preset_index + 1) % len(self.preset_list)
        return await self.load_preset_by_index(next_index)  # Returns coroutine

    async def load_previous_preset(self) -> bool:
        """
        Load the previous preset in the list (cycles to last).

        Returns:
            True if preset loaded successfully, False otherwise
        """
        if not self.preset_list:
            self._logger.warning("No presets available")
            return False

        prev_index = (self.current_preset_index - 1) % len(self.preset_list)
        return await self.load_preset_by_index(prev_index)

    def get_current_preset(self) -> Optional[Preset]:
        """
        Get the currently active preset.

        Returns:
            Current preset instance, or None if no presets available
        """
        if 0 <= self.current_preset_index < len(self.preset_list):
            return self.preset_list[self.current_preset_index]
        return None

    def get_current_preset_name(self) -> str:
        """
        Get the name of the currently active preset.

        Returns:
            Name of current preset, or "No preset" if none available
        """
        current = self.get_current_preset()
        return current.name if current else "No preset"

    def get_preset_names(self) -> list[str]:
        """
        Get list of all preset names.

        Returns:
            List of preset names
        """
        return [preset.name for preset in self.preset_list]

    def get_status(self) -> dict[str, Any]:
        """
        Get current status of the preset manager.

        Returns:
            Dictionary containing preset manager status
        """
        current_preset = self.get_current_preset()

        return {
            "total_presets": len(self.preset_list),
            "current_preset_index": self.current_preset_index,
            "current_preset_name": self.get_current_preset_name(),
            "preset_names": self.get_preset_names(),
            "current_preset_details": {
                "active_plugins": current_preset.active_plugins
                if current_preset
                else [],
                "inactive_plugins": current_preset.inactive_plugins
                if current_preset
                else []
            }
            if current_preset
            else None,
        }

    async def _apply_initial_state(self, preset: Preset) -> None:
        """
        Apply plugin bypass states for the given preset.

        Args:
            preset: Preset to apply bypass states for
        """
        await observer.emit("ApplyPresetState", preset)

    def clear_presets(self) -> None:
        """Clear all presets from the manager."""
        self.preset_list.clear()
        self.current_preset_index = 0
        self._logger.info("Cleared all presets")
