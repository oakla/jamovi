
from __future__ import annotations

from duckdb import connect
from duckdb import DuckDBPyConnection

from .store import Store
from .duckdataset import DuckDataSet


class DuckStore(Store):
    ''' a store for data sets based on a duckdb database '''

    _db: DuckDBPyConnection | None
    _attached: bool

    @staticmethod
    def create(path: str) -> DuckStore:
        ''' create a new duckdb database to use as a store '''
        return DuckStore(path)

    def __init__(self, path: str):
        self._path = path
        self._db = None
        self._attached = False

    def attach(self):
        ''' attach to the database to make changes '''
        if self._attached:
            raise ValueError('Store already attached')
        self._attached = True
        # we don't actually attach to the db until we need to

    def detach(self):
        ''' detach from the database (and flush to disk) '''
        if not self._attached:
            raise ValueError('Store not attached')
        if self._db:
            self._db.close()
            self._db = None
        self._attached = False

    def create_dataset(self) -> 'DuckDataSet':
        return DuckDataSet.create(self)

    def retrieve_dataset(self) -> 'DuckDataSet':
        raise NotImplementedError

    def execute(self, query: object, params: object=None, multiple_parameter_sets=False):
        ''' execute SQL in the duckdb database '''
        if not self._attached:
            raise ValueError('Store not attached')
        if self._db is None:
            self._db = connect(self._path)
        return self._db.execute(query, params, multiple_parameter_sets)

    def close(self) -> None:
        pass
