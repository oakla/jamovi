
from uuid import uuid4

import pytest

from jamovi.server.pool import Pool
from jamovi.server.utils import ProgressStream
from jamovi.server.jamovi_pb2 import AnalysisRequest
from jamovi.server.jamovi_pb2 import AnalysisResponse

@pytest.mark.asyncio
@pytest.mark.timeout(2)
async def test_analysis(analysis_pool: Pool):
    request = AnalysisRequest()
    request.instanceId = str(uuid4())
    request.analysisId = 1
    request.ns = 'jmv'
    request.name = 'anova'

    stream: ProgressStream = analysis_pool.add(request)
    results: AnalysisResponse = await stream

    assert results.instanceId == request.instanceId
    assert results.analysisId == request.analysisId
