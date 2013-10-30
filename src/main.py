'''
Created on Aug 8, 2013

@author: amitshah
'''
from mailgun import *
from bluerover import Api
from database import DatabaseService
import ssl,socket,sys
import os,tornado
from tornado.httpserver import HTTPServer
from tornado.websocket import WebSocketHandler
import sys,functools,json
from threading import Lock
import datetime,logging, threading

logger = logging.getLogger('sensor_main')
logger.setLevel(logging.INFO)

fh = logging.FileHandler('sensor.log')
fh.setLevel(logging.INFO)
logger.addHandler(fh)


'''helper method to handle casting of improper chars'''
def ignore_exception(IgnoreException=Exception,DefaultVal=None):
    """ Decorator for ignoring exception from a function
    e.g.   @ignore_exception(DivideByZero)
    e.g.2. ignore_exception(DivideByZero)(Divide)(2/0)
    """
    def dec(function):
        def _dec(*args, **kwargs):
            try:
                return function(*args, **kwargs)
            except IgnoreException:
                return DefaultVal
        return _dec
    return dec

sint = ignore_exception(IgnoreException=ValueError)(int)


from threading import RLock

class EventRecorder(object):
    
    def __init__(self,database):
        self.database = database
        pass
    
    def notify(self, message):
        try:
            event = json.loads(message)        
            if not isinstance(event,(int,long)) and 'rfidTagNum' in event:
                self.database.add_event(accountId=event['accountID'],
                                   deviceId=event['deviceID'],
                                   timestamp=event['timestamp'],
                                   statusCode=event['statusCode'],
                                   gforce=event['rfidTemperature'],
                                   rfidTagNum=event['rfidTagNum'],
                                   latitude=event['latitude'],
                                   longitude=event['longitude'],
                                   speed=event['speedKPH']
                                   )
        except:            
            pass
    
        
'''Look for new line characters and notify all observer per line '''
class LineObserver(EventRecorder):
    def __init__(self,database):
        EventRecorder.__init__(self,database)
        self.buffer = ''
        self.rlock = RLock()
    '''we need to protect buffer from async calls :('''        
    def notify(self,message):
        try:              
            #prevent multiple async calls from overriding the buffer while in processing  
            with self.rlock:                
                self.buffer= self.buffer+message                
                while "\n" in self.buffer:
                    (line, self.buffer) = self.buffer.split("\n", 1)
                    data = line.strip() #remove blank lines (when keep alive is sent from server)
                    if data:
                        logger.info(('sending buffered data:%s' % self.buffer))
                        EventRecorder.notify(self, data)                            
        except:
            logger.error('notify exception')
            pass
        finally:
            pass
        

    
    
class BaseHandler(tornado.web.RequestHandler):        
    def initialize(self,api,database):
        self.api = api
        self.database = database
        pass
    
    def get_current_user(self):
        '''used for web api administration access'''
        #self.account_service.getUserWithPassword()
        user = self.get_secure_cookie('user')
        if user is not None:            
            user = json.loads(self.get_secure_cookie("user"))
        return user

class MainHandler(tornado.web.RequestHandler):
    def get(self):
        self.render('home.html')
  
class RfidsHandler(BaseHandler):    
    def post(self):
        json_rfid= self.api.call_api("/rfid", {})
        self.write(json_rfid)          

class DevicesHandler(BaseHandler):
    def post(self):
        devices = self.api.call_api("/device",{})
        self.write(devices)
from tornado.escape import json_encode
class EventHandler(BaseHandler):
    def post(self):
        rfidTagNum = self.get_argument("rfidTagNum", 0)
        start = self.get_argument("start", 0)
        end = self.get_argument("end", 0)
        events = self.database.get_events(rfidTagNum,start,end)
        self.write(json_encode(events))
    
if __name__ == '__main__':
    
    '''let setup tcp connection to the upstream service to get sensor data 
    and handle this data with a async socket read for distribution :) '''
    #demoaccount
    api = Api(token='AyHBnaaukc32qIxv21KW7o1ogQHU3xOrsAFU3fzO',
              key='g22EPptMppsLfHUoqifXwWDDIVv7qV/L8dccEWcmcq0JKpQ5QVuBPToUNor4ZfqT',
              base_url='https://developers.polairus.com')
    
    database= DatabaseService()
    observer= LineObserver(database)
    
    sock = socket.socket()    
    s = ssl.wrap_socket(sock)
    
    def connect_to_service():        
        s.connect(('developers.polairus.com',443))    
        s.sendall(api.create_eventstream_request())
        pass
    
    
    def data_handler(sock,fd,events):
        try:                    
            data = sock.recv(4096)
            logger.info(('received data:%s' % data))
            observer.notify(data)        
        except:
            logger.error('data handler')
            sock.close()
            ioloop = tornado.ioloop.IOLoop.instance()
            ioloop.remove_handler(fd)
            ioloop.add_timeout(datetime.timedelta(seconds=60), connect_to_service) 
        pass


    callback = functools.partial(data_handler, s)
    ioloop = tornado.ioloop.IOLoop.instance()
    ioloop.add_handler(s.fileno(), callback, ioloop.READ)    
    #ioloop.add_callback(connect_to_service)
        
    #define all the services
    services = dict(
        api = api,
        database = database
        )
    
    settings = dict(
        template_path=os.path.join(os.path.dirname(__file__), "template"),
        static_path=os.path.join(os.path.dirname(__file__), "static"),
        cookie_secret= 'secret_key',
        login_url='/login'
        )
      
    application = tornado.web.Application([
    (r"/rfids", RfidsHandler, services),
    (r"/devices", DevicesHandler, services),
    (r"/event", EventHandler, services),
    (r"/*", MainHandler),
          
    ], **settings)
    
    sockets = tornado.netutil.bind_sockets(9999)
    server = HTTPServer(application)
    server.add_sockets(sockets)
    
    #pc.start()
    ioloop.start()
    
