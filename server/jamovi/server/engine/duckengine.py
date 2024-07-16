
from typing import TypeVar
from typing import Generic
from typing import Iterator

import sys
import itertools

from asyncio import Event
from asyncio import Queue
from asyncio import wait_for
from asyncio import wait
from asyncio import FIRST_COMPLETED
from asyncio import create_task
from asyncio import Task
from asyncio.subprocess import create_subprocess_exec
from asyncio.subprocess import Process
from asyncio.subprocess import PIPE
from asyncio import TimeoutError

from dataclasses import dataclass

from jamovi.server.jamovi_pb2 import AnalysisRequest
from jamovi.server.jamovi_pb2 import AnalysisResponse
from jamovi.server.jamovi_pb2 import ComsMessage
from jamovi.server.jamovi_pb2 import Status as MessageStatus

from jamovi.server.logging import logger
from jamovi.server.utils import req_str
from jamovi.server.utils import ProgressStream

from .error import create_error_results
from .dummy import DummyProcess as Process

MESSAGE_COMPLETE = MessageStatus.Value('COMPLETE')
MESSAGE_ERROR = MessageStatus.Value('ERROR')
MESSAGE_IN_PROGRESS = MessageStatus.Value('IN_PROGRESS')


@dataclass
class Analysis:
    ''' A request and corresponding results stream '''
    request: AnalysisRequest
    results: ProgressStream


T = TypeVar('T')


class SingleQueue(Queue, Generic[T]):
    ''' A queue which only allows a single item '''
    def __init__(self):
        super().__init__(maxsize=1)
    def put_nowait(self, item: T) -> None:
        if self.full():
            super().get_nowait()
        return super().put_nowait(item)
    async def get(self) -> T:
        return await super().get()


class DuckEngine:
    ''' An 'engine' process for running analyses '''
    _analysis: Analysis | None = None
    _queue: SingleQueue[Analysis]
    _process: Process | None = None
    _process_ended: Event
    _run_loop_task: Task
    _message_id: Iterator[int]
    _stopping: bool

    def __init__(self):
        self._queue = SingleQueue()
        self._message_id = iter(itertools.count())
        self._process_ended = Event()
        self._process_ended.set()
        self._stopping = False

    @property
    def current_request(self) -> AnalysisRequest:
        ''' The current request being processed '''
        if self._analysis is None:
            return None
        return self._analysis.request

    async def start(self) -> None:
        ''' Start the worker process, and begin processing requests/results '''
        assert self._process is None

        # self._process = await create_subprocess_exec(sys.executable, '-m', 'jamovi.server.worker', stdin=PIPE, stdout=PIPE, stderr=None)
        self._process = Process()
        logger.debug('Engine process started')
        self._process_ended.clear()
        self._run_loop_task = create_task(self._run_loop())

    async def restart(self) -> None:
        ''' Restart the worker process '''
        await self.stop()
        await self.start()

    def run_analysis(self, request: AnalysisRequest, results_stream: ProgressStream) -> None:
        ''' Run the analysis on this worker '''
        logger.debug('Worker received request {}', lambda: req_str(request))
        if self._queue.full():
            prev: Analysis = self._queue.get_nowait()
            self._cancel(prev)
        analysis = Analysis(request, results_stream)
        self._queue.put_nowait(analysis)

    def _cancel(self, analysis: Analysis) -> None:
        if analysis.results.done():
            return
        results = create_error_results(analysis.request, 'This analysis has been cancelled')
        analysis.results.set_result(results)

    async def _abort_current(self) -> None:
        # abort the current analysis
        if self._analysis is None:
            return
        self._cancel(self._analysis)
        self._analysis = None

        # TODO
        # await ... send something to engine to abort
        # if it doesn't abort quickly, then terminate it
        # await self.restart()

    async def _run_loop(self) -> None:
        # run loop, handles all the sub tasks
        receive_analysis = create_task(self._receive_analysis())
        receive_results = create_task(self._receive_results())
        process_ended = create_task(self._wait_ended())
        pending = { receive_analysis, receive_results, process_ended }

        try:
            while True:
                done, pending = await wait(pending, return_when=FIRST_COMPLETED)

                if receive_analysis in done:
                    analysis = receive_analysis.result()
                    await self._send_analysis(analysis)

                    receive_analysis = create_task(self._receive_analysis())
                    pending.add(receive_analysis)

                if receive_results in done:
                    results, complete = receive_results.result()
                    self._send_results(results, complete)

                    receive_results = create_task(self._receive_results())
                    pending.add(receive_results)

                if process_ended in done:
                    self._process_ended.set()
                    break

        except Exception as e:
            if not self._stopping:
                logger.exception(e)
        finally:
            for task in pending:
                task.cancel()

        if not self._process_ended.is_set():
            await self.stop()

        if not self._stopping:
            await self.start()


    async def _send_analysis(self, analysis: Analysis) -> None:
        # send the analysis to the worker process
        assert self._process is not None
        assert self._process.stdin is not None

        if self._analysis is not None:
            await self._abort_current()

        self._analysis = analysis
        request_bytes: bytes = self._analysis.request.SerializeToString()

        message = ComsMessage()
        message.id = next(self._message_id)
        message.payload = request_bytes
        message.payloadType = 'AnalysisRequest'

        message_bytes = message.SerializeToString()

        message_size = len(message_bytes)
        message_size_bytes: bytes = message_size.to_bytes(4, 'little')
        self._process.stdin.write(message_size_bytes)
        self._process.stdin.write(message_bytes)
        await self._process.stdin.drain()

    async def _receive_analysis(self) -> Analysis:
        # wait for an analysis to be received
        return await self._queue.get()

    def _send_results(self, results: AnalysisResponse, complete: bool):
        # send the results to the analysis
        if (self._analysis is not None
                and results.instanceId == self.current_request.instanceId
                and results.analysisId == self.current_request.analysisId
                and results.revision == self.current_request.revision):
            if not complete:
                self._analysis.results.write(results)
            else:
                self._analysis.results.set_result(results)
                self._analysis = None

    async def _receive_results(self) -> tuple[AnalysisResponse, bool]:
        # wait for results and return them
        assert self._process is not None
        payload_size_bytes = await self._process.stdout.readexactly(4)
        payload_size = int.from_bytes(payload_size_bytes, 'little')
        payload = await self._process.stdout.readexactly(payload_size)

        message = ComsMessage()
        message.ParseFromString(payload)

        complete = (message.status != MESSAGE_IN_PROGRESS)
        results = AnalysisResponse()
        results.ParseFromString(message.payload)

        return (results, complete)

    async def _wait_ended(self):
        # wait for the engine process to finish
        assert self._process is not None
        process_ended = create_task(self._process.wait())
        process_abandoned = create_task(self._process_ended.wait())
        done, pending = await wait({ process_ended, process_abandoned }, return_when=FIRST_COMPLETED)
        if process_ended in done:
            self._process_ended.set()
        for task in pending:
            task.cancel()

    async def stop(self):
        ''' stop the engine process '''

        if self._stopping:
            await self._process_ended.wait()
            return

        assert self._process is not None

        # flag indicating intentional stop
        self._stopping = True

        logger.debug('Terminating engine')
        try:
            self._process.terminate()
        except ProcessLookupError:
            pass  # already terminated
        except Exception as e:
            logger.exception(e)

        try:
            await wait_for(self._process_ended.wait(), 1)
        except TimeoutError:
            pass
        else:
            logger.debug('Terminated engine')
            return

        # kill the engine process
        logger.debug('Killing engine')

        try:
            self._process.kill()
        except ProcessLookupError:
            pass  # already terminated
        except Exception as e:
            logger.exception(e)

        # abandon
        self._process_ended.set()
