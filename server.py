from flask import Flask, request, make_response
from flask_restful import Resource, Api
from pymongo import MongoClient
from bson.objectid import ObjectId
from utils.mongo_json_encoder import JSONEncoder
from functools import wraps
import bcrypt  # make sure the install this library for the module to work


# Basic Setup
app = Flask(__name__)  # created flask instance and assign it to the app var
mongo = MongoClient('localhost', 27017)  # establish a connection to our MongoDB service that's running locally
app.db = mongo.develop_database  # specify a particular database (develop_database) to store data.
api = Api(app)  # create an instance of the flask_restful API
app.bcrypt_rounds = 12  # work factor for the hash


def check_auth(username, password):
    user_collection = app.db.users  # references the database for users
    user = user_collection.find_one({'username': username})  # find a user

    if user is None:  # if there is no user
        return False
    else:  # if there is a user
        # check if the hash we generate based on auth matches stored hash
        encodedPassword = password.encode('utf-8')  # encode user with pw
        # if the bcrypt pw matches with the un encrypted pw 
        if bcrypt.hashpw(encodedPassword,
                         user['password']) == user['password']:
            return True
        else:  # if the bcrypt pw does not match
            return False


def requires_auth(f):  # checks authenication of incoming request
    @wraps(f)
    def decorated(*args, **kwargs):
        auth = request.authorization  # reads the authenication header
        # checks if the user credentials provided are valid
        if not auth or not check_auth(auth.username, auth.password):
            return ({'error': 'Basic Auth Required.'}, 401, None)
        return f(*args, **kwargs)
    return decorated


class User(Resource):

    def post(self):
        if (request.json['username'] is None  # if there is no username
                or request.json['password'] is None):
                return ({'error':  'Request requires username and password'},
                        400,
                        None)

        user_collection = app.db.users  # references the database for users
        user = user_collection.find_one({'username': request.json['username']})

        if user is not None:  # if there is a user
            return ({'error': 'Username already in use'}, 400, None)
        else:  # if there is no user, create with password
            encodedPassword = request.json['password'].encode('utf-8')
            # encrypt the password
            hashed = bcrypt.hashpw(
                encodedPassword, bcrypt.gensalt(app.bcrypt_rounds))
            request.json['password'] = hashed
            user_collection.insert_one(request.json)

    @requires_auth  # decorater - if authorized, run get
    def get(self):
        return (None, 200, None)


# Implement REST Resource
class Trip(Resource):

    @requires_auth   # checks authenication of incoming request
    def get(self, trip_id=None):   # to read info from data
        if trip_id is None:  # if there is no trip
            trip_collection = app.db.trips  # reference the database from which the client is requesting
            trips = list(trip_collection.find(  # create a list to store the users
                {'user': request.authorization.username}))
            return trips  # return the trips
        else:
            trip_collection = app.db.trips  # reference the database from which the client is requesting
            trip = trip_collection.find_one(  # create a query (search) based on the object_id
                {'_id': ObjectId(trip_id),
                 'user': request.authorization.username})

            if trip is None:  # if we can't find the trip
                # Flask allows us to return tuple in form
                # (response, status, headers)
                return (None, 404, None)  # return error
            else:  # if we can find the documents
                return trip  # return the trip

    @requires_auth
    def post(self):
        new_trip = request.json  # access the json client
        new_trip['user'] = request.authorization.username
        trip_collection = app.db.trips  # create collection to store the new object
        result = trip_collection.insert_one(request.json)  # insert the json document into collection for the results

        trip = trip_collection.find_one(result.inserted_id)  # use the trip to fetch the inserted results

        return (trip, 201, None)  # return the trip with selected documents

    @requires_auth
    def put(self, trip_id):
        new_trip = request.json
        new_trip['user'] = request.authorization.username
        trip_collection = app.db.trips

        # remove _id since we can't update it and would need to
        # transform it into an ObjectId
        del request.json['_id']
        trip_collection.update_one({'_id': ObjectId(trip_id),
                                    'user': request.authorization.username},
                                   {'$set': request.json})
        trip = trip_collection.find_one(ObjectId(trip_id))

        return trip

    @requires_auth
    def delete(self, trip_id):
        trip_collection = app.db.trips   # create collection to store the new object
        trip_collection.delete_one(  # delete the json document from the collection
            {'_id': ObjectId(trip_id),
             'user': request.authorization.username}
        )

        return {"tripIdentifier": trip_id}

# Add REST resource to API
# The endpoints for User and Trips
api.add_resource(Trip, '/trip/', '/trip/<string:trip_id>')
api.add_resource(User, '/user/')


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
