import sys
import logging
from flask_cors import CORS
from Dremio import DremioQueryMaker, DremioQueryBuilderHTTP
from flask import Flask, request, abort, jsonify, make_response

app = Flask(__name__)
cors = CORS(app, resources={r"/*": {"origins": "*"}})
logger = logging.getLogger()
dremio_conn = DremioQueryMaker()
dremio_api = DremioQueryBuilderHTTP()

@app.route("/getMetadata", methods=['GET'])
def getMetadata():
    table_name = request.args.get('table_name')
    query_stages = "catalog"
    stages = {stage["path"][0]:stage["id"] for stage in dremio_api.get(query_stages)["data"]}
    query_tables = "catalog/{}".format(stages["Covid-Lake"])
    tables = {table["path"][1]:table["id"] for table in dremio_api.get(query_tables)["children"]}
    query_wiki = "catalog/{}".format(tables[table_name])
    return jsonify(dremio_api.get(query_wiki))

@app.route("/showTables", methods=['GET'])
def showTables():
    df = dremio_conn.showTables()
    return jsonify(df.to_dict())

@app.route("/getTable", methods=['GET'])
def getTable():
    table_name = request.args.get('table_name')
    df = dremio_conn.getFirstRows(table_name)
    return jsonify(df.to_dict())

@app.route("/exploreEntity", methods=['GET'])
def exploreEntity():
    df = dremio_conn.showTables()
    response = make_response(df.to_csv())
    response.headers["Content-Disposition"] = "attachment; filename=Entities.csv"
    response.headers["Content-Type"] = "text/csv"
    return response

@app.route("/downloadEntity", methods=['GET'])
def downloadEntity():
    table_name = request.args.get('table_name')
    response = make_response(dremio_conn.getTable(table_name).to_csv())
    response.headers["Content-Disposition"] = "attachment; filename={}.csv".format(table_name)
    response.headers["Content-Type"] = "text/csv"
    return response
    
@app.errorhandler(400)
def internal_server_error(e):
    return jsonify(error=str(e)), 400

@app.route("/querySQL", methods=['GET'])
def querySQL():
    try:
        query = request.args.get('query')
        df = dremio_conn.querySQL(query)
        return jsonify(df.to_dict())
    except ValueError as err:
        abort(400, description=str(err))
    except:
        abort(400, description="Please check your Query!!")
    
if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0')
