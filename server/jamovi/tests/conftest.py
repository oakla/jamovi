"""Pytest fixtures to use in the tests."""

from os import path
from tempfile import TemporaryDirectory

from typing import Iterator

import pytest

from jamovi.server.dataset import StoreFactory
from jamovi.server.dataset import Store
from jamovi.server.dataset import DataSet
from jamovi.server.dataset import Column


@pytest.fixture
def temp_dir() -> Iterator[str]:
    with TemporaryDirectory() as temp:
        yield temp


@pytest.fixture
def shared_memory_store(temp_dir: str) -> Iterator[Store]:
    temp_file = path.join(temp_dir, "fred.mm")
    store = StoreFactory.create(temp_file, "shmem")
    yield store
    store.close()


@pytest.fixture
def duckdb_store(temp_dir: str) -> Iterator[Store]:
    temp_file = path.join(temp_dir, "fred.duckdb")
    store = StoreFactory.create(temp_file, "duckdb")
    yield store
    store.close()


@pytest.fixture
def empty_dataset(duckdb_store: Store) -> Iterator[DataSet]:
    dataset = duckdb_store.create_dataset()
    dataset.attach()
    yield dataset
    dataset.detach()


@pytest.fixture
def empty_column(empty_dataset: DataSet) -> Column:
    return empty_dataset.append_column("fred")


@pytest.fixture
def simple_dataset(empty_dataset: DataSet) -> DataSet:
    ds = empty_dataset
    ds.append_column("fred")
    ds.append_column("jim")
    ds.append_column("bob")
    return ds
