#!/usr/bin/env python
# coding: utf-8
# Copyright (c) 2013-2014 Abram Hindle, Daniel Cones
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#
from flask import Flask, request
from flask_sockets import Sockets
from gevent import queue, spawn, kill
import json

app = Flask(__name__)
sockets = Sockets(app)
app.debug = True

class World:
    def __init__(self):
        self.listeners = list()
        self.clear()

    def add_set_listener(self, listener):
        self.listeners.append( listener )

    def set(self, entity, data):
        self.space[entity] = data
        self.update_listeners({entity:data})

    def update_listeners(self, data):
        string = json.dumps(data)
        for listener in self.listeners:
            listener(string)

    def clear(self):
        self.space = dict()
        self.update_listeners(self.socket_world())

    def get(self, entity):
        return self.space.get(entity,dict())

    def world(self):
        return self.space

    def socket_world(self):
        return {'world':self.world()}

myWorld = World()

def read_ws(ws):
    try:
        while True:
            message = ws.receive()
            if message:
                entity, data = list(*json.loads(message).items())
                myWorld.set(entity, data)
    except:
        pass

@sockets.route('/subscribe')
def subscribe_socket(ws):
    ws.send(json.dumps(myWorld.socket_world()))
    client = queue.Queue()
    myWorld.add_set_listener(client.put_nowait)
    g = spawn(read_ws, ws)
    try:
        while True:
            ws.send(client.get())
    except Exception as e:
        print('WS Error : ',e)
    finally:
        kill(g)

# I give this to you, this is how you get the raw body/data portion of a post in flask
# this should come with flask but whatever, it's not my project.
def flask_post_json():
    '''Ah the joys of frameworks! They do so much work for you
       that they get in the way of sane operation!'''
    if (request.json != None):
        return request.json
    elif (request.data != None and request.data.decode("utf8") != u''):
        return json.loads(request.data.decode("utf8"))
    else:
        return json.loads(request.form.keys()[0])

@app.route('/')
def hello():
    return ("",301,[("Location", "/static/index.html")])

@app.route("/entity/<entity>", methods=['POST','PUT'])
def update(entity):
    myWorld.set(entity,flask_post_json())
    return get_entity(entity)

@app.route("/world", methods=['POST','GET'])
def world():
    return (myWorld.world(), 200, [("Content-Type","application/json")])

@app.route("/entity/<entity>")
def get_entity(entity):
    return (myWorld.get(entity), 200, [("Content-Type","application/json")])

@app.route("/clear", methods=['POST','GET'])
def clear():
    myWorld.clear()
    return world()

if __name__ == "__main__":
    app.run()
