from abc import ABC, abstractmethod
from enum import Enum
from typing import Iterable

import pyodbc

from dbscripts.dbscripts import DBScript


class DBWriter:
    """
    ? Used to run database script objects (`DBScript`, `DBScripts`) against a connected database.
    """
    def __init__(self, conn: pyodbc.Connection):
        """
        Args:
            conn (pyodbc.Connection): the `pyodbc` connection object to execute queries with.
        """
        self.conn = conn
        self.cursor = conn.cursor()
    
    def execute_script(self, script: DBScript, raise_exceptions: bool = True) -> None:
        """
        ? Runs a database script object against the database.

        Args:
            script (DBScript): the database script object to run against the database.
            raise_exceptions (bool, optional): should I raise an exception if a script fails, or just ignore it and carry on? Defaults to True.

        Raises:
            pyodbc.Error: raised if raise_exceptions is `True` and an exception is met running the script.
        """
        try:
            self.cursor.execute(script.contents)
            self.conn.commit()
        except pyodbc.Error as e:
            if raise_exceptions:
                raise e
            
    def execute_scripts(self, scripts: Iterable[DBScript], raise_exceptions: bool = True) -> None:
        """
        ? Runs an iterable of database script objects against the database in order of the iterable. 
        
        * You can use a `DBScripts` object to reorder a scripts such that they are safe to execute in order without dependency issues.

        Args:
            scripts (Iterable[DBScript]): an iterable of database script objects.
            raise_exceptions (bool, optional): should I raise an exception if a script fails, or just ignore it and carry on? Defaults to True.

        Raises:
            pyodbc.Error: raised if raise_exceptions is `True` and an exception is met running the script.
        """
        for script in scripts:
            try:
                self.cursor.execute(script.contents)
                self.conn.commit()
            except pyodbc.Error as e:
                if raise_exceptions:
                    raise e


class IConnectionStringBuilder(ABC):
    @abstractmethod
    def set_driver(self, driver: str):
        pass

    @abstractmethod
    def set_server(self, server: str):
        pass

    @abstractmethod
    def set_database(self, database: str):
        pass

    @abstractmethod
    def set_user(self, user: str):
        pass

    @abstractmethod
    def set_password(self, password: str):
        pass

    @abstractmethod
    def set_options(self, options: dict):
        pass

    @abstractmethod
    def build(self) -> str:
        pass


class MSSQLConnectionStringBuilder(IConnectionStringBuilder):
    """
    ? A connection string builder for Microsoft SQL Server.
    """
    def __init__(self):
        self.connection_string = {}

    def set_driver(self, driver: str):
        self.connection_string["DRIVER"] = driver
        return self

    def set_server(self, server: str):
        self.connection_string["SERVER"] = server
        return self

    def set_database(self, database: str):
        self.connection_string["DATABASE"] = database
        return self

    def set_user(self, user: str):
        self.connection_string["UID"] = user
        return self

    def set_password(self, password: str):
        self.connection_string["PWD"] = password
        return self

    def set_options(self, options: dict):
        self.connection_string.update(options)
        return self

    def set_windows_authentication(self, use_windows_auth: bool = True):
        if use_windows_auth:
            self.connection_string["Trusted_Connection"] = "yes"
        return self

    def build(self) -> str:
        return ';'.join([f"{key}={value}" for key, value in self.connection_string.items()])


class DBTypes(Enum):
    """
    ? An enumerated type of supported database types.
    """
    MSSQL = 'mssql'


class ConnectionStringBuilderFactory:
    """
    ? A factory class for connection string builders.
    """
    @staticmethod
    def get_builder(db_type: DBTypes) -> IConnectionStringBuilder:
        if db_type == DBTypes.MSSQL:
            return MSSQLConnectionStringBuilder()
        else:
            raise ValueError(f"Unsupported database type: {db_type}")
