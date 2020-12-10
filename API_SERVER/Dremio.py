import re
import json
import pyodbc
import jaydebeapi
import requests
import pandas as pd

keywords = [
    'ADD',
    'ALTER',
    'CREATE',
    'DELETE',
    'DROP',
    'INSERT',
    'UPDATE'
]

class DremioQueryMaker:
        
    def showTables(self):
        query = """SELECT TABLE_SCHEMA, TABLE_NAME FROM INFORMATION_SCHEMA.VIEWS WHERE TABLE_SCHEMA = 'Covid-Lake';"""
        return self.querySQL(query)
    
    def getTable(self, table_name):
        return self.querySQL("""SELECT * FROM \"Covid-Lake\".\"{}\" LIMIT 10000""".format(table_name))
    
    def getFirstRows(self, table_name):
        return self.querySQL("""SELECT * FROM \"Covid-Lake\".\"{}\" LIMIT 5""".format(table_name))
    
    def check_query(self, query):
        QUERY = query.upper()
        search_pattern = '|'.join(keywords)
        first_check = re.search(search_pattern, QUERY)
        if first_check:
            keyword_pos = first_check.start()
            sub_query = query[keyword_pos:]
            check_pattern = '|'.join([r'\b{}\b'.format(item) for item in keywords])
            check_res = re.match(check_pattern, sub_query)
            if check_res:
                return (False, check_res[0]) # Invalid query
        return (True, )

    def querySQL(self, query):
        check_res = self.check_query(query)
        if check_res[0]:
            with open('/home/ubuntu/notebooks/files/.credentials.json') as f: 
                credentials = json.load(f)
            username = credentials['uid']
            password = credentials['pwd']
            host = credentials['host']
            port = credentials['port']  
            connection_string = "jdbc:dremio:direct={host}:{port}".format(host=host, port=port)
            conn = jaydebeapi.connect(
                "com.dremio.jdbc.Driver",
                connection_string,
                {'user': username, 'password': password},
                "/home/ubuntu/notebooks/files/dremio-jdbc-driver-4.1.3-202001022113020736-53142377.jar"
            )
            curs = conn.cursor()
            curs.execute(query)
            col_names = [name[0] for name in curs.description]
            data = curs.fetchall()
            return pd.DataFrame(data, columns=col_names)
        else:
            raise ValueError('{}: Permission denied.'.format(check_res[1]))

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