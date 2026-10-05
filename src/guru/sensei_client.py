"""
gRPC client for connecting to SenseiService and subscribing to hardware events.
"""

import asyncio
import logging
import time
from typing import AsyncIterator

from .rpc import sensei_rpc_pb2, sensei_rpc_pb2_grpc
from . import observer


logger = logging.getLogger('SENSEI')

IDLING_TIMEOUT_S = 5


class SenseiClient:
    """Client for connecting to the Sensei gRPC service."""

    def __init__(self, server_address: str = "localhost:50051"):
        """
        Initialize the Sensei client.

        Args:
            server_address: Address of the gRPC server (host:port)
        """
        self.server_address = server_address
        self.channel = None
        self.stub = None
        self._streaming = False
        self._timeout_task: asyncio.Task | None = None
        self._last_event_time: float = 0.0

        observer.subscribe("ToggleLedRequest", self._update_led)
        observer.subscribe("PrintToMockDisplay", self._print_to_mock_display)

    async def connect(self) -> None:
        """Establish connection to the gRPC server."""
        logger.debug("Connecting to Sensei at %s", self.server_address)
        import grpc.aio
        self.channel = grpc.aio.insecure_channel(self.server_address)
        self.stub = sensei_rpc_pb2_grpc.SenseiControllerStub(self.channel)
        logger.debug("Connected to Sensei")

    async def disconnect(self) -> None:
        """Close the gRPC connection."""
        if self.channel:
            logger.debug("Disconnecting from Sensei")
            self._streaming = False
            await self.channel.close()
            self.channel = None
            self.stub = None

    async def _is_idling(self) -> None:
        try:
            await asyncio.sleep(IDLING_TIMEOUT_S)
            await observer.emit("Idle")
        except asyncio.CancelledError:
            return

    async def _idle_watcher(self) -> None:
        loop = asyncio.get_running_loop()
        while self._streaming:
            elapsed = loop.time() - self._last_event_time
            remaining = IDLING_TIMEOUT_S - elapsed
            if remaining <= 0:
                await observer.emit("Idle")
                self._last_event_time = loop.time()
                await asyncio.sleep(IDLING_TIMEOUT_S)
            else:
                await asyncio.sleep(remaining)

    async def stream_events(self) -> None:
        """
        Main TaskGroup task - streams events and emits via observer.
        Runs until _streaming is set to False.
        """
        try:
            if not self._streaming:
                logger.debug("Event stream not starting - _streaming is False")
                return
            loop = asyncio.get_running_loop()
            self._last_event_time = loop.time()
            asyncio.create_task(self._idle_watcher())

            logger.info("Starting event stream, subscribing to all events")
            async for event in self.subscribe_to_events():
                if not self._streaming:
                    logger.debug("Event stream stopping (streaming flag is False)")
                    break
                # Emit event to observer
                logger.debug("Received Sensei event: %s", event)
                t_recv = time.perf_counter()
                await observer.emit("UiEvent", event)
                self._last_event_time = loop.time()
                logger.debug(
                    "ctrl=%d %s → UiEvent dispatch complete: %.2fms",
                    event.controller_id,
                    event.WhichOneof("event"),
                    (time.perf_counter() - t_recv) * 1000,
                )
                
        except Exception as e:
            # Check if it's a gRPC error
            if hasattr(e, '__class__') and 'AioRpcError' in e.__class__.__name__:
                logger.error(f"gRPC error in event stream: {e}")
            else:
                logger.error(f"Unexpected error in event stream: {e}", exc_info=True)
        finally:
            logger.debug("Event stream ended")

    async def refresh_all_states(self) -> None:
        """
        Request current state of all controllers and build name->ID mapping.

        Returns:
            Dictionary mapping controller names to their IDs
        """
        if not self.stub:
            raise RuntimeError("Not connected to server. Call connect() first.")

        logger.debug("Requesting controller states via RefreshAllStates()")
        response = await self.stub.RefreshAllStates(sensei_rpc_pb2.GenericVoidValue())

    async def get_controller_map(self) -> dict:
        if not self.stub:
            raise RuntimeError("Not connected to server. Call connect() first.")
        controller_map = {}

        response = await self.stub.GetControllerMap(sensei_rpc_pb2.GenericVoidValue())

        for pot in response.pots:
            controller_map[pot.name] = pot.id
            logger.debug("Pot: %s -> ID %s", pot.name, pot.id)

        for switch in response.switches:
            controller_map[switch.name] = switch.id
            logger.debug("Switch: %s -> ID %s", switch.name, switch.id)

        for encoder in response.encoders:
            controller_map[encoder.name] = encoder.id
            logger.debug("Encoder: %s -> ID %s", encoder.name, encoder.id)

        for rotary in response.rotaries:
            controller_map[rotary.name] = rotary.id
            logger.debug("Rotary: %s -> ID %s", rotary.name, rotary.id)

        for led in response.leds:
            controller_map[led.name] = led.id
            logger.debug("Led: %s -> ID %s", led.name, led.id)

        logger.info(f"Discovered {len(controller_map)} controllers")
        await observer.emit("NewControllerMap", controller_map)
        return response

    async def subscribe_to_events(self, controller_ids: list[int] | None = None) -> AsyncIterator:
        """
        Subscribe to hardware events stream.

        Args:
            controller_ids: Optional list of controller IDs to filter events.
                          If None, subscribe to all controllers.

        Yields:
            Event messages from the server
        """
        if not self.stub:
            raise RuntimeError("Not connected to server. Call connect() first.")

        request = sensei_rpc_pb2.SubscribeRequest()
        if controller_ids:
            request.controller_ids.extend(controller_ids)
            logger.debug("Subscribing to events for controllers: %s", controller_ids)
        else:
            logger.debug("Subscribing to all controller events")

        try:
            async for event in self.stub.SubscribeToEvents(request):
                yield event
        except Exception as e:
            # Check if it's a gRPC error
            if hasattr(e, '__class__') and 'AioRpcError' in e.__class__.__name__:
                logger.error(f"gRPC error during event subscription: {e}")
            raise

    async def _update_led(self, led_id: int, active: bool) -> None:
        """
        Update the state of an LED.

        Args:
            led_id: ID of the LED to update
            active: Whether the LED should be on (True) or off (False)
        """
        if not self.stub:
            raise RuntimeError("Not connected to server. Call connect() first.")

        request = sensei_rpc_pb2.UpdateLedRequest(controller_id=led_id, active=active)
        await self.stub.UpdateLed(request)
        logger.debug(f"Updated LED {led_id} to {'active' if active else 'inactive'}")

    async def _print_to_mock_display(self, message: str) -> None:
        if not self.stub:
            raise RuntimeError("Not connected to server. Call connect() first.")

        request = sensei_rpc_pb2.WriteToDisplayRequest(data=message)
        await self.stub.WriteToDisplay(request)
        logger.debug(f"Printed {message} to display")


if __name__ == '__main__':
    sc = SenseiClient()
    print(asyncio.run(sc.get_controller_map()))
