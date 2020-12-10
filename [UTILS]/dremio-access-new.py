import re
import json
import pyodbc
import requests
import pandas as pd
import time
import jaydebeapi

class DremioQueryBuilderHTTP:
    
    def __init__(self):
        self.__get_credentials__()
        self.username = self.credentials['uid']
        self.password = self.credentials['pwd']
        self.headers = {'content-type':'application/json'}
        self.dremioServer = 'http://{}:{}'.format(self.credentials["host"], self.credentials["api_port"])
        self.login_endpoint = '{server}/apiv2/login'.format(server=self.dremioServer)
        self.base_url = '{server}/api/v3/'.format(server=self.dremioServer)
        self.__login__()
    
    def __get_credentials__(self):
        with open('/home/ubuntu/notebooks/files/.credentials.json') as f: 
            self.credentials = json.load(f)
        
    def __login__(self):
        loginData = {'userName': self.username, 'password': self.password}
        response = requests.post(self.login_endpoint, headers=self.headers, data=json.dumps(loginData))
        authResponse = json.loads(response.text)
        if not "token" in authResponse: 
            return {
                "ERROR" : "NO AUTHENTICAN TOKEN RETURNED FOR THE CREDENTIALS {}.".format(self.last_jobQuery), 
                "POSTRESPONSE" : "{}".format(loginData, authResponse)
            }
        self.authorization_token = authResponse["token"]
        self.headers['authorization'] = '_dremio{authToken}'.format(authToken=self.authorization_token)
        
    def get(self, query):
        return json.loads(requests.get(self.base_url + query, headers=self.headers).text)
    
    def post(self, endpoint, body = None):
        text = requests.post(self.base_url + endpoint, headers=self.headers, data=json.dumps(body)).text
        return json.loads(text) if text else None
    
    def ṕut(self, endpoint, body = None):
        text = requests.put(self.base_url + endpoint, headers=self.headers, data=json.dumps(body)).text
        return json.loads(text) if text else None
    
    def delete(self, endpoint):
        return json.loads(requests.delete(self.base_url + endpoint, headers=self.headers))
                          
class DremioQueryMakerHTTP:
    
    def __init__(self, verbose = True):
        self.builder = DremioQueryBuilderHTTP()
        self.index_sql = "SELECT * FROM INFORMATION_SCHEMA.VIEWS"
        self.limit = 500 # Dremio max limit
        self.verbose = verbose
        self.pendingStates = ["STARTING", "RUNNING", "PLANNING", "ENQUEUED"]
        self.index = self.querySQL(self.index_sql)
    
    def __start_jobMetadata__(self, query):
        self.last_jobQuery = query
        self.last_jobId = None
        self.last_jobStatus = None
        
    def __get_jobId__(self):
        postResponse = self.builder.post('sql', body={'sql': self.last_jobQuery})
        if not "id" in postResponse: 
            return {
                "ERROR" : "NO JOBID RETURNED FOR THE QUERY {}.".format(self.last_jobQuery), 
                "POSTRESPONSE" : "{}".format(self.last_jobQuery, postResponse)
            }
        self.last_jobId = postResponse["id"]

    def __get_jobStatus__(self):
        jobStatus = self.builder.get("job/{jobId}".format(jobId=self.last_jobId)).get("jobState", None)
        self.last_jobStatus = jobStatus    

    def __print_query_status(self):
        print("QUERY STATUS: {}".format(self.last_jobStatus))

    def __get_jobResultPage__(self, offset):    
        pageResponse = self.builder.get("job/{jobid}/results?offset={offset}&limit={limit}"
                                        .format(jobid=self.last_jobId, offset=offset, limit=self.limit))
        return pageResponse["rows"] if "rows" in pageResponse else []
    
    def querySQLPaginator(self):
        offset = 0
        data = []
        row_count = True
        while row_count:
            pageResponse = self.__get_jobResultPage__(offset)
            row_count = len(pageResponse)
            offset += row_count
            data += pageResponse
        return data

    def querySQL(self, query):
        self.__start_jobMetadata__(query)
        self.__get_jobId__()
        self.__get_jobStatus__()
        if self.verbose: self.__print_query_status()
        while self.last_jobStatus in self.pendingStates:
            time.sleep(1)
            self.__get_jobStatus__()
            if self.verbose: self.__print_query_status()
        data = self.querySQLPaginator()          
        return pd.DataFrame(data)

    def getTable(self, line):
        table_name = self.index.loc[line]["TABLE_NAME"]
        source = self.index.loc[line]["TABLE_SCHEMA"]
        return self.querySQL("""SELECT * FROM \"{}\".\"{}\"""".format(source, table_name))

    def getIndex(self):
        return self.index
    
class DremioQueryMakerJDBC:    
   
    def __init__(self):
        self.__get_credentials__()
        self.username = self.credentials['uid']
        self.password = self.credentials['pwd']
        self.host = self.credentials['host']
        self.port = self.credentials['port']  
        self.connection_string = self.__get_connection_string__()
        self.conn = self.__get_connector__()
        self.index_query = """SELECT * FROM INFORMATION_SCHEMA.VIEWS;"""
        self.index = self.querySQL(self.index_query)
        self.raw_index_query = """SELECT * FROM INFORMATION_SCHEMA."TABLES";"""
        self.raw_index = self.querySQL(self.raw_index_query)
        
    def __get_credentials__(self):
        with open('/home/ubuntu/notebooks/files/.credentials.json') as f: 
            self.credentials = json.load(f)
            
    def __get_connection_string__(self):
        return "jdbc:dremio:direct={host}:{port}".format(host = self.host, port = self.port)
    
    def __get_connector__(self):
        return jaydebeapi.connect(
            "com.dremio.jdbc.Driver",
            self.connection_string,
            {'user': self.username, 'password': self.password},
            "/home/ubuntu/notebooks/files/dremio-jdbc-driver-4.1.3-202001022113020736-53142377.jar",
        )
    
    def querySQL(self, query):
        # Retrieve query keyword
        keyword = re.match(r'\W*(\w[^,. !?"]*)', query).groups()[0]
        if keyword.upper() == 'SELECT':
            curs = self.conn.cursor()
            curs.execute(query)
            col_names = [name[0] for name in curs.description]
            data = curs.fetchall()
            return pd.DataFrame(data, columns = col_names)
        else:
            raise ValueError('{}: Permission denied.'.format(keyword))

    
    def getIndex(self):
        return self.index
    
    def getRawIndex(self):
        return self.raw_index
    
    def getTable(self, line):
        table_name = self.index.loc[line]["TABLE_NAME"]
        source = self.index.loc[line]["TABLE_SCHEMA"]
        return self.querySQL("""SELECT * FROM \"{}\".\"{}\";""".format(source, table_name))
    
    def getRawTable(self, line):
        table_name = self.raw_index.loc[line]["TABLE_NAME"]
        source = self.raw_index.loc[line]["TABLE_SCHEMA"]
        return self.querySQL("""SELECT * FROM \"{}\".\"{}\";""".format('\".\"'.join(source.split(".")), table_name))
    
class DremioQueryMakerODBC:
    
    def __init__(self):
        self.__get_credentials__()
        self.username = self.credentials['uid']
        self.password = self.credentials['pwd']
        self.driver = self.credentials["driver"]
        self.host = self.credentials['host']
        self.port = self.credentials['port'] 
        self.connection_string = self.__get_connection_string__()
        self.conn = self.__get_connector__()
        self.index_query = """SELECT * FROM INFORMATION_SCHEMA.VIEWS;"""
        self.index = self.querySQL(self.index_query)
        
    def __get_credentials__(self):
        with open('/home/ubuntu/notebooks/files/.credentials.json') as f: 
            self.credentials = json.load(f)
            
    def __get_connection_string__(self):
        return (
            "Driver={};".format(self.driver)
            + "ConnectionType=Direct;"
            + "HOST={};".format(self.host)
            + "PORT={};".format(self.port)
            + "AuthenticationType=Plain;"
            + "UID={};".format(self.username)
            + "PWD={}".format(self.password)
    )
    
    def __get_connector__(self):
        return pyodbc.connect(self.connection_string,autocommit=True)
    
    def getIndex(self):
        return self.index
    
    def querySQL(self, query): 
        return pd.read_sql(query,self.conn)
    
    def getTable(self, line):
        table_name = self.index.loc[line]["TABLE_NAME"]
        source = self.index.loc[line]["TABLE_SCHEMA"]
        return self.querySQL("""SELECT * FROM {}.{}""".format(source, table_name))