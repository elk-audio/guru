import pytest
from unittest.mock import AsyncMock, patch
from guru.mappings import (
    MappingManager,
    MappingMode,
    PluginParameterMapping,
    Control,
    MultiSwitch,
    ComboMapping,
)
from functools import partial
from guru import observer


MAPPINGS_1 = [
    MappingMode(
        [
            PluginParameterMapping(
                track_name="TRACK",
                plugin_name="GxVintageFuzzMaster",
                parameter_name="INTENSITY",
                controller_name="ENC1",
                parameter_label="Fuzz",
            )
        ],
        1,
    )
]


MAPPINGS_2 = [
    MappingMode(
        [
            Control(
                controller_name="ENC1S", cb=lambda _: observer.emit("ModeSwitch", 0)
            ),
            Control(
                controller_name="ENC2S", cb=lambda _: observer.emit("ModeSwitch", 0)
            ),
            Control(
                controller_name="ENC3S", cb=lambda _: observer.emit("ModeSwitch", 0)
            ),
            PluginParameterMapping(
                track_name="TRACK",
                plugin_name="Vibey",
                parameter_name="Delay",
                controller_name="ENC1",
            ),
            PluginParameterMapping(
                track_name="TRACK",
                plugin_name="Vibey",
                parameter_name="Vibes",
                controller_name="ENC2",
            ),
            PluginParameterMapping(
                track_name="TRACK",
                plugin_name="Vibey",
                parameter_name="Level",
                controller_name="ENC3",
            ),
        ],
        16,
    )
]


MAPPINGS_3 = [
    # Default layer: the slot machine
    MappingMode(
        [
            Control(
                controller_name="ENC1S", cb=lambda _: observer.emit("Slot1ParamMode")
            ),
            Control(
                controller_name="ENC2S", cb=lambda _: observer.emit("Slot2ParamMode")
            ),
            Control(
                controller_name="ENC3S", cb=lambda _: observer.emit("Slot3ParamMode")
            ),
            Control(controller_name="ENC1", cb=partial(observer.emit, "Slot1Select")),
            Control(controller_name="ENC2", cb=partial(observer.emit, "Slot2Select")),
            Control(controller_name="ENC3", cb=partial(observer.emit, "Slot3Select")),
            MultiSwitch(
                controller_names=["ENC1S", "ENC2S", "ENC3S"],
                mapping=Control(
                    controller_name="ENC3S", cb=lambda _: observer.emit("SpinIt")
                ),
            ),
        ],
        0,
    ),
    # Mode 1: GxLiquidDrive param view
    # ID : 1
    MappingMode(
        [
            Control(
                controller_name="ENC1S", cb=lambda _: observer.emit("ModeSwitch", 0)
            ),
            Control(
                controller_name="ENC2S", cb=lambda _: observer.emit("ModeSwitch", 0)
            ),
            Control(
                controller_name="ENC3S", cb=lambda _: observer.emit("ModeSwitch", 0)
            ),
            PluginParameterMapping(
                track_name="TRACK",
                plugin_name="GxLiquidDrive",
                parameter_name="DRIVE",
                controller_name="ENC1",
                parameter_label="Drive",
            ),
            PluginParameterMapping(
                track_name="TRACK",
                plugin_name="GxLiquidDrive",
                parameter_name="LEVEL",
                controller_name="ENC2",
                parameter_label="Volume",
            ),
        ],
        1,
    ),
    # Mode 2: GxBaJaTubeDriver
    MappingMode(
        [
            Control(
                controller_name="ENC1S", cb=lambda _: observer.emit("ModeSwitch", 0)
            ),
            Control(
                controller_name="ENC2S", cb=lambda _: observer.emit("ModeSwitch", 0)
            ),
            Control(
                controller_name="ENC3S", cb=lambda _: observer.emit("ModeSwitch", 0)
            ),
            PluginParameterMapping(
                track_name="TRACK",
                plugin_name="GxBaJaTubeDriver",
                parameter_name="DRIVE",
                controller_name="ENC1",
                parameter_label="Drive",
            ),
            PluginParameterMapping(
                track_name="TRACK",
                plugin_name="GxBaJaTubeDriver",
                parameter_name="TONE",
                controller_name="ENC2",
                parameter_label="Tone",
            ),
            PluginParameterMapping(
                track_name="TRACK",
                plugin_name="GxBaJaTubeDriver",
                parameter_name="VOLUME",
                controller_name="ENC3",
                parameter_label="Vol",
            ),
        ],
        2,
    ),
    MappingMode(
        [
            # Mode 3: GxVintageFuzzMaster
            Control(
                controller_name="ENC1S", cb=lambda _: observer.emit("ModeSwitch", 0)
            ),
            Control(
                controller_name="ENC2S", cb=lambda _: observer.emit("ModeSwitch", 0)
            ),
            Control(
                controller_name="ENC3S", cb=lambda _: observer.emit("ModeSwitch", 0)
            ),
            PluginParameterMapping(
                track_name="TRACK",
                plugin_name="GxVintageFuzzMaster",
                parameter_name="INTENSITY",
                controller_name="ENC1",
                parameter_label="Fuzz",
            ),
            PluginParameterMapping(
                track_name="TRACK",
                plugin_name="GxVintageFuzzMaster",
                parameter_name="MODE",
                controller_name="ENC2",
                parameter_label="Mode",
            ),
            PluginParameterMapping(
                track_name="TRACK",
                plugin_name="GxVintageFuzzMaster",
                parameter_name="VOLUME",
                controller_name="ENC3",
                parameter_label="Vol",
            ),
        ],
        3,
    ),
    # Mode 4: mda Degrade
    MappingMode(
        [
            Control(
                controller_name="ENC1S", cb=lambda _: observer.emit("ModeSwitch", 0)
            ),
            Control(
                controller_name="ENC2S", cb=lambda _: observer.emit("ModeSwitch", 0)
            ),
            Control(
                controller_name="ENC3S", cb=lambda _: observer.emit("ModeSwitch", 0)
            ),
            PluginParameterMapping(
                track_name="TRACK",
                plugin_name="Degrade",
                parameter_name="Quant",
                controller_name="ENC1",
                parameter_label="Bits",
            ),
            PluginParameterMapping(
                track_name="TRACK",
                plugin_name="Degrade",
                parameter_name="PostFilt",
                controller_name="ENC2",
            ),
            PluginParameterMapping(
                track_name="TRACK",
                plugin_name="Degrade",
                parameter_name="Rate",
                controller_name="ENC3",
                preprocessor=lambda x: 0.272 + (x * (0.723 - 0.272)),
            ),
        ],
        4,
    ),
    # Mode 5: BW Chorus
    MappingMode(
        [
            Control(
                controller_name="ENC1S", cb=lambda _: observer.emit("ModeSwitch", 0)
            ),
            Control(
                controller_name="ENC2S", cb=lambda _: observer.emit("ModeSwitch", 0)
            ),
            Control(
                controller_name="ENC3S", cb=lambda _: observer.emit("ModeSwitch", 0)
            ),
            PluginParameterMapping(
                track_name="TRACK",
                plugin_name="BW Chorus",
                parameter_name="amount",
                controller_name="ENC1",
            ),
            PluginParameterMapping(
                track_name="TRACK",
                plugin_name="BW Chorus",
                parameter_name="rate",
                controller_name="ENC2",
            ),
        ],
        5,
    ),
    # Mode 6: BW Phaser
    MappingMode(
        [
            Control(
                controller_name="ENC1S", cb=lambda _: observer.emit("ModeSwitch", 0)
            ),
            Control(
                controller_name="ENC2S", cb=lambda _: observer.emit("ModeSwitch", 0)
            ),
            Control(
                controller_name="ENC3S", cb=lambda _: observer.emit("ModeSwitch", 0)
            ),
            PluginParameterMapping(
                track_name="TRACK",
                plugin_name="BW Phaser",
                parameter_name="rate",
                controller_name="ENC1",
            ),
            PluginParameterMapping(
                track_name="TRACK",
                plugin_name="BW Phaser",
                parameter_name="center",
                controller_name="ENC2",
            ),
            PluginParameterMapping(
                track_name="TRACK",
                plugin_name="BW Phaser",
                parameter_name="amount",
                controller_name="ENC3",
            ),
        ],
        6,
    ),
    # Mode 7: BW Tremolo
    MappingMode(
        [
            Control(
                controller_name="ENC1S", cb=lambda _: observer.emit("ModeSwitch", 0)
            ),
            Control(
                controller_name="ENC2S", cb=lambda _: observer.emit("ModeSwitch", 0)
            ),
            Control(
                controller_name="ENC3S", cb=lambda _: observer.emit("ModeSwitch", 0)
            ),
            PluginParameterMapping(
                track_name="TRACK",
                plugin_name="BW Tremolo",
                parameter_name="rate",
                controller_name="ENC1",
            ),
            PluginParameterMapping(
                track_name="TRACK",
                plugin_name="BW Tremolo",
                parameter_name="amount",
                controller_name="ENC2",
            ),
        ],
        7,
    ),
    # Mode 8: mda RingMod
    MappingMode(
        [
            Control(
                controller_name="ENC1S", cb=lambda _: observer.emit("ModeSwitch", 0)
            ),
            Control(
                controller_name="ENC2S", cb=lambda _: observer.emit("ModeSwitch", 0)
            ),
            Control(
                controller_name="ENC3S", cb=lambda _: observer.emit("ModeSwitch", 0)
            ),
        ],
        8,
    ),
    # Mode 9: mda Leslie
    MappingMode(
        [
            Control(
                controller_name="ENC1S", cb=lambda _: observer.emit("ModeSwitch", 0)
            ),
            Control(
                controller_name="ENC2S", cb=lambda _: observer.emit("ModeSwitch", 0)
            ),
            Control(
                controller_name="ENC3S", cb=lambda _: observer.emit("ModeSwitch", 0)
            ),
            PluginParameterMapping(
                track_name="TRACK",
                plugin_name="Leslie",
                parameter_name="Speed",
                controller_name="ENC1",
            ),
            ComboMapping(
                controller_name="ENC2",
                parameter_label="Width",
                initial_value=0.1,
                mappings=[
                    PluginParameterMapping(
                        track_name="TRACK",
                        plugin_name="Leslie",
                        parameter_name="Lo Width",
                        controller_name="ENC2",
                    ),
                    PluginParameterMapping(
                        track_name="TRACK",
                        plugin_name="Leslie",
                        parameter_name="Hi Width",
                        controller_name="ENC2",
                    ),
                ],
            ),
            ComboMapping(
                controller_name="ENC3",
                parameter_label="Throb",
                initial_value=0.1,
                mappings=[
                    PluginParameterMapping(
                        track_name="TRACK",
                        plugin_name="Leslie",
                        parameter_name="Lo Throb",
                        controller_name="ENC3",
                    ),
                    PluginParameterMapping(
                        track_name="TRACK",
                        plugin_name="Leslie",
                        parameter_name="Hi Throb",
                        controller_name="ENC3",
                    ),
                ],
            ),
        ],
        9,
    ),
    # Mode 10: mda Detune
    MappingMode(
        [
            Control(
                controller_name="ENC1S", cb=lambda _: observer.emit("ModeSwitch", 0)
            ),
            Control(
                controller_name="ENC2S", cb=lambda _: observer.emit("ModeSwitch", 0)
            ),
            Control(
                controller_name="ENC3S", cb=lambda _: observer.emit("ModeSwitch", 0)
            ),
            PluginParameterMapping(
                track_name="TRACK",
                plugin_name="Detune",
                parameter_name="Detune",
                controller_name="ENC1",
            ),
            PluginParameterMapping(
                track_name="TRACK",
                plugin_name="Detune",
                parameter_name="Mix",
                controller_name="ENC2",
            ),
        ],
        10,
    ),
    # Mode 11: Freeverb
    MappingMode(
        [
            Control(
                controller_name="ENC1S", cb=lambda _: observer.emit("ModeSwitch", 0)
            ),
            Control(
                controller_name="ENC2S", cb=lambda _: observer.emit("ModeSwitch", 0)
            ),
            Control(
                controller_name="ENC3S", cb=lambda _: observer.emit("ModeSwitch", 0)
            ),
            PluginParameterMapping(
                track_name="TRACK",
                plugin_name="Freeverb",
                parameter_name="room_size",
                controller_name="ENC1",
                parameter_label="Size",
            ),
            PluginParameterMapping(
                track_name="TRACK",
                plugin_name="Freeverb",
                parameter_name="width",
                controller_name="ENC2",
                parameter_label="Width",
            ),
            ComboMapping(
                mappings=[
                    PluginParameterMapping(
                        track_name="TRACK",
                        plugin_name="Freeverb",
                        parameter_name="wet",
                        controller_name="ENC2",
                        parameter_label="Wet",
                        preprocessor=lambda x: x * 0.5,
                    ),
                    PluginParameterMapping(
                        track_name="TRACK",
                        plugin_name="Freeverb",
                        parameter_name="dry",
                        controller_name="ENC2",
                        parameter_label="Dry",
                        preprocessor=lambda x: (1 - x) * 0.5,
                    ),
                ],
                controller_name="ENC3",
                parameter_label="Mix",
                initial_value=0.1,
            ),
        ],
        11,
    ),
    # Mode 12: DubDelay
    MappingMode(
        [
            Control(
                controller_name="ENC1S", cb=lambda _: observer.emit("ModeSwitch", 0)
            ),
            Control(
                controller_name="ENC2S", cb=lambda _: observer.emit("ModeSwitch", 0)
            ),
            Control(
                controller_name="ENC3S", cb=lambda _: observer.emit("ModeSwitch", 0)
            ),
            PluginParameterMapping(
                track_name="TRACK",
                plugin_name="DubDelay",
                parameter_name="Delay",
                controller_name="ENC1",
            ),
            PluginParameterMapping(
                track_name="TRACK",
                plugin_name="DubDelay",
                parameter_name="Feedback",
                controller_name="ENC2",
            ),
            PluginParameterMapping(
                track_name="TRACK",
                plugin_name="DubDelay",
                parameter_name="FX Mix",
                controller_name="ENC3",
            ),
        ],
        12,
    ),
    # Mode 13: Ambience
    MappingMode(
        [
            Control(
                controller_name="ENC1S", cb=lambda _: observer.emit("ModeSwitch", 0)
            ),
            Control(
                controller_name="ENC2S", cb=lambda _: observer.emit("ModeSwitch", 0)
            ),
            Control(
                controller_name="ENC3S", cb=lambda _: observer.emit("ModeSwitch", 0)
            ),
            PluginParameterMapping(
                track_name="TRACK",
                plugin_name="Ambience",
                parameter_name="Size",
                controller_name="ENC1",
            ),
            PluginParameterMapping(
                track_name="TRACK",
                plugin_name="Ambience",
                parameter_name="HF Damp",
                controller_name="ENC2",
            ),
            PluginParameterMapping(
                track_name="TRACK",
                plugin_name="Ambience",
                parameter_name="Mix",
                controller_name="ENC3",
            ),
        ],
        13,
    ),
    # Mode 14: No FX
    MappingMode(
        [
            Control(
                controller_name="ENC1S", cb=lambda _: observer.emit("ModeSwitch", 0)
            ),
            Control(
                controller_name="ENC2S", cb=lambda _: observer.emit("ModeSwitch", 0)
            ),
            Control(
                controller_name="ENC3S", cb=lambda _: observer.emit("ModeSwitch", 0)
            ),
        ],
        14,
    ),
    # Mode 15: Cheapdist
    MappingMode(
        [
            Control(
                controller_name="ENC1S", cb=lambda _: observer.emit("ModeSwitch", 0)
            ),
            Control(
                controller_name="ENC2S", cb=lambda _: observer.emit("ModeSwitch", 0)
            ),
            Control(
                controller_name="ENC3S", cb=lambda _: observer.emit("ModeSwitch", 0)
            ),
            PluginParameterMapping(
                track_name="TRACK",
                plugin_name="Cheapdist",
                parameter_name="aggression",
                controller_name="ENC1",
            ),
            PluginParameterMapping(
                track_name="TRACK",
                plugin_name="cheap gain",
                parameter_name="gain",
                controller_name="ENC2",
            ),
        ],
        15,
    ),
    # Mode 16: Vibey
    MappingMode(
        [
            Control(
                controller_name="ENC1S", cb=lambda _: observer.emit("ModeSwitch", 0)
            ),
            Control(
                controller_name="ENC2S", cb=lambda _: observer.emit("ModeSwitch", 0)
            ),
            Control(
                controller_name="ENC3S", cb=lambda _: observer.emit("ModeSwitch", 0)
            ),
            PluginParameterMapping(
                track_name="TRACK",
                plugin_name="Vibey",
                parameter_name="Delay",
                controller_name="ENC1",
            ),
            PluginParameterMapping(
                track_name="TRACK",
                plugin_name="Vibey",
                parameter_name="Vibes",
                controller_name="ENC2",
            ),
            PluginParameterMapping(
                track_name="TRACK",
                plugin_name="Vibey",
                parameter_name="Level",
                controller_name="ENC3",
            ),
        ],
        16,
    ),
    # Mode 17: SpringReverb
    MappingMode(
        [
            Control(
                controller_name="ENC1S", cb=lambda _: observer.emit("ModeSwitch", 0)
            ),
            Control(
                controller_name="ENC2S", cb=lambda _: observer.emit("ModeSwitch", 0)
            ),
            Control(
                controller_name="ENC3S", cb=lambda _: observer.emit("ModeSwitch", 0)
            ),
            PluginParameterMapping(
                track_name="TRACK",
                plugin_name="Spring",
                parameter_name="Tone",
                controller_name="ENC1",
            ),
            PluginParameterMapping(
                track_name="TRACK",
                plugin_name="Spring",
                parameter_name="Drive",
                controller_name="ENC2",
            ),
            PluginParameterMapping(
                track_name="TRACK",
                plugin_name="Spring",
                parameter_name="Mix",
                controller_name="ENC3",
            ),
        ],
        17,
    ),
]


@pytest.mark.asyncio
async def test_initialize_mappings():
    with (
        patch("guru.mappings.observer.emit", new_callable=AsyncMock) as mock_emit,
        patch("guru.mappings.observer.subscribe"),
    ):
        mgr = MappingManager()
        await mgr.initialize_mappings(MAPPINGS_1)
        mock_emit.assert_awaited_with(
            signal="InitMapping", mappings=MAPPINGS_1[0].mappings
        )


@pytest.mark.asyncio
async def test_initialize_multimappings():
    with (
        patch("guru.mappings.observer.emit", new_callable=AsyncMock) as mock_emit,
        patch("guru.mappings.observer.subscribe"),
    ):
        mgr = MappingManager()
        await mgr.initialize_mappings(MAPPINGS_2)
        expected = [
            m
            for mode in MAPPINGS_2
            for m in mode.mappings
            if not isinstance(m, Control)
        ]
        mock_emit.assert_awaited_with(signal="InitMapping", mappings=expected)


@pytest.mark.asyncio
async def test_initialize_multimode_mappings():
    with (
        patch("guru.mappings.observer.emit", new_callable=AsyncMock) as mock_emit,
        patch("guru.mappings.observer.subscribe"),
    ):
        mgr = MappingManager()
        await mgr.initialize_mappings(MAPPINGS_3)
        expected = [
            m
            for mode in MAPPINGS_3
            for m in mode.mappings
            if not isinstance(m, Control)
        ]
        mock_emit.assert_awaited_with(signal="InitMapping", mappings=expected)


def test_register_single_mapping():
    mgr = MappingManager()
    mgr.controller_map = {"ENC1": 32}
    mgr.register_mappings(MAPPINGS_1)
    assert mgr.mappings_by_controller_id == [{32: MAPPINGS_1[0].mappings[0]}]


def test_register_multi_mapping():
    mgr = MappingManager()
    mgr.controller_map = {
        "ENC1": 32,
        "ENC1S": 33,
        "ENC2": 34,
        "ENC2S": 35,
        "ENC3": 36,
        "ENC3S": 37,
    }
    expected = [
        {32: MAPPINGS_2[0].mappings[3],
        33: MAPPINGS_2[0].mappings[0],
        34: MAPPINGS_2[0].mappings[4],
        35: MAPPINGS_2[0].mappings[1],
        36: MAPPINGS_2[0].mappings[5],
        37: MAPPINGS_2[0].mappings[2]},
    ]
    mgr.register_mappings(MAPPINGS_2)
    assert sorted(
        mgr.mappings_by_controller_id, key=lambda d: sorted(d.keys())
    ) == sorted(expected, key=lambda d: sorted(d.keys()))
