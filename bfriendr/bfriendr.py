# Copyright 2011 Google Inc. All Rights Reserved.
# 
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
# 
#     http://www.apache.org/licenses/LICENSE-2.0
# 
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

#!/usr/bin/env python

import datetime
import logging
import os

from lib.py import belay

from google.appengine.ext import db
from google.appengine.ext import webapp
from google.appengine.ext.webapp.util import run_wsgi_app
  
def delete_entity(entity):
  belay.CapServer.revoke_entity(entity)
  entity.delete()


class CardData(db.Model):
  name = db.StringProperty(default='')
  email = db.StringProperty(default='')
  image = db.BlobProperty(default=None)
  imageType = db.StringProperty(default='')
  notes = db.StringProperty()
  # TODO(mzero): needs a refresh_cap property at some point
  
  def toJSON(self, cap_server):
    cardJSON = {
      'name':       self.name,
      'email':      self.email,
      'notes':      self.notes,
    }
    if self.imageType:
      cardJSON['image'] = cap_server.regrant(ImageHandler, self).serialize()
    return cardJSON

  
  def deleteAll(self):
    delete_entity(self)
  
class FriendData(db.Model):
  card = db.ReferenceProperty(CardData, required=True)
  read_their_stream = db.StringProperty()

  def deleteAll(self):
    self.card.deleteAll()
    q = MessageData.all()
    q.ancestor(self)
    for message in q:
      message.deleteAll()
    delete_entity(self)

class MessageData(db.Model):
  when = db.DateTimeProperty(auto_now_add=True)
  message = db.TextProperty()
  capability = db.StringProperty()
  resource_class = db.StringProperty()
  
  def nicedate(self):
    date = self.when
    today = datetime.datetime.now()
    date_ordinal = date.toordinal()
    today_ordinal = today.toordinal()
    format = ""
    if date_ordinal == today_ordinal:
      format = "today"
    elif date_ordinal == today_ordinal - 1:
      format = "yesterday"
    elif date_ordinal > today_ordinal - 7:
      format = '%a'
    elif date.year == today.year:
      format = '%a, %b %d'
    else:
      format = '%a, %b %d %Y'
    format += ' - %I:%M %p'
    return date.strftime(format)

  def deleteAll(self):
    delete_entity(self)

  def toJSON(self, cap_server):
    if self.capability is None or self.resource_class is None:
      return {'message': self.message,
              'when': str(self.when) }
    else:
      return {'message': self.message,
              'when': str(self.when),
              'capability': cap_server.restore(self.capability),
              'resource_class': str(self.resource_class)}

class AccountData(db.Model):
  my_card = db.ReferenceProperty(CardData, required=True)

  def deleteAll(self):
    self.my_card.deleteAll()
    q = FriendData.all()
    q.ancestor(self)
    for friend in q:
      friend.deleteAll()
    delete_entity(self)

def new_account():
  card = CardData()
  card.put()
  account = AccountData(my_card=card)
  account.put()
  return account

class GenerateHandler(belay.CapHandler): pass
class LaunchHandler(belay.CapHandler): pass
class AccountInfoHandler(belay.CapHandler): pass
class FriendsListHandler(belay.CapHandler): pass
class FriendInfoHandler(belay.CapHandler): pass
class StreamReadHandler(belay.CapHandler): pass
class StreamPostHandler(belay.CapHandler): pass
class MessageInfoHandler(belay.CapHandler): pass
class IntroduceYourselfHandler(belay.CapHandler): pass

class GenerateHandler(belay.BcapHandler):
  def get(self):
    self.bcapResponse(self.cap_server.grant(LaunchHandler, new_account()))

  def post(self):
    account = new_account()
    card = account.my_card
    # TODO(mzero): never trust what they send you!
    card.name = self.request.POST['name']
    card.email = self.request.POST['email']
    card.notes = self.request.POST['notes']
    
    if 'imageFile' in self.request.POST:
        image = self.request.POST['imageFile']
        card.image = image.value
        card.imageType = image.type

    card.put()
    response = {
      'launch': self.cap_server.grant(LaunchHandler, account),
      'icon': self.server_url('/person.png'),
      'name': 'bfriendr for ' + card.name
    }
    self.bcapResponse(response)

class GenerateAccountHandler(belay.BcapHandler):
  def get(self):
    self.bcapResponse(self.cap_server.grant(AccountInfoHandler, new_account()))


class LaunchHandler(belay.CapHandler):
  def get(self):
    account = self.get_entity()
    response = {
      'page': {
        'html': self.server_url('/bfriendr-belay.html'),
        'window': {'height': 800, 'width': 350}
      },
      'x-gadget': {
        'html': self.server_url('/bfriendr.html'),
        'scripts': [ self.server_url('/bfriendr.js') ]
      },
      'info': {
        'friends':  self.cap_server.regrant(FriendsListHandler, account),
        'myCard':  self.cap_server.regrant(CardInfoHandler, account.my_card),
        'introduceYourself': self.cap_server.regrant(IntroduceYourselfHandler, account),
        'introduceMeTo': self.cap_server.regrant(IntroduceMeToHandler, account),
        'chitURL': self.server_url('/chit.png'),
        # TODO(mzero): or should this be just the following?
        'account':  self.cap_server.regrant(AccountInfoHandler, account),
      }
    }

    self.bcapResponse(response)


class AccountInfoHandler(belay.CapHandler):
  def get(self):
    account = self.get_entity()
    introduceYS = self.cap_server.regrant(IntroduceYourselfHandler, account)
    introduceMT = self.cap_server.regrant(IntroduceMeToHandler, account)
    self.bcapResponse({
      'friends':  self.cap_server.regrant(FriendsListHandler, account),
      'introduceYourself': introduceYS,
      'introduceMeTo': introduceMT,
      'myCard':  self.cap_server.regrant(CardInfoHandler, account.my_card),
    })

  def delete(self):
    account = self.get_entity()
    account.deleteAll()
    self.bcapNullResponse()
    
    
class CardInfoHandler(belay.CapHandler):
  def get(self):
    card = self.get_entity()
    cardJSON = card.toJSON(self.cap_server)
    cardJSON['uploadImage'] = self.cap_server.regrant(ImageUploadHandler, card).serialize()
    self.bcapResponse(cardJSON)
  
  def put(self):
    card = self.get_entity()
    request = self.bcapRequest()
    # TODO(mzero): never trust what they send you!
    card.name = request['name']
    card.email = request['email']
    card.notes = request['notes']
    card.put()
    self.bcapNullResponse()
  
  def delete(self):
    card = self.get_entity()
    card.deleteAll()
    self.bcapNullResponse()

class ImageHandler(belay.CapHandler):
  def get(self):
    card = self.get_entity()
    self.xhr_response()
    if card.imageType:
      self.response.content_type = card.imageType
      self.response.body = card.image
    else:
      self.response.status = 404

class ImageUploadHandler(belay.CapHandler):
  def post(self):
    card = self.get_entity()
    image = self.request.POST['imageFile']
    card.image = image.value
    card.imageType = image.type
    card.put()
    # TODO(mzero): Revoking the cap is a hack, and will break some clients for
    # no good reason. Really ImageHandler should do ETags on the image data.
    self.cap_server.revoke(ImageHandler, card)
    self.xhr_response()



class FriendsListHandler(belay.CapHandler):
  def get(self):
    account = self.get_entity()

    q = FriendData.all(keys_only=True)
    q.ancestor(account)
    friends = []
    for friendKey in q:
      friends.append(self.cap_server.regrant(FriendInfoHandler, friendKey))
        # NOTE(mzero): regrant should re-use any existing granted cap
        # NOTE(mzero): 2nd arg should accept a key as well as an entity
    self.bcapResponse(friends)


class FriendInfoHandler(belay.CapHandler):
  def get(self):
    friend = self.get_entity()

    read_my_stream = self.cap_server.regrant(StreamReadHandler, friend)
    write_my_stream = self.cap_server.regrant(StreamPostHandler, friend)
    read_conversation = self.cap_server.regrant(ConversationReadHandler, friend)

    self.bcapResponse({
      'card': friend.card.toJSON(self.cap_server),
      'readTheirStream': self.cap_server.restore(friend.read_their_stream),
      'readMyStream': read_my_stream,
      'postToMyStream': write_my_stream,
      'readConversation': read_conversation
    })
  
  def put(self):
    # TODO(mzero)
    pass
  
  def delete(self):
    friend = self.get_entity()
    friend.deleteAll()
    self.bcapNullResponse()
      # NOTE(mzero)

class StreamPostHandler(belay.CapHandler):
  def post(self):
    friend_info = self.get_entity()
    request = self.bcapRequest()
    msg = request['message'] 
    if 'capability' in request and 'resource_class' in request:
      message_data = \
        MessageData(message = msg, parent = friend_info,
                    capability = request['capability'].serialize(),
                    resource_class = request['resource_class'])
    else:
      message_data = MessageData(message = msg, parent = friend_info)
    message_data.put()
    # TODO(jpolitz): handle capabilities in messages
    self.bcapResponse({'success': True})

class ConversationReadHandler(belay.CapHandler):
  def get(self):
    friend_info = self.get_entity()

    readMine = self.cap_server.regrant(StreamReadHandler, friend_info)
    readTheirs = self.cap_server.restore(friend_info.read_their_stream)

    mine = readMine.invoke('GET')['items']
    theirs = readTheirs.invoke('GET')['items']

    combined = mine
    combined.extend(theirs)
    sorted_combined = sorted(combined, key = lambda(m): m['when'], reverse = True)

    self.bcapResponse({'items': sorted_combined})
  
  def post(self):
    friend_info = self.get_entity()
    request = self.bcapRequest()

    when = request['when']

    readMine = self.cap_server.regrant(StreamReadHandler, friend_info)
    readTheirs = self.cap_server.restore(friend_info.read_their_stream)

    mine = readMine.invoke('GET')['items']
    theirs = readTheirs.invoke('GET')['items']

    combined = mine
    combined.extend(theirs)
    combined = filter(lambda(msg): msg['when'] > when, combined)
    combined = sorted(combined, key = lambda(m): m['when'])
    self.bcapResponse({'items': combined})


class StreamReadHandler(belay.CapHandler):
  def get(self):
    friend_info = self.get_entity()
    q = MessageData.all().ancestor(friend_info)
    # TODO(jpolitz): more than 10 messages
    json_messages = []
    for m in q:
      json_messages.append(m.toJSON(self.cap_server))

    self.bcapResponse({'items': json_messages})


class MessageInfoHandler(belay.CapHandler):
  def get(self):
    message = self.get_entity();
    self.bcapResponse({
      'when':       message.nicedate(),
      'message':    message.message,
      'capability': message.capability,
      'resourceClass':      message.resource_class
    })

  def delete(self):
    message = self.get_entity()
    message.deleteAll()
    self.bcapNullResponse()

class IntroduceYourselfHandler(belay.CapHandler):
  def get(self):
    account = self.get_entity()
    self.bcapResponse(account.my_card.toJSON(self.cap_server))

  def post(self):
    account = self.get_entity()
    request = self.bcapRequest()
    card_data = request['card']

    stream = None
    if 'streamForYou' in request:
      stream = request['streamForYou']

    their_card = CardData(name=card_data['name'],
                          email=card_data['email'],
                          notes=card_data['notes'],
                          parent=account)
    # TODO(jpolitz): should images be modeled as caps or no?
    if 'image' in card_data:
      response = self.cap_server.restore(card_data['image']).invoke('GET')
      their_card.image = db.Blob(response.content)
      their_card.imageType = response.headers['Content-Type']
    their_card.put()

    them = FriendData(card=their_card, parent=account)
    if stream: 
      them.read_their_stream = stream.serialize()
    them.put()

    stream_for_them = self.cap_server.regrant(StreamReadHandler, them)

    self.bcapResponse({'card': account.my_card.toJSON(self.cap_server),
                       'streamForYou': stream_for_them })

class IntroduceMeToHandler(belay.CapHandler):
  def post(self):
    account = self.get_entity()
    request = self.bcapRequest()
    card = account.my_card

    blank_card = CardData(name="Pending", email="Pending", notes="Pending")
    blank_card.put()
    new_friend = FriendData(parent=account, card=blank_card)
    new_friend.put()

    stream = self.cap_server.regrant(StreamReadHandler, new_friend)

    cap = request['introductionCap']

    # TODO(jpolitz): useful abstraction so card.toJSON is unnecessary
    intro_info = cap.invoke('POST',
                            {'card': card.toJSON(self.cap_server),
                             'streamForYou': stream})

    card_data = intro_info['card']
    friend_card = CardData(name=card_data['name'],
                           email=card_data['email'],
                           notes=card_data['notes'])
    # TODO(jpolitz): should images be modeled as caps or no?
    if 'image' in card_data:
      response = self.cap_server.restore(card_data['image']).invoke('GET')
      friend_card.image = db.Blob(response.content)
      friend_card.imageType = response.headers['Content-Type']
    friend_card.put()

    new_friend.card=friend_card
    blank_card.delete()

    if('streamForYou' in intro_info):
      new_friend.read_their_stream = intro_info['streamForYou'].serialize()

    new_friend.put()
    self.bcapResponse({
        'friend': self.cap_server.regrant(FriendInfoHandler, new_friend)
    })


# Externally Visible URL Paths
application = webapp.WSGIApplication(
  [(r'/cap/.*', belay.ProxyHandler),
   ('/belay/generate', GenerateHandler),
   ('/generate-account', GenerateAccountHandler),
  ],
  debug=True)

# Internal Cap Paths
belay.set_handlers(
  '/cap',
  [('station/launch',           LaunchHandler),
   ('friend/account',           AccountInfoHandler),
  
   ('friend/card',              CardInfoHandler),
   ('friend/image',             ImageHandler),
   ('friend/imageUpload',       ImageUploadHandler),
   
   ('friend/list',              FriendsListHandler),
   ('friend/friend',            FriendInfoHandler),
   
   ('friend/message',           MessageInfoHandler),
   ('friend/read',              StreamReadHandler),
   ('friend/post',              StreamPostHandler),
   ('friend/convo',             ConversationReadHandler),
   
   ('friend/introduceMeTo',     IntroduceMeToHandler),
   ('friend/introduceYourself', IntroduceYourselfHandler)
  ])

