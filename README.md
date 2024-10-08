*Written by Kyle Catterall of Baltic Apprenticeships L4.

This message will remain here as evidence of identity until appr. end.

---

# dbscripts

dbscripts is a small Python package for handling what my collegues and I like to refer to as "database scripts" - SQL scripts, often generated by a DBMS, that allow for the quick creation and altering of database objects.

### Supported Features

- **Minor Analysis** - this package can be used to analyse database scripts produced by MS-SSMS. For any given database script, you can get the name of the database object, the type of the database object, and the schema of the database object.

- **Dependency Management** - this package can be used to reorder a collection of database scripts into an order safe to execute without dependency issues. It does this through a combination of regular-expressions and Khan's topological sorting algorithm.

- **Script Execution** - of course, this package can be used to execute database scripts against a database.


### Limitations

- As implied, I have created this package as an aid to my job. As such, only Microsoft SQL Server is currently supported, since that's what I use. However, I have attempted to make the package as easily extendable as possible, so feel free to fork, alter, and make pull requests if you would like another flavor to be supported.

---

## Basic Usage

### Connecting to a SQL Server database.
To connect to a SQL server database, create a `pyodbc.Connection` using your connection string as usual. 

For those who are unfamiliar with SQL Server connection strings, I have created a connection string builder that will hopefully simplify its creation.

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

### Creating `DBScript` instances.
A `DBScript` instance can be created with a path to a database script and the flavor of your database. Given that, as mentioned, only MSSQL is currently supported, this process is very simple.

```py
from dbscripts.dbscripts import DBScript, DBFlavor_MSSQL

script = DBScript('./your_database_script.sql', DBFlavor_MSSQL())

# DBScript attributes. . .
print(script.contents)
print(script.metadata.obj_name, script.metadata.obj_type, script.metadata.obj_schema, sep=" - ")
```

### Using `DBScripts`.
The `DBScripts` class allows you to have a collection of `DBScript` instances, and perform operations that require or affect multiple scripts at once. The most noteable use-case is handling dependencies.

```py
from dbscripts.dbscripts import DBScripts, DBScript, DBFlavor_MSSQL, DBScriptsAppendRegular

script_a = DBScript('./dependent_on_b.sql', DBFlavor_MSSQL())
script_b = DBScript('./b.sql', DBFlavor_MSSQL())
scripts = DBScripts(DBFlavor_MSSQL(), DBScriptsAppendRegular())
scripts.append(script_a)
scripts.append(script_b)

# Example: handling dependencies. . .
for script in scripts.scripts:
    print(script.metadata.obj_name)

for script in scripts.safe_execution_order():
    print(script.metadata.obj_name)
```

As you can see, as well as taking a flavor, the `DBScripts` class also takes one of several `IDBScriptsAppender` implementations, which determine how the `append` method will behave. The following implementations exist:
- `DBScriptsAppendRegular` - does nothing fancy; it just appends the scripts.
- `DBScriptsAppendIgnoreDuplicates` - if you append a `DBScript` instance already present, it will be ignored.
- `DBScriptsAppendErrorOnDuplicates` - if you append a `DBScript` instance already present, a `DBScriptAlreadyPresentError` exception is raised.

These implementations are a lot more handy when using populating methods, such as `populate_from_dir`, which just attempts to append instances of `DBScript` for every SQL file in a given directory.

### Executing scripts with `DBWriter`.

A `DBWriter` class can be given a `pyodbc.Connection` instance and used to execute either a `DBScript` instance or a list of `DBScript` instances. Two common use cases are shown below as examples.

##### Running a directory of scripts irregardless of dependencies.

```py
from dbscripts.dbscripts import DBScripts, DBFlavor_MSSQL, DBScriptsAppendRegular
from dbscripts.dbwriter import DBWriter

conn = pyodbc.connect('your_connection_string')
writer = DBWriter(conn)
scripts = DBScripts(DBFlavor_MSSQL(), DBScriptsAppendRegular())
scripts.populate_from_dir('./your_database_scripts_directory')
writer.execute_scripts(scripts.scripts, raise_exceptions=True)
```

##### Running a directory of scripts with attention to dependencies.

```py
from dbscripts.dbscripts import DBScripts, DBFlavor_MSSQL, DBScriptsAppendRegular
from dbscripts.dbwriter import DBWriter

conn = pyodbc.connect('your_connection_string')
writer = DBWriter(conn)
scripts = DBScripts(DBFlavor_MSSQL(), DBScriptsAppendRegular())
scripts.populate_from_dir('./your_database_scripts_directory')
writer.execute_scripts(scripts.safe_execution_order(), raise_exceptions=True)
```
