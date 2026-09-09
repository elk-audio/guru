import pytest
from elkpy import sushierrors

from guru import observer
from guru.presets import Preset, PresetManager
from guru.sushi_client import SushiClient


@pytest.mark.asyncio
async def test_preset_init_resolves_real_ids_from_sushi_config(fake_sushi):
    preset = Preset(
        name="Fuzz",
        initial_state=[
            {
                "processor": "GxVintageFuzzMaster",
                "parameters": {"INTENSITY": 0.8},
                "bypassed": False,
            },
        ],
    )

    await preset.init(fake_sushi)

    processor_id = fake_sushi.processors["GxVintageFuzzMaster"]
    param_id = await fake_sushi.parameters.get_parameter_id(processor_id, "INTENSITY")
    assert preset.parameter_states == [(processor_id, param_id, 0.8)]
    assert preset.bypass_states == [(processor_id, False)]


@pytest.mark.asyncio
async def test_preset_init_raises_when_processor_missing_from_sushi_config(fake_sushi):
    # Catches the case where a preset references a plugin that was renamed or
    # removed in sushi_config.json but not updated here.
    preset = Preset(name="Typo", initial_state=[{"processor": "GxTypoDrive"}])

    with pytest.raises(sushierrors.SushiNotFoundError):
        await preset.init(fake_sushi)


@pytest.mark.asyncio
async def test_load_preset_by_index_applies_only_the_diff(fake_sushi):
    # Wire SushiClient's real ApplyPresetState handler up to the fake, without
    # going through __init__ (which would try to open a real connection to Sushi).
    client = object.__new__(SushiClient)
    client.controller = fake_sushi
    observer.subscribe("ApplyPresetState", cb=client.apply_preset_state)

    manager = PresetManager()

    # Preset at index 0 is assumed to already match Sushi's boot state, so
    # loading it is a no-op diff - nothing should be sent to Sushi for it.
    boot_preset = Preset(name="Boot", initial_state=[{"processor": "GxVintageFuzzMaster", "bypassed": True}])
    fuzz_preset = Preset(
        name="Fuzz",
        initial_state=[
            {"processor": "GxVintageFuzzMaster", "parameters": {"INTENSITY": 0.8}, "bypassed": False},
        ],
    )
    for preset in (boot_preset, fuzz_preset):
        await preset.init(fake_sushi)
        manager.add_preset(preset)

    assert await manager.load_preset_by_index(0) is True
    assert fake_sushi.calls == []

    assert await manager.load_preset_by_index(1) is True

    processor_id = fake_sushi.processors["GxVintageFuzzMaster"]
    param_id = await fake_sushi.parameters.get_parameter_id(processor_id, "INTENSITY")
    assert fake_sushi.bypass_states[processor_id] is False
    assert fake_sushi.parameter_values[(processor_id, param_id)] == 0.8
    assert ("set_processor_bypass_state", processor_id, False) in fake_sushi.calls
    assert ("set_parameter_value", processor_id, param_id, 0.8) in fake_sushi.calls
