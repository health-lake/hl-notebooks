Covid PRJ01 Workstation
======

## This project contains notebook examples on how to connect to dremio through:
1. ODBC
2. JDBC
3. HTTP

The classes that implement the connections are all in the **[UTILS]/dremio-access-new.py**.

## It also has examples on how to access the ipeadata.gov.br

See the **[UTILS][EXTRACAO]** files.

------
## Bellow I give a brief description of what was coded to access each dremio connector:

### 1. ODBC
This is only available in Python, since the ODBC connector is failing to fetch tables with special characters and is not being used. The connector needs the odbc driver which is pre-installed and the python lib *pyodbc*.

### 2. JDBC
This connector fufils all the needs of fetching tables with different characters and also has a good performance. It is implemented for Python and R for R users if needed. In python it uses the [jaydebeapi](https://pypi.org/project/JayDeBeApi/) and in R it uses the [RJDBC](http://www.rforge.net/RJDBC/).

Her we have to take an extra step to recover metadata from queries such as columns names:
```py
curs = self.conn.cursor()
curs.execute(query)
col_names = [name[0] for name in curs.description]
```
Since the querie does not return column names or types on JDBC connector.

### 3. HTTP
This is the most versatile access, but the least performant ones. The Dremio API is limited to 500 registries at each response, which makes retriving big datasets a troublesome task with this connections. However, this is a [well documented API ](https://docs.dremio.com/rest-api/) and can be used to fetch metadata. we implemented the connector for Python and use R reticulate to translate python datasets to R on the example notebook.

#### by dourival@datasprints.com 
on 29-04-2020 