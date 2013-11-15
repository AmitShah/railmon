import pymysql
import sys


class DatabaseService(object):
    def __init__(self):
        self.connection = pymysql.connect(host='127.0.0.1', port=3306, user='root', passwd='', db='cnrail')
        self.connection.autocommit(True)
        pass
        
    def create_tables(self):
        cursor = None
        try:
            cursor =self.connection.cursor()
            cursor.execute("""CREATE TABLE IF NOT EXISTS history 
                (autoIndex BIGINT NOT NULL AUTO_INCREMENT,
                accountId char(32) NOT NULL,
                deviceId char(32) NOT NULL,
                timestamp BIGINT NOT NULL, 
                statuscode BIGINT NOT NULL,
                rfidTagNum BIGINT,
                gforce DOUBLE,
                latitude DOUBLE,
                longitude DOUBLE, 
                speed DOUBLE,
                PRIMARY KEY(autoIndex))""")
        except:
            pass
        finally:
            cursor.close()
    '''insert an event containing accountId,deviceId,timestamp,statusCode,gforce,latitude,longitude,rfidTagNum'''
    def add_event(self,accountId="",deviceId="",timestamp=0,statusCode=0,gforce=0.0,latitude=0.0,longitude=0.0,rfidTagNum=0, speed=0.0):
        cmd = "INSERT into history (accountId,deviceId,timestamp,statusCode,gforce,latitude,longitude,rfidTagNum,speed) values(%s,%s,%s,%s,%s,%s,%s,%s,%s)"
        cursor = None
        try:
            self.connection.ping(reconnect=True)
            cursor = self.connection.cursor(pymysql.cursors.DictCursor)
            cursor.execute(cmd,(accountId,deviceId,timestamp,statusCode,gforce,latitude,longitude,rfidTagNum,speed))
        except:
            pass
        finally:
            cursor.close()
        
    def get_events(self,start=0,end=0):
        cmd = "SELECT * FROM history where timestamp >= %s and timestamp <=%s and not latitude=0 and not longitude=0"
        cursor = None
        result = None
        try:
            self.connection.ping(reconnect=True)
            cursor = self.connection.cursor(pymysql.cursors.DictCursor)
            cursor.execute(cmd,(start,end))
            result = cursor.fetchall()
        except:
            pass
        finally:
            cursor.close()
        return result
        
if __name__ == '__main__':
    database = DatabaseService()
    database.create_tables()
    database.add_event(accountId='test', 
                           deviceId='testdevice', 
                           timestamp=1010101, 
                           statusCode=62725, 
                           rfidTagNum=22,
                           gforce=2.57,
                           latitude=10.010,
                           longitude=180.923)
    result = database.get_events(22, 0, 1010102)
    print result