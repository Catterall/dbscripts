from abc import ABC, abstractmethod
import os
import re
from enum import IntEnum
from typing import List, Dict


class ImproperDBScriptFormatError(Exception):
    """Raised when DBScript cannot properly read the provided script file. Usually a formatting issue."""
    pass


class SQLObjectScriptTypes(IntEnum):
    """The different types of recognized SQL object scripts."""
    TABLE = 0
    VIEW = 1
    TRIGGER = 2
    STORED_PROC = 3
    SCALAR_FUNC = 4
    TABLE_FUNC = 5


class ISQLDialect(ABC):
    """An interface for different SQL dialects, such as `MSSQL_Dialect` (Transact-SQL)"""
    @abstractmethod
    def get_object_name(self, script_content: str) -> str | None:
        """Get the object name of the object script."""
        pass

    @abstractmethod
    def get_script_type(self, script_content: str) -> SQLObjectScriptTypes:
        """Get the object type of the object script. e.g. `SQLObjectScriptTypes.TABLE`"""
        pass


class MSSQL_Dialect(ISQLDialect):
    """The dialect for Microsoft SQL Server's SQL variation, Transact-SQL."""
    MSSQL_TABLE_PATTERN = re.compile(r'TABLE\s+(\[[a-zA-Z]+\])?\.?\[?([a-zA-Z]+)\]?', re.IGNORECASE)
    MSSQL_VIEW_PATTERN = re.compile(r'VIEW\s+(\[[a-zA-Z]+\])?\.?\[?([a-zA-Z]+)\]?', re.IGNORECASE)
    MSSQL_TRIGGER_PATTERN = re.compile(r'TRIGGER\s+(\[[a-zA-Z]+\])?\.?\[?([a-zA-Z]+)\]?', re.IGNORECASE)
    MSSQL_STORED_PROC_PATTERN = re.compile(r'PROCEDURE\s+(\[[a-zA-Z]+\])?\.?\[?([a-zA-Z]+)\]?', re.IGNORECASE)
    MSSQL_FUNCTION_PATTERN = re.compile(r'FUNCTION\s+(\[[a-zA-Z]+\])?\.?\[?([a-zA-Z]+)\]?', re.IGNORECASE)
    MSSQL_SCALAR_F_PATTERN = re.compile(r'RETURNS\s+\b(INT|VARCHAR|FLOAT|DATETIME|CHAR|BIT|DECIMAL|NUMERIC|TEXT|NVARCHAR|BIGINT|SMALLINT|TINYINT|BINARY)\b', re.IGNORECASE)

    def get_object_name(self, script_content: str) -> str | None:
        if (m := re.search(self.MSSQL_TABLE_PATTERN, script_content)) is not None:
            return m.group(2)
        elif (m := re.search(self.MSSQL_VIEW_PATTERN, script_content)) is not None:
            return m.group(2)
        elif (m := re.search(self.MSSQL_TRIGGER_PATTERN, script_content)) is not None:
            return m.group(2)
        elif (m := re.search(self.MSSQL_STORED_PROC_PATTERN, script_content)) is not None:
            return m.group(2)
        elif (m := re.search(self.MSSQL_FUNCTION_PATTERN, script_content)) is not None:
            return m.group(2)
        return None

    def get_script_type(self, script_content: str) -> SQLObjectScriptTypes | None:
        if re.search(self.MSSQL_TABLE_PATTERN, script_content):
            return SQLObjectScriptTypes.TABLE
        elif re.search(self.MSSQL_VIEW_PATTERN, script_content):
            return SQLObjectScriptTypes.VIEW
        elif re.search(self.MSSQL_TRIGGER_PATTERN, script_content):
            return SQLObjectScriptTypes.TRIGGER
        elif re.search(self.MSSQL_STORED_PROC_PATTERN, script_content):
            return SQLObjectScriptTypes.STORED_PROC
        elif re.search(self.MSSQL_FUNCTION_PATTERN, script_content):
            if re.search(self.MSSQL_SCALAR_F_PATTERN, script_content):
                return SQLObjectScriptTypes.SCALAR_FUNC
            else:
                return SQLObjectScriptTypes.TABLE_FUNC
        return None


class DBScript:
    def __init__(self, path: str, sql_dialect: ISQLDialect):
        """Represents a database script - a script to create, modify, or delete database objects. e.g. `CREATE PROCEDURE ...`

        Args:
            path (str): the path to the DB script.
            sql_dialect (ISQLDialect): the dialect of SQL used to generate the script.

        Raises:
            OSError: raised if the script could not be found.
        """
        if not os.path.exists(path):
            raise OSError(f'The path provided, "{path}", could not be found.')
        self.path = path
        self.sql_dialect = sql_dialect
        self.dependencies: List[DBScript] = []
        self._read_content()

    def _read_content(self):
        """Reads the contents of the script, figuring out the object name and the type of object the script is for.

        Raises:
            ImproperDBScriptFormatError: raised if the object name and type could not be determined, usually due to an incorrect ISQLDialect provided.
        """
        with open(self.path, 'r') as f:
            self.contents = f.read()
        self.obj_name = self.sql_dialect.get_object_name(self.contents)
        self.script_type = self.sql_dialect.get_script_type(self.contents)
        if self.obj_name is None or self.script_type is None:
            raise ImproperDBScriptFormatError('Could not determine the object name and script type from the provided .sql file.')


class DBScripts:
    def __init__(self, sql_dialect: ISQLDialect):
        """
        Represents a collection of database scripts, allowing for dependency calculation 
        and ordering of scripts such that execution is in a safe order with respect to dependencies.

        Args:
            sql_dialect (ISQLDialect): the dialect of SQL used to generate the scripts.
        """
        self.scripts: List[DBScript] = []
        self.obj_name_instance_mapping: Dict[str, DBScript] = {}
        self.sql_dialect = sql_dialect

    def append(self, script: DBScript) -> None:
        """
        Adds a script to the collection, updating the object name instance mapping. 
        # Use this over self.scripts.append!
        """
        self.scripts.append(script)
        self.obj_name_instance_mapping[script.obj_name] = script

    def populate_from_dir(self, dir: str) -> None:
        """Populates the collection with all `.sql` files in a given directory.

        Args:
            dir (str): the directory to walk over for `.sql` files.

        Raises:
            OSError: raised if the directory provided could not be found.
        """
        if not os.path.exists(dir):
            raise OSError(f'The directory provided, "{dir}", could not be found.')
        for _, _, filenames in os.walk(dir):
            for filename in filenames:
                if filename.endswith('.sql'):
                    script = DBScript(os.path.join(dir, filename), self.sql_dialect)
                    self.append(script)
    
    def calculate_dependencies(self) -> None:
        """
        Looks at the scripts in the collection and attempts to determine the dependency structure,
        populating each script object's dependency array if necessary.
        """
        encountered_scripts: List[DBScript] = []
        
        def populate_script_dependencies(script: DBScript):
            if script.dependencies:
                return
            for obj_name in self.obj_name_instance_mapping.keys():
                if obj_name in script.contents and obj_name != script.obj_name:
                    script.dependencies.append(self.obj_name_instance_mapping[obj_name])
                    populate_script_dependencies(self.obj_name_instance_mapping[obj_name])
                    encountered_scripts.append(script)
                    
        for script in self.scripts:
            if script not in encountered_scripts:
                populate_script_dependencies(script)
    
    def order_by_safe_execution(self) -> List[DBScript]:
        """
        Uses the script object's dependency arrays to determine a new order of
        the scripts list that is safe to execute without running into missing
        dependency issues.
        """
        new_order: List[DBScript] = []
        
        def reorder_callback(script: DBScript):
            if script in new_order:
                return
            if not script.dependencies:
                new_order.append(script)
            else:
                for dependency in script.dependencies:
                    reorder_callback(dependency)
                new_order.append(script)
        
        for script in self.scripts:
            reorder_callback(script)
        return new_order
