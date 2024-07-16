"""Pytest fixtures to use in the tests."""

from os import path
from tempfile import TemporaryDirectory
from typing import AsyncIterable

import pytest
import pytest_asyncio

from jamovi.server.engine import EngineFactory
from jamovi.server import dataset
from jamovi.server.pool import Pool


@pytest.fixture
def temp_dir() -> str:
    with TemporaryDirectory() as temp:
        yield temp


@pytest.fixture
def shared_memory_store(temp_dir: str) -> dataset.Store:
    temp_file = path.join(temp_dir, "fred.mm")
    store = dataset.StoreFactory.create(temp_file, "shmem")
    yield store
    store.close()


@pytest.fixture
def duckdb_store(temp_dir: str) -> dataset.Store:
    temp_file = path.join(temp_dir, "fred.duckdb")
    store = dataset.StoreFactory.create(temp_file, "duckdb")
    yield store
    store.close()


@pytest.fixture
def empty_dataset(shared_memory_store: dataset.Store) -> dataset.DataSet:
    return shared_memory_store.create_dataset()


@pytest.fixture
def empty_column(empty_dataset: dataset.DataSet) -> dataset.Column:
    return empty_dataset.append_column("fred")


@pytest_asyncio.fixture
async def analysis_pool(temp_dir: str) -> AsyncIterable[Pool]:
    pool = Pool(1)
    engine_manager = EngineFactory.create('duckdb', temp_dir, pool, {})
    await engine_manager.start()
    yield pool
    await engine_manager.stop()
