
from __future__ import annotations

from asyncio import Event
from asyncio import sleep

from jamovi.server.jamovi_pb2 import ComsMessage
from jamovi.server.jamovi_pb2 import AnalysisRequest

from jamovi.server.utils import req_str
from jamovi.server.logging import logger

from .error import create_error_results


class DummyStreamReader:

    _callbacks: dict

    def __init__(self, callbacks: dict):
        self._callbacks = callbacks

    async def readexactly(self, n: int) -> bytes:
        return await self._callbacks['readexactly'](n)


class DummyStreamWriter:

    _callbacks: dict

    def __init__(self, callbacks: dict):
        self._callbacks = callbacks

    def write(self, payload: bytes) -> None:
        return self._callbacks['write'](payload)

    async def drain(self):
        pass


class DummyProcess:

    stdin: DummyStreamWriter
    stdout: DummyStreamReader
    stderr: None

    _request: AnalysisRequest | None
    _request_received: Event
    _stopped: Event

    def __init__(self):
        self.stdin = DummyStreamWriter({
            'write': self._write,
        })
        self.stdout = DummyStreamReader({
            'readexactly': self._readexactly,
        })
        self._request_received = Event()
        self._stopped = Event()

    async def wait(self) -> None:
        await self._stopped.wait()

    def kill(self) -> None:
        self._stopped.set()

    def terminate(self) -> None:
        self._stopped.set()

    async def _readexactly(self, n: int) -> bytes:
        await self._request_received.wait()

        results = create_error_results(self._request, 'Analysis worked!')
        results_bytes: bytes = results.SerializeToString()

        message = ComsMessage()
        message.payload = results_bytes
        message.payloadType = 'AnalysisResponse'
        message_bytes: bytes = message.SerializeToString()

        if n == 4:
            await sleep(1)
            message_size = len(message_bytes)
            message_size_bytes = message_size.to_bytes(4, 'little')
            return message_size_bytes
        else:
            self._request_received.clear()
            return message_bytes

    def _write(self, payload: bytes) -> None:
        if len(payload) == 4:
            return

        message = ComsMessage()
        message.ParseFromString(payload)

        request = AnalysisRequest()
        request.ParseFromString(message.payload)
        self._request = request
        self._request_received.set()

        logger.debug('Received request {}', lambda: req_str(request))
