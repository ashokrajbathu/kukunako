import os
import jwt, json
from eve import Eve
from flask import Flask, make_response, g, request, jsonify, Response,session
from eve.auth import TokenAuth
from datetime import datetime, timedelta
from functools import wraps
from settings import TOKEN_SECRET
from bson.objectid import ObjectId
from werkzeug.security import generate_password_hash, check_password_hash
from bson import json_util
from framework.match_me_algorithm import *
import requests
#import grequests
import flask
import time
import urllib2, random
from views import get_search
from weberdb import WeberDB
from flask.ext.socketio import SocketIO, emit, join_room, leave_room
from flask import Flask
from flask_mail import Mail, Message
from bson import json_util
import string
import random




class TokenAuth(TokenAuth):
	def check_auth(self, token, allowed_roles, resource, method):
		accounts = app.data.driver.db['people']
		return accounts.find_one({'token': token})

app = Eve(__name__,static_url_path='/static')
app.debug = True,
app.config.update(
	DEBUG=True,
    #EMAIL SETTINGS
	MAIL_SERVER='smtp.gmail.com',
	MAIL_PORT=465,
	MAIL_USE_SSL=True,
	MAIL_USERNAME = 'Team@theweber.in',
	MAIL_PASSWORD = 'ashok@weber'
	)
mail=Mail(app)
socketio = SocketIO(app)


def create_token(user):
    payload = {
        'sub': str(user['_id']),
        'iat': datetime.now(),
        'exp': datetime.now() + timedelta(days=14)
    }

    token = jwt.encode(payload, TOKEN_SECRET)
    return token.decode('unicode_escape')

def parse_token(req):
    token = req.headers.get('Authorization').split()[1]
    return jwt.decode(token, TOKEN_SECRET)

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not request.headers.get('Authorization'):
            response = jsonify(error='Missing authorization header')
            response.status_code = 401
            return response

        payload = parse_token(request)

        if datetime.fromtimestamp(payload['exp']) < datetime.now():
            response = jsonify(error='Token has expired')
            response.status_code = 401
            return response

        g.user_id = payload['sub']

        return f(*args, **kwargs)

    return decorated_function

# Routes

@app.route('/')
def index():
	return make_response(open('static/app/index.html').read())


@app.route('/api/me')
@login_required
def me():
    return Response(json.dumps(g.user_id),  mimetype='application/json')


@app.route('/api/getpeoplenames',  methods=['GET','POST'])
def getnames():

    page =  request.json['page']
    query = request.json['query']
    accounts = app.data.driver.db['people']
    print page
    data = accounts.find({"$or":[
                {"name.first":{"$regex":".*"+query+".*"}},
                {"name.name":{"$regex":".*"+query+".*"}},
                {"username":{"$regex":".*"+query+".*"}}
            ]}).limit(10);

    return json_util.dumps(data)


@app.route('/foo/<path:filename>')
def send_foo(filename):
    return send_from_directory('/static/', filename)

@app.route('/auth/login', methods=['POST'])
def login():
    accounts = app.data.driver.db['people']
    user = accounts.find_one({'email': request.json['email']})
    if not user:
        response = jsonify(error='you email does not exist')
        response.status_code = 401
        return response
    if not user['email_confirmed'] == True:
        response = jsonify(error='email is not confirmed')
        response.status_code = 401
        return response
    if not user or not check_password_hash(user['password']['password'], request.json['password']):
        response = jsonify(error='Wrong Email or Password')
        response.status_code = 401
        return response
    token = create_token(user)
    return jsonify(token=token)


@app.route('/forgotpasswordlink', methods=['POST', 'GET'])
def forgotpassword():
    accounts = app.data.driver.db['people']
    user = accounts.find_one({'email': request.json['email']})
    user_name = user['username']
    user_randome_string = user['random_string']
    if not user:
        response = jsonify(error = 'Your Email does not exist in our database')
        response.status_code = 401
        return response
    else:
        msg = Message('Password Link',
                      sender='Team@theweber.in',
                      recipients=[request.json['email']]

            )
        msg.html = "<p>Thanks for registering with us, " \
                       "To complete your Weber registration, Follow this link:<br>\
                        <br><p style='color:red;border:1px solid #dcdcdc;padding:10px;" \
                       "width:800px;text-align:center;font-size:14px;'>" \
                       "<a href='http://www.weber.ooo/#/users/"+user_name+"/change_password_link/"+user_randome_string+"'>Click Here</a></p>\
                        <br><br><br><br>\
                        Thanks,<br>The Weber Team\
                        </p>"
        mail.send(msg)
        return "recovery email link has been sent to your email"



@app.route('/changepassword', methods=['POST', 'GET'])
def changepassword():
    accounts = app.data.driver.db['people']
    user = accounts.find_one({'username': request.json['user_name']})
    if user:
        password = generate_password_hash(request.json['password'])
        return password

@login_required
@app.route('/check_user_current_password', methods=['POST', 'GET'])
def check_user_current_password():
    accounts = app.data.driver.db['people']
    user = accounts.find_one({'username': request.json['user_name']})
    if check_password_hash(user['password']['password'], request.json['old_password']):
        response = jsonify(data = 'Your password is correct')
        response.status_code = 200
        return response
    else:
        response = jsonify(error = 'Your old password is incorrect')
        response.status_code = 401
        return response


@login_required
@app.route('/get_new_hash_password', methods=['POST', 'GET'])
def get_new_hash_password():
    accounts = app.data.driver.db['people']
    user = accounts.find_one({'username': request.json['user_name']})
    if user:
        return generate_password_hash(request.json['new_password'])
    else:
        response = jsonify(error = 'No user Found')
        response.status_code = 401
        return response


@app.route('/getsearch')
def getSearchResults():
    extract_words = []
    extract_words = create_tokens(request.args.get("searchtext"))
    print len(extract_words)
    if len(extract_words) == 2:
        data = 'http://127.0.0.1:8000/api/posts?where={"keywords":{"$in":'+json.dumps(list(extract_words))+'}}'
        r = requests.get(data)
        return r.data
    else:
        return "none"

@app.route('/api/similarwords')
def getSimilarWords():
    print '----------------'
    print request.args.get('querystring')
    words = parse_sentence(request.args.get("querystring"))
    post_tokens = create_tokens(request.args.get("querystring"))
    keywords = set(list(post_tokens)+list(words))
    return json.dumps(list(set(keywords)))

##################################################
#Signup with email confirm validation


import time
@app.route('/auth/signup', methods=['POST'])
def signup():
    accounts = app.data.driver.db['people']
    user_email = accounts.find_one({'email': request.json['email']})
    if not user_email:
        dt = datetime.now()
        user = {
            'email' :request.json['email'],
            'username':request.json['username'],
            'name':{
               'first':request.json['firstname'],
               'last':request.json['lastname']
            },
            'password':{
                'password':generate_password_hash(request.json['password']),
                'password_test':request.json['password'],
                'password_updated':str(datetime.now())
            },
            'email_confirmed':False,
            'picture' : {
                'large' : "static/app/images/w-logo.jpg",
                'medium' : "static/app/images/w-logo.jpg",
                'thumbnail' : "static/app/images/w-logo.jpg"
            },
            'phone': "",
            'interests': [],
            'study': {
              'intermediate':"",
              'graduate': ""
            },
            'random_string': id_generator(),
            'accept_notifications':[],
            'born' : "",
            'gender' : request.json['gender'],
            'lastmessageseen' : dt.strftime('%Y-%m-%dT%H:%M:%SZ'),
            'location' : {
                'city' : "",
                'state' : "",
                'street' : ""
            },
            'friends' : [],
            'matchnotifications':[],
            'notifications':[],
            'interests': request.json['interests'],
            'interestsimilarwords': request.json['interestsimilarwords'],
            'conversations':[]

        }

        data = accounts.insert(user)
        user_id = str(user['_id'])
        user_random_string = str(user['random_string'])

        msg = Message('Confirm your Weber account',
                      sender='Team@theweber.in',
                      recipients=[request.json['email']]

            )
        msg.html = '<div style="min-height:100px;border:1px solid #dcdcdc;">' \
                   '<h5>Thanks for registering with us, To complete your Weber registration, Follow this link:</h5>' \
                   '<div style="padding:20px 5px">' \
                   '<a href="http://www.weber.ooo/#/confirm_account/users/'\
                   +user_id+'/confirm/'+user_random_string+'">Click Here</a>' \
                                                           '</div>' \
                                                           '</div>'
        mail.send(msg)
        return user_id
    else:
        response = jsonify(error='This email is registered with us. Please try forgot password.')
        response.status_code = 401
        return response


@app.route('/api/chat/sendmessage', methods=['POST'])
def sendmessage():
    print '------------datetime-----------'
    print datetime.now()
    ts = int(time.time())
    if not request.json['sender'] or not request.json['receiver']\
            or not request.json['message']:
        return False

    accounts = app.data.driver.db['messages']

    message = {
        'sender':ObjectId(request.json['sender']),
        'receiver': ObjectId(request.json['receiver']),
        'seen' : False,
        'message' : request.json['message'],
        'timestamp': ts,
        'message_created': datetime.now()
    }

    #accounts.update({'timestamp':1425368551},{'$set':{'seen':True}})
    data = accounts.insert(message)
    if data:
        return json.dumps({'status': 'ok','data':data}, default=json_util.default)
    return json.dumps({'status':'failed','data':0})

@app.route('/api/updatetimestamp', methods=['POST'])
def updateTimeStamp():
    accounts = app.data.driver.db['people']
    ts = int(time.time())
    data = accounts.update({'_id':ObjectId(request.json['userid'])},{'$set':{'lastmessageseen':ts}})
    if data:
        return jsonify({'status':'ok'})
    return jsonify({'status':'failed'})

@app.route('/api/updateMessageSeen', methods=['POST'])
def makeMessagesSeen():
    print request.json['messageids']
    list = []
    accounts = app.data.driver.db['messages']

    for x in request.json['messageids']:
        accounts.update({ '_id':ObjectId(x) },{'$set':{'seen':True}})
        print(x+'is updated')

    return 'hai'

def id_generator(size=60, chars=string.ascii_uppercase + string.digits):
    return ''.join(random.choice(chars) for _ in range(size))

from random import randint

"""def random_with_N_digits(n):
    range_start = 10**(n-1)
    range_end = (10**n)-1
    return randint(range_start, range_end)"""


#end of confirm validation
#################################################

import redis
r = redis.Redis()
pipe = r.pipeline()

friendsNotific = 0
searchNotific = 0

"""def check_updates(userid):

    skey = 'search_'+userid
    if((r.get(skey)) == 'search_notific'):
        yield 'data: %s \n\n' % json.dumps({'userid':userid,'searchNotific': 1,'friendsnotifc':0 })
        r.delete(skey)

    fkey = 'friend_'+userid
    if((r.get(fkey)) == 'friend_notific'):
        yield 'data: %s \n\n' % json.dumps({'userid':userid,'searchNotific': 0,'friendsnotifc':1 })
        r.delete(fkey):"""


@app.route('/stream/<userid>')
#@nocache
def stream(userid):
    return Response(check_updates(userid),mimetype='text/event-stream')

def after_post_inserted(items):
    post_author = ""
    post_id = ""
    for atribute,value in items[0].iteritems():
        print atribute, value

        if(atribute == "author"):
            post_author = str(value)
        if(atribute == "_id"):
            post_id = str(value)

    socketio.emit('postNotifications',{'data':{'postnotific': True},
                                           'author':post_author,
                                           'postid':post_id})


def after_friend_notification_get(updates, original):
    for attrbute,value in original.iteritems():
        if(attrbute == '_id'):
            socketio.emit('FMnotific',{'data':{'FMnotific': True}}, room = str(value))
            #key = 'friend_'+str(value)
            #pipe.set(key,'friend_notific')
    #pipe.execute()

# match button notifications
def postNotific(updates, original):
    present = updates['interestedPeople']['presentupdated']
    last =  updates['interestedPeople']['lastupdated']
    if(present != last):
        socketio.emit('FMnotific',{'data':{'FMnotific': True}}, room = str(original['author']))



app.on_inserted_people_posts+= after_post_inserted
app.on_updated_people+= after_friend_notification_get
app.on_updated_posts = postNotific






from werkzeug import secure_filename

UPLOAD_FOLDER = 'static/images'
ALLOWED_EXTENSIONS = set(['png','jpg', 'jpeg', 'bmp'])


app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1] in ALLOWED_EXTENSIONS



@app.route('/fileUpload', methods=['GET', 'POST'])
def fileupload():
    if request.method == 'POST':
        file = request.files['file']

        if file and allowed_file(file.filename):
            filename = secure_filename(file.filename)

            import datetime
            dt = str(datetime.datetime.now())


            import os
            renamed_filename = dt+'_'+filename

            file.save(os.path.join(app.config['UPLOAD_FOLDER'], renamed_filename))
            #print os.path.join(app.config['UPLOAD_FOLDER'], renamed_filename)
        return os.path.join(app.config['UPLOAD_FOLDER'], renamed_filename)

#chating part



@socketio.on('connecting', namespace='/live')
def joiningtoroom(data):
    if(join_into_room(data['id'])):
        emit('joiningstatus',{'data': data['id'] in request.namespace.rooms})



@socketio.on('connect')
def creta_or_join(data):

    #print '========================'
    #print data['data']
    if(join_into_room(data['data'])):
        #print request.namespace.rooms
        emit('join_status',{'data': data['data'] in request.namespace.rooms})


@socketio.on('send_message')
def send_to_room(data):

    #print '===========message============='
    #print data['receiverid']
    #print data['senderid']
    #print data['message']

    emit('receive_messages',
         {
          'message': data['message'],
          'senderid':data['senderid'],
          'receiverid':data['receiverid']
         },
         room=data['receiverid'])

    """if(join_into_room(data['data'])):
        print request.namespace.rooms
        emit('join_status',{'data': data['data'] in request.namespace.rooms})"""



@socketio.on_error()
def error_handler(e):
    print '============error=========='
    print e

def join_into_room(id):

    data = False
    if id is not None:
        join_room(id)
        data = True
    return data



app.threaded=True
socketio.run(app, host='127.0.0.1', port=8000)

# server sent events section
"""from redis import Redis
redis = Redis()
pubsub = redis.pubsub()


import time
from datetime import datetime
p = redis.pipeline()
app.config['ONLINE_LAST_MINUTES'] = 5


def mark_online(user_id):
    global p
    now = int(time.time())
    expires = now + (app.config['ONLINE_LAST_MINUTES'] * 60) + 10
    all_users_key = 'online-users/%d' % (now // 60)
    user_key = 'user-activity/%s' % user_id
    p.sadd(all_users_key, user_id)
    p.set(user_key, now)
    p.expireat(all_users_key, expires)
    p.expireat(user_key, expires)
    p.execute()

def mark_friend_requests(userid):
    global p
    now = int(time.time())
    user_key = 'friend-notific/%s' % userid
    p.set(user_key,now)




def get_user_last_activity(user_id):
    last_active = redis.get('user-activity/%s' % user_id)
    if last_active is None:
        return None
    return datetime.utcfromtimestamp(int(last_active))

def get_online_users():
    current = int(time.time()) // 60
    minutes = xrange(app.config['ONLINE_LAST_MINUTES'])
    return redis.sunion(['online-users/%d' % (current - x)
                         for x in minutes])


def mark_current_user_online(userid):
    mark_online(userid)"""
