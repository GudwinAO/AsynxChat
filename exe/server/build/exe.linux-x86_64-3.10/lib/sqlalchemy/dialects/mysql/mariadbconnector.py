# mysql/mariadbconnector.py
# Copyright (C) 2005-2021 the SQLAlchemy authors and contributors
# <see AUTHORS file>
#
# This module is part of SQLAlchemy and is released under
# the MIT License: http://www.opensource.org/licenses/mit-license.php

"""

.. dialect:: mysql+mariadbconnector
    :name: MariaDB Connector/Python
    :dbapi: mariadb
    :connectstring: mariadb+mariadbconnector://<user>:<password>@<host>[:<port>]/<dbname>
    :url: https://pypi.org/project/mariadb/

Driver Status
-------------

MariaDB Connector/Python enables Python programs to access MariaDB and MySQL
databases using an API which is compliant with the Python DB API 2.0 (PEP-249).
It is written in C and uses MariaDB Connector/C client library for client server
communication.

Note that the default driver for a ``mariadb://`` connection URI continues to
be ``mysqldb``. ``mariadb+mariadbconnector://`` is required to use this driver.

.. mariadb: https://github.com/mariadb-corporation/mariadb-connector-python

"""  # noqa
import re

from .base import MySQLCompiler
from .base import MySQLDialect
from .base import MySQLExecutionContext
from .base import MySQLIdentifierPreparer
from ... import sql
from ... import util

mariadb_cpy_minimum_version = (1, 0, 1)


class MySQLExecutionContext_mariadbconnector(MySQLExecutionContext):
    def create_server_side_cursor(self):
        return self._dbapi_connection.cursor(buffered=False)

    def create_default_cursor(self):
        return self._dbapi_connection.cursor(buffered=True)


class MySQLCompiler_mariadbconnector(MySQLCompiler):
    pass


class MySQLIdentifierPreparer_mariadbconnector(MySQLIdentifierPreparer):
    pass


class MySQLDialect_mariadbconnector(MySQLDialect):
    driver = "mariadbconnector"

    # set this to True at the module level to prevent the driver from running
    # against a backend that server detects as MySQL. currently this appears to
    # be unnecessary as MariaDB client libraries have always worked against
    # MySQL databases.   However, if this changes at some point, this can be
    # adjusted, but PLEASE ADD A TEST in test/dialect/mysql/test_dialect.py if
    # this change is made at some point to ensure the correct exception
    # is raised at the correct point when running the driver against
    # a MySQL backend.
    # is_mariadb = True

    supports_unicode_statements = True
    encoding = "utf8mb4"
    convert_unicode = True
    supports_sane_rowcount = True
    supports_sane_multi_rowcount = True
    supports_native_decimal = True
    default_paramstyle = "qmark"
    execution_ctx_cls = MySQLExecutionContext_mariadbconnector
    statement_compiler = MySQLCompiler_mariadbconnector
    preparer = MySQLIdentifierPreparer_mariadbconnector

    supports_server_side_cursors = True

    @util.memoized_property
    def _dbapi_version(self):
        if self.dbapi and hasattr(self.dbapi, "__version__"):
            return tuple(
                [
                    int(x)
                    for x in re.findall(
                        r"(\d+)(?:[-\.]?|$)", self.dbapi.__version__
                    )
                ]
            )
        else:
            return (99, 99, 99)

    def __init__(self, **kwargs):
        super(MySQLDialect_mariadbconnector, self).__init__(**kwargs)
        self.paramstyle = "qmark"
        if self.dbapi is not None:
            if self._dbapi_version < mariadb_cpy_minimum_version:
                raise NotImplementedError(
                    "The minimum required version for MariaDB "
                    "Connector/Python is %s"
                    % ".".join(str(x) for x in mariadb_cpy_minimum_version)
                )

    @classmethod
    def dbapi(cls):
        return __import__("mariadb")

    def is_disconnect(self, e, connection, cursor):
        if super(MySQLDialect_mariadbconnector, self).is_disconnect(
            e, connection, cursor
        ):
            return True
        elif isinstance(e, self.dbapi.Error):
            str_e = str(e).lower()
            return "not connected" in str_e or "isn't valid" in str_e
        else:
            return False

    def create_connect_args(self, url):
        opts = url.translate_connect_args()

        int_params = [
            "connect_timeout",
            "read_timeout",
            "write_timeout",
            "client_flag",
            "port",
            "pool_size",
        ]
        bool_params = [
            "local_infile",
            "ssl_verify_cert",
            "ssl",
            "pool_reset_connection",
        ]

        for key in int_params:
            util.coerce_kw_type(opts, key, int)
        for key in bool_params:
            util.coerce_kw_type(opts, key, bool)

        # FOUND_ROWS must be set in CLIENT_FLAGS to enable
        # supports_sane_rowcount.
        client_flag = opts.get("client_flag", 0)
        if self.dbapi is not None:
            try:
                CLIENT_FLAGS = __import__(
                    self.dbapi.__name__ + ".constants.CLIENT"
                ).constants.CLIENT
                client_flag |= CLIENT_FLAGS.FOUND_ROWS
            except (AttributeError, ImportError):
                self.supports_sane_rowcount = False
            opts["client_flag"] = client_flag
        return [[], opts]

    def _extract_error_code(self, exception):
        try:
            rc = exception.errno
        except:
            rc = -1
        return rc

    def _detect_charset(self, connection):
        return "utf8mb4"

    _isolation_lookup = set(
        [
            "SERIALIZABLE",
            "READ UNCOMMITTED",
            "READ COMMITTED",
            "REPEATABLE READ",
            "AUTOCOMMIT",
        ]
    )

    def _set_isolation_level(self, connection, level):
        if level == "AUTOCOMMIT":
            connection.autocommit = True
        else:
            connection.autocommit = False
            super(MySQLDialect_mariadbconnector, self)._set_isolation_level(
                connection, level
            )

    def do_begin_twophase(self, connection, xid):
        connection.execute(
            sql.text("XA BEGIN :xid").bindparams(
                sql.bindparam("xid", xid, literal_execute=True)
            )
        )

    def do_prepare_twophase(self, connection, xid):
        connection.execute(
            sql.text("XA END :xid").bindparams(
                sql.bindparam("xid", xid, literal_execute=True)
            )
        )
        connection.execute(
            sql.text("XA PREPARE :xid").bindparams(
                sql.bindparam("xid", xid, literal_execute=True)
            )
        )

    def do_rollback_twophase(
        self, connection, xid, is_prepared=True, recover=False
    ):
        if not is_prepared:
            connection.execute(
                sql.text("XA END :xid").bindparams(
                    sql.bindparam("xid", xid, literal_execute=True)
                )
            )
        connection.execute(
            sql.text("XA ROLLBACK :xid").bindparams(
                sql.bindparam("xid", xid, literal_execute=True)
            )
        )

    def do_commit_twophase(
        self, connection, xid, is_prepared=True, recover=False
    ):
        if not is_prepared:
            self.do_prepare_twophase(connection, xid)
        connection.execute(
            sql.text("XA COMMIT :xid").bindparams(
                sql.bindparam("xid", xid, literal_execute=True)
            )
        )


dialect = MySQLDialect_mariadbconnector
