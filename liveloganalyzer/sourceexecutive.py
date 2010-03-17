import time
from pprint import pprint
from threading import Thread
from pymongo import Connection
from pymongo.errors import CollectionInvalid, InvalidStringData
from debuglogging import error
from settings import MONGODB_NAME, MAX_COLLECTION_SIZE, SOURCES_SETTINGS
from util import smart_str

def main():
    for ss in SOURCES_SETTINGS:
        t = Thread(target=run_one, args=(ss,))
        t.start()
        time.sleep(1)

def run_one(settings):
    s = SourceExecutive(settings)
    s.start()

class SourceExecutive(object):
    def __init__(self, settings):
        self.collection = settings['collection']
        self.parser = settings['parser']
        self.source_class = settings['source'][0]
        self.kwargs = settings['source'][1]

    def start(self):
        self.start_source()
        self.connect_to_mongo()
        self.store_data()

    def start_source(self):
        self.source = self.source_class(**self.kwargs)
        self.stream = self.source.get_stream()

    def connect_to_mongo(self):
        conn = Connection()
        db = conn[MONGODB_NAME]
        try:
            self.mongo = db.create_collection(
                self.collection, {'capped': True, 'size': MAX_COLLECTION_SIZE * 1048576,})
        except CollectionInvalid:
            self.mongo = db[self.collection]

    def store_data(self):
        while True:
            line = self.stream.readline()
            line = smart_str(line)
            if not line:
                continue

            data = self.parser.parse_line(line)
            if data:
                data['server'] = self.source.host
                try:
                    self.mongo.insert(data)
                except InvalidStringData, e:
                    error('%s\n%s' % (str(e), line))
            else:
                error('Could not parse line:\n%s' % line)

if __name__ == '__main__':
    main()
