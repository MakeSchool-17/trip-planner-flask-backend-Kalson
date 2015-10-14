from flask import Flask, request, make_response, jsonify
from flask_restful import Resource, Api
from pymongo import MongoClient
from bson.objectid import ObjectId
from utils.mongo_json_encoder import JSONEncoder

# Basic Setup
app = Flask(__name__)  # created flask instance and assign it to the app var
mongo = MongoClient('localhost', 27017)  # establish a connection to our MongoDB service that's running locally
app.db = mongo.develop_database  # specify a particular database (develop_database) to store data.
api = Api(app)  # create an instance of the flask_restful API

# Implement REST Resource
class MyObject(Resource):

    def post(self):
      new_myobject = request.json  # access the json client
      myobject_collection = app.db.myobjects  # create collection to store the new object
      result = myobject_collection.insert_one(request.json)  # insert the json document into collection for the results
      myobject = myobject_collection.find_one({"_id": ObjectId(result.inserted_id)})  # use the result to fetch the inserted documents

      return myobject  # return the selected documents

    def get(self, myobject_id):  # to read info from data
      myobject_collection = app.db.myobjects  # reference the database from which the client is requesting
      myobject = myobject_collection.find_one({"_id": ObjectId(myobject_id)})  # create a query (search) based on the object_id
      if myobject is None:  # if we can't the documents
        response = jsonify(data=[])
        response.status_code = 404  # return error
        return response
      else:  # if we can find the documents
        return myobject  # return it to the client

# Add REST resource to API
api.add_resource(MyObject, '/myobject/','/myobject/<string:myobject_id>')

# provide a custom JSON serializer for flaks_restful
@api.representation('application/json')
def output_json(data, code, headers=None):
    resp = make_response(JSONEncoder().encode(data), code)
    resp.headers.extend(headers or {})
    return resp

if __name__ == '__main__':
    # Turn this on in debug mode to get detailled information about request related exceptions: http://flask.pocoo.org/docs/0.10/config/
    app.config['TRAP_BAD_REQUEST_ERRORS'] = True
    app.run(debug=True)
