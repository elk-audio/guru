"""
Pytest configuration and shared fixtures.
"""

import sys
from pathlib import Path

# Add project root to Python path
project_root = Path(__file__).parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

import pytest
from unittest.mock import MagicMock

from guru.testing import FakeSushiController


@pytest.fixture
def fake_sushi() -> FakeSushiController:
    """A FakeSushiController seeded with a couple of example plugins, for tests
    that need a real (fake) SushiController rather than a MagicMock."""
    return FakeSushiController(
        tracks={"TRACK": 0},
        processors={"GxVintageFuzzMaster": 0},
    )


@pytest.fixture
def mock_sushi_controller():
    """Create a mock SushiController for testing."""
    mock_sc = MagicMock()
    mock_sc.audio_graph.get_track_id.return_value = 1
    mock_sc.audio_graph.get_processor_id.return_value = 2
    mock_sc.parameters.get_parameter_id.return_value = 3
    return mock_sc


@pytest.fixture
def mock_controller_map():
    """Create a sample controller name->ID mapping."""
    return {
        "POT1": 1,
        "POT2": 2,
        "SW1": 10,
        "SW2": 11,
        "ENC1": 20,
    }


@pytest.fixture
def mock_grpc_event():
    """Create a mock gRPC Event object."""
    event = MagicMock()
    event.WhichOneof.return_value = "analog_ev"
    event.analog_ev.controller_id = 1
    event.analog_ev.value = 0.5
    event.analog_ev.timestamp = 1234567890
    return event
