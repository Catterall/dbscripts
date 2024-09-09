# dbscripts

dbscripts is a small Python package to quickly run several database object scripts against a database whilst avoiding dependency issues. I wrote this package at work after being asked to mindlessly ensure that a few hundred scripts were in the correct order when running :( 

### Supported Features

- As of now, as per my requirements at work, the package supports use of Microsoft SQL Server and that's about it. It supports table, view, trigger, scalar-function, table-function, and stored procedure object scripts (CREATE, ALTER, etc.).

> Other SQL dialects *may* be supported in the future, if I find the motivation to support them. However, given that this is currently just a helper package I use at work, probably not. But, just in case, I have tried to design the package to be as flexible as possible to any future dialects - feel free to fork if impatient.

---

## Basic Usage

### Connecting to a SQL Server database.
To connect to a SQL server database, create a `pyodbc.Connection` using your connection string as usual. For those who are unfamiliar with the `pyodbc` module, I have attempted to create a connection string builder that will hopefully abstract away its usage.

```py
import pyodbc

from dbscripts.dbwriter import ConnectionStringBuilderFactory, DBTypes

builder = ConnectionStringBuilderFactory.get_builder(DBTypes.MSSQL)

connection_string = (
    builder.set_driver("{DRIVER}")
            .set_server("SERVER")
            .set_database("DATABASE_NAME")
            .set_windows_authentication(True)  # Include this line if using Windows Auth.
            .set_options({"Encrypt": "yes", "TrustServerCertificate": "yes"})  # Adjust as needed.
            .build()
)

conn = pyodbc.connect(connection_string)
```

### Running scripts irregardless of dependencies.
If you just want to mass-run database scripts without caring about dependencies, you can do easily by placing the `.sql` scripts in a directory, and then doing something akin to the code below.

```py
from dbscripts.dbwriter import DBWriter
from dbscripts.dbscripts import DBScripts, MSSQL_Dialect

writer = DBWriter(conn)
scripts = DBScripts(sql_dialect=MSSQL_Dialect())
scripts.populate_from_dir('./your_scripts_directory')
writer.execute_scripts(scripts.scripts, False)
```

### Running scripts with attention to dependencies.
To do this, you can use a reordering method available to `DBScripts` instances that will recursively shift through scripts, trying to identify any object names that appear in the script collection. 

> Remember, only dependencies *within* the collection can be identified and solved; if a database object appears in a script, but its own script is not in the collection, you may run into an exception if said object does not yet exist.

```py
from dbscripts.dbwriter import DBWriter
from dbscripts.dbscripts import DBScripts, MSSQL_Dialect

writer = DBWriter(conn)
scripts = DBScripts(sql_dialect=MSSQL_Dialect())
scripts.populate_from_dir('./your_scripts_directory')
scripts.calculate_dependencies()
writer.execute_scripts(scripts.order_by_safe_execution(), False)
```