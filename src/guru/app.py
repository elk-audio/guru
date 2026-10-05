"""
Pedal Glue App - Bridge between hardware controllers and Sushi audio engine.

This application subscribes to gRPC events from hardware controllers and
routes them to Sushi parameters based on user-defined mappings.
"""

import asyncio
import logging
import signal
import sys
from pathlib import Path

from .sensei_client import SenseiClient
from .sushi_client import MappingError, TransportMode, SushiClient
from .mappings import MappingManager, MappingMode
from .presets import PresetManager
from . import id_cache

DEFAULT_SUSHI_ADDRESS = "localhost:51051"
if sys.platform == "win32":
    DEFAULT_SUSHI_ADDRESS = "localhost:510"

class ShutdownSignalException(Exception):
    """Exception raised by the shutdown signal monitoring Task"""

    pass


def setup_logging(level: int = logging.INFO) -> None:
    """Configure logging for the application."""
    logging.basicConfig(
        level=level,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )


class GlueApp:
    """This is the main app class. An application must instantiate one of those.
    It MUST also be initialized with self.initialize()"""

    def __init__(
        self,
        mappings: list[MappingMode] | None = None,
        sensei_address: str = "localhost:50051",
        sushi_address: str = DEFAULT_SUSHI_ADDRESS,
        sushi_transport = TransportMode.IPC,
        log_level: int = logging.INFO,
        id_cache_path: str | None = None,
    ):
        """
        Args:
            mappings: List of mapping objects (PluginParameterMapping, etc.)
            sensei_address: Address of the Sensei gRPC server
            sushi_address: Address of the Sushi gRPC server
            log_level: Logging level (e.g., logging.DEBUG, logging.INFO)
            id_cache_path: Path to persist resolved name→ID cache across restarts
        """
        self.mappings = mappings or []
        self.sensei_address = sensei_address
        self.sushi_address = sushi_address
        self._id_cache_path = Path(id_cache_path) if id_cache_path else None
        self._id_cache: dict | None = None

        setup_logging(log_level)
        self.logger = logging.getLogger("APP")
        self._shutdown_event = asyncio.Event()

        # Check if mappings are defined
        if not self.mappings:
            self.logger.warning(
                "No mappings defined. "
                "The app will run but won't control any parameters."
            )

        # Initialize clients (but don't connect yet)
        self.sensei_client = SenseiClient(self.sensei_address)
        self.mapping_manager = MappingManager()
        self.sushi_client = SushiClient(sushi_transport, self.sushi_address)
        self.preset_manager = PresetManager()

    def _setup_signal_handlers(self):
        """Setup asyncio-compatible signal handlers."""
        loop = asyncio.get_running_loop()

        def signal_handler():
            self.logger.info("Shutdown signal received, stopping...")
            self._shutdown_event.set()

        if sys.platform != "win32":
            for sig in (signal.SIGINT, signal.SIGTERM):
                loop.add_signal_handler(sig, signal_handler)

    async def initialize(self, subscribe_to_parameter_updates: bool = False) -> bool:
        """
        Initialize connections to Sensei and Sushi. This MUST be run before any calls to
        Sensei or Sushi are made, typically directly after instantiation.

        Returns:
            True if initialization succeeded, False otherwise.
        """
        self.logger.info("Starting Pedal Glue App")

        # Connect to Sensei client with retry
        self.logger.info("Initializing Sensei client")
        await self.sensei_client.connect()

        # Get caontroller name->ID mapping with retry
        self.logger.info("Fetching controller states")
        while not self._shutdown_event.is_set():
            try:
                await self.sensei_client.get_controller_map()
                break
            except Exception:
                self.logger.debug("Sensei unavailable. Retrying in 1s...")
                try:
                    await asyncio.wait_for(self._shutdown_event.wait(), timeout=1.0)
                    return False  # Shutdown requested during retry
                except asyncio.TimeoutError:
                    pass  # Continue retry

        # Connect to Sushi client
        self.logger.info("Initializing Sushi client")
        while not self._shutdown_event.is_set():
            if not await self.sushi_client.connect(
                subscribe_to_parameter_updates=subscribe_to_parameter_updates
            ):
                try:
                    await asyncio.wait_for(self._shutdown_event.wait(), timeout=1.0)
                    return False  # Shutdown requested during retry
                except asyncio.TimeoutError:
                    self.logger.debug("Retrying Sushi connection...")
                    pass  # Continue retry
            else:
                break

        if self._id_cache_path:
            self._id_cache = id_cache.load(self._id_cache_path)
            id_cache.wrap_controller(self.sushi_client.controller, self._id_cache)

        # Initialize mappings with Sushi
        if self.mappings:
            try:
                self.logger.info("Initializing mappings")
                await self.mapping_manager.initialize_mappings(self.mappings)
                self.mapping_manager.register_mappings(self.mappings)
            except MappingError:
                self.logger.error("Mapping initialization failed.")
                return False

        return True

    def save_id_cache(self) -> None:
        """Persist resolved IDs to disk. Call after all preset/mapping inits complete."""
        if self._id_cache_path and self._id_cache is not None:
            id_cache.save(self._id_cache_path, self._id_cache)

    async def run(self) -> int:
        """
        Run the application with async event loop and TaskGroup.

        Returns:
            Exit code (0 for success, 1 for failure).
        """
        self._setup_signal_handlers()

        try:
            # Run concurrent tasks
            self.sensei_client._streaming = True
            async with asyncio.TaskGroup() as tg:
                tg.create_task(self.sensei_client.stream_events())
                tg.create_task(self._wait_for_shutdown())
                tg.create_task(self._refresh_sensei())

        except* ShutdownSignalException as eg:
            # TaskGroup wraps exceptions in ExceptionGroup
            self.logger.info("Shutting down...")
        finally:
            await self.stop()

        return 0

    async def _refresh_sensei(self) -> None:
        """Triggers Sensei to fire events for all its api. Needed to get jack insertion statuses for instance"""
        await asyncio.sleep(
            1
        )  # This sleep is to ensure that sensei_client is already streaming events
        await self.sensei_client.refresh_all_states()

    async def _wait_for_shutdown(self):
        """Wait for shutdown signal."""
        await self._shutdown_event.wait()
        self.logger.debug("Shutdown event triggered")
        raise ShutdownSignalException

    async def stop(self) -> None:
        """Cleanup connections."""
        self.logger.debug("Cleaning up connections")
        if self.sensei_client:
            await self.sensei_client.disconnect()
        if self.sushi_client:
            self.sushi_client.disconnect()
        self.logger.debug("Shutdown complete")
