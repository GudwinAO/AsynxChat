# mysql/aiomysql.py
# Copyright (C) 2005-2021 the SQLAlchemy authors and contributors <see AUTHORS
# file>
#
# This module is part of SQLAlchemy and is released under
# the MIT License: http://www.opensource.org/licenses/mit-license.php
r"""
.. dialect:: mysql+aiomysql
    :name: aiomysql
    :dbapi: aiomysql
    :connectstring: mysql+aiomysql://user:password@host:port/dbname[?key=value&key=value...]
    :url: https://github.com/aio-libs/aiomysql

The aiomysql dialect is SQLAlchemy's second Python asyncio dialect.

Using a special asyncio mediation layer, the aiomysql dialect is usable
as the backend for the :ref:`SQLAlchemy asyncio <asyncio_toplevel>`
extension package.

This dialect should normally be used only with the
:func:`_asyncio.create_async_engine` engine creation function::

    from sqlalchemy.ext.asyncio import create_async_engine
    engine = create_async_engine("mysql+aiomysql://user:pass@hostname/dbname")

Unicode
-------

Please see :ref:`mysql_unicode` for current recommendations on unicode
handling.


"""  # noqa

from .pymysql import MySQLDialect_pymysql
from ... import pool
from ... import util
from ...util.concurrency import asyncio
from ...util.concurrency import await_fallback
from ...util.concurrency import await_only


class AsyncAdapt_aiomysql_cursor:
    server_side = False
    __slots__ = (
        "_adapt_connection",
        "_connection",
        "await_",
        "_cursor",
        "_rows",
    )

    def __init__(self, adapt_connection):
        self._adapt_connection = adapt_connection
        self._connection = adapt_connection._connection
        self.await_ = adapt_connection.await_

        cursor = self._connection.cursor()

        # see https://github.com/aio-libs/aiomysql/issues/543
        self._cursor = self.await_(cursor.__aenter__())
        self._rows = []

    @property
    def description(self):
        return self._cursor.description

    @property
    def rowcount(self):
        return self._cursor.rowcount

    @property
    def arraysize(self):
        return self._cursor.arraysize

    @arraysize.setter
    def arraysize(self, value):
        self._cursor.arraysize = value

    @property
    def lastrowid(self):
        return self._cursor.lastrowid

    def close(self):
        self._rows[:] = []

    def execute(self, operation, parameters=None):
        return self.await_(self._execute_async(operation, parameters))

    def executemany(self, operation, seq_of_parameters):
        return self.await_(
            self._executemany_async(operation, seq_of_parameters)
        )

    async def _execute_async(self, operation, parameters):
        async with self._adapt_connection._execute_mutex:
            if parameters is None:
                result = await self._cursor.execute(operation)
            else:
                result = await self._cursor.execute(operation, parameters)

            if not self.server_side:
                # aiomysql has a "fake" async result, so we have to pull it out
                # of that here since our default result is not async.
                # we could just as easily grab "_rows" here and be done with it
                # but this is safer.
                self._rows = list(await self._cursor.fetchall())
            return result

    async def _executemany_async(self, operation, seq_of_parameters):
        async with self._adapt_connection._execute_mutex:
            return await self._cursor.executemany(operation, seq_of_parameters)

    def setinputsizes(self, *inputsizes):
        pass

    def __iter__(self):
        while self._rows:
            yield self._rows.pop(0)

    def fetchone(self):
        if self._rows:
            return self._rows.pop(0)
        else:
            return None

    def fetchmany(self, size=None):
        if size is None:
            size = self.arraysize

        retval = self._rows[0:size]
        self._rows[:] = self._rows[size:]
        return retval

    def fetchall(self):
        retval = self._rows[:]
        self._rows[:] = []
        return retval


class AsyncAdapt_aiomysql_ss_cursor(AsyncAdapt_aiomysql_cursor):
    __slots__ = ()
    server_side = True

    def __init__(self, adapt_connection):
        self._adapt_connection = adapt_connection
        self._connection = adapt_connection._connection
        self.await_ = adapt_connection.await_

        cursor = self._connection.cursor(
            adapt_connection.dbapi.aiomysql.SSCursor
        )

        self._cursor = self.await_(cursor.__aenter__())

    def close(self):
        if self._cursor is not None:
            self.await_(self._cursor.close())
            self._cursor = None

    def fetchone(self):
        return self.await_(self._cursor.fetchone())

    def fetchmany(self, size=None):
        return self.await_(self._cursor.fetchmany(size=size))

    def fetchall(self):
        return self.await_(self._cursor.fetchall())


class AsyncAdapt_aiomysql_connection:
    await_ = staticmethod(await_only)
    __slots__ = ("dbapi", "_connection", "_execute_mutex")

    def __init__(self, dbapi, connection):
        self.dbapi = dbapi
        self._connection = connection
        self._execute_mutex = asyncio.Lock()

    def ping(self, reconnect):
        return self.await_(self._connection.ping(reconnect))

    def character_set_name(self):
        return self._connection.character_set_name()

    def autocommit(self, value):
        self.await_(self._connection.autocommit(value))

    def cursor(self, server_side=False):
        if server_side:
            return AsyncAdapt_aiomysql_ss_cursor(self)
        else:
            return AsyncAdapt_aiomysql_cursor(self)

    def rollback(self):
        self.await_(self._connection.rollback())

    def commit(self):
        self.await_(self._connection.commit())

    def close(self):
        # it's not awaitable.
        self._connection.close()


class AsyncAdaptFallback_aiomysql_connection(AsyncAdapt_aiomysql_connection):
    __slots__ = ()

    await_ = staticmethod(await_fallback)


class AsyncAdapt_aiomysql_dbapi:
    def __init__(self, aiomysql, pymysql):
        self.aiomysql = aiomysql
        self.pymysql = pymysql
        self.paramstyle = "format"
        self._init_dbapi_attributes()

    def _init_dbapi_attributes(self):
        for name in (
            "Warning",
            "Error",
            "InterfaceError",
            "DataError",
            "DatabaseError",
            "OperationalError",
            "InterfaceError",
            "IntegrityError",
            "ProgrammingError",
            "InternalError",
            "NotSupportedError",
        ):
            setattr(self, name, getattr(self.aiomysql, name))

        for name in (
            "NUMBER",
            "STRING",
            "DATETIME",
            "BINARY",
            "TIMESTAMP",
            "Binary",
        ):
            setattr(self, name, getattr(self.pymysql, name))

    def connect(self, *arg, **kw):
        async_fallback = kw.pop("async_fallback", False)

        if util.asbool(async_fallback):
            return AsyncAdaptFallback_aiomysql_connection(
                self,
                await_fallback(self.aiomysql.connect(*arg, **kw)),
            )
        else:
            return AsyncAdapt_aiomysql_connection(
                self,
                await_only(self.aiomysql.connect(*arg, **kw)),
            )


class MySQLDialect_aiomysql(MySQLDialect_pymysql):
    driver = "aiomysql"

    supports_server_side_cursors = True
    _sscursor = AsyncAdapt_aiomysql_ss_cursor

    is_async = True

    @classmethod
    def dbapi(cls):
        return AsyncAdapt_aiomysql_dbapi(
            __import__("aiomysql"), __import__("pymysql")
        )

    @classmethod
    def get_pool_class(cls, url):

        async_fallback = url.query.get("async_fallback", False)

        if util.asbool(async_fallback):
            return pool.FallbackAsyncAdaptedQueuePool
        else:
            return pool.AsyncAdaptedQueuePool

    def create_connect_args(self, url):
        return super(MySQLDialect_aiomysql, self).create_connect_args(
            url, _translate_args=dict(username="user", database="db")
        )

    def is_disconnect(self, e, connection, cursor):
        if super(MySQLDialect_aiomysql, self).is_disconnect(
            e, connection, cursor
        ):
            return True
        else:
            str_e = str(e).lower()
            return "not connected" in str_e

    def _found_rows_client_flag(self):
        from pymysql.constants import CLIENT

        return CLIENT.FOUND_ROWS


dialect = MySQLDialect_aiomysql
