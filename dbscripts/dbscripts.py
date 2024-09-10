import os
import re
from abc import ABC, abstractmethod
from collections import deque, defaultdict
from typing import List, Dict


class ImproperDBScriptFormatError(Exception):
    """Raised when DBScript cannot properly read the provided script file. Usually a formatting issue."""
    pass


class CyclicalDependenciesError(Exception):
    """Raised when cyclical dependencies are encountered, which should not be possible for a set of database scripts."""
    pass


class ISQLDialect(ABC):
    """An interface for different SQL dialects, such as `MSSQL_Dialect` (Transact-SQL)."""
    @abstractmethod
    def strip_comments_and_strings(script_content: str) -> str:
        """Removes comments and string identifiers from the script."""
        pass
    
    @abstractmethod
    def get_object_name(self, script_content: str) -> str | None:
        """Get the object name of the object script."""
        pass

    @abstractmethod
    def is_valid_reference(self, obj_name: str, script: "DBScript") -> bool:
        """
        Determine whether an object name in a script is a valid reference. Attempts
        to avoid false positives.
        """
        pass


class MSSQL_Dialect(ISQLDialect):
    """The dialect for Microsoft SQL Server's SQL variation, Transact-SQL."""
    MSSQL_OBJECT_PATTERN = re.compile(
        r'(?:CREATE|ALTER|CREATE\s+OR\s+ALTER)\s+(?:PROCEDURE|TABLE|VIEW|FUNCTION|TRIGGER)\s+(?:\[(\w+)\]\.)?\[(\w+)\]',
        re.IGNORECASE
    )

    @staticmethod
    def strip_comments_and_strings(script_content: str) -> str:
        script_content = re.sub(r'--.*', '', script_content)
        script_content = re.sub(r'/\*.*?\*/', '', script_content, flags=re.DOTALL)
        script_content = re.sub(r"'([^']*)'", '', script_content)
        script_content = re.sub(r'"([^"]*)"', '', script_content)
        return script_content

    def is_valid_reference(self, obj_name: str, script: "DBScript") -> bool:
        processed_script = self.strip_comments_and_strings(script.contents)
        pattern = re.compile(rf'\b(?:dbo\.)?{re.escape(obj_name)}\b', re.IGNORECASE)
        valid_context_keywords = ['JOIN', 'FROM', 'INTO', 'UPDATE', 'DELETE', 'INSERT', 'EXEC', 'CALL']
        for keyword in valid_context_keywords:
            if re.search(rf'{keyword}\s+{pattern.pattern}', processed_script, re.IGNORECASE):
                return True
        return False

    def get_object_name(self, script_content: str) -> str | None:
        match = re.search(self.MSSQL_OBJECT_PATTERN, script_content)
        return match.group(2) if match else None


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
        if self.obj_name is None:
            raise ImproperDBScriptFormatError(f'Could not determine the object name from the provided .sql file at "{self.path}".')


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
        """Creates a graph and uses Khan's Algorithm to calculate the dependencies for the script objects.

        Raises:
            CyclicalDependenciesError: raised if the resulting safe execution order is different in length to the original scripts list.
        """
        graph = defaultdict(list)
        in_degree = defaultdict(int)

        for script in self.scripts:
            in_degree[script.obj_name] = 0
            for obj_name in self.obj_name_instance_mapping.keys():
                if obj_name != script.obj_name and self.sql_dialect.is_valid_reference(obj_name, script):
                    graph[obj_name].append(script.obj_name)
                    in_degree[script.obj_name] += 1

        self.safe_execution_order = []
        queue = deque([script for script in self.scripts if in_degree[script.obj_name] == 0])

        while queue:
            current_script = queue.popleft()
            self.safe_execution_order.append(current_script)

            for dependent_obj_name in graph[current_script.obj_name]:
                in_degree[dependent_obj_name] -= 1
                if in_degree[dependent_obj_name] == 0:
                    queue.append(self.obj_name_instance_mapping[dependent_obj_name])

        if len(self.safe_execution_order) != len(self.scripts):
            raise CyclicalDependenciesError(f"Cyclic dependencies detected!")
    
    def order_by_safe_execution(self) -> List[DBScript]:
        """Returns the scripts list in an order such that running should avoid dependency issues.

        Returns:
            List[DBScript]: the reordered script list.
        """
        if not hasattr(self, 'safe_execution_order'):
            self.calculate_dependencies()
        return self.safe_execution_order
