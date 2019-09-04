'''
Base miner class
'''

# import  pickle
import cPickle as pickle
import json
import os
import requests
import shutil
import sys
import time
import yaml

class DailyLimitException(Exception):
    def __init__(self, value):
        self.value = value
    def __str__(self):
        return repr(self.value)

class BaseMiner(object):
    def __init__(self, save_dir, config_path):
        '''
        save_dir:       the directory where we save files to
        config_path:    path to configuration file
        '''
        self.config = yaml.load(open(config_path))
        self.save_dir = save_dir
        self.cur_api_key = 0
        self.file_id = 1
        self.save_after_every_query = True
        self.sleep_time = 5
        self.max_sleep_time = 60*60 # 1 hour
        self.save_results_every_n = 20
        self.idx = {}
        self.results = {}

        if self.save_dir[-1] == '/':
            self.save_dir = self.save_dir[:-1] # strip trailing / if any

        if not os.path.exists(self.save_dir):
            os.makedirs(self.save_dir)
        elif os.path.exists(self.save_dir + '/index.pkl'):
            self.results    = pickle.load(open(self.save_dir + '/results.pkl', 'rb'))
            self.idx        = pickle.load(open(self.save_dir + '/index.pkl', 'rb'))
            self.file_id    = max([int(fname.split('.')[0]) \
                                for sublist in self.idx.itervalues() \
                                for fname in sublist if fname is not None]) + 1

    def getResults(self, queries, limit):
        '''
        queries:    list of queries
        limit:      number of files per query
        '''
        for ii, query in enumerate(queries):
            if query in self.idx:
                n_stored_results = len(self.idx[query])
                print(query, n_stored_results, 'present')
                if n_stored_results >= limit:
                    print('%s already exists and has enough images, skipping..' % query)
                    continue

            if query in self.results:
                n_stored_results = len(self.results[query])
                if n_stored_results >= limit:
                    print('%s already queried, skipping..' % query)
                    continue

            print('Querying for %s' % query)

            try:
                query_results = self.search(query, limit)
                if query in self.idx and n_stored_results >= len(query_results):
                    print('%s already has all available images, skipping..' % query)
                    continue

                self.results[query] = query_results
            except DailyLimitException:
                # exit gracefully so that we can download the images
                return

            if ii % self.save_results_every_n == 0:
                pickle.dump(self.results, open('%s/results.pkl' % (self.save_dir), 'wb'))

    def loadResults(self, fname):
        '''
        fname:      if something went wrong, we can load search results
                    and retrieve later (results.pkl usually)
        '''
        self.results = pickle.load(open(fname, 'rb'))

    def saveFile(self, result):
        '''
        result:     result object (BingResult, GoogleResult, FlickrResult or ImageNetResult)
        '''
        if result.format in ['image/jpg', 'image/jpeg']:
            format = 'jpg'
        elif result.format in ['image/png']:
            format = 'png'
        elif result.format in ['image/gif']:
            format = 'gif'
        else: # unknown format, default to jpg
            format = 'jpg'

        fname = '%s.%s' % (self.file_id, format)
        path = '%s/%s' % (self.save_dir, fname)

        # download the file
        try:
            r = requests.get(result.url, stream=True, timeout=20)
            if r.status_code != 200:
                return None
            r.raw.decode_content = True
            with open(path, 'wb') as fw:
                shutil.copyfileobj(r.raw, fw)
        except: # something wrong, skipping..
            print(fname, 'error saving')
            return None

        print(fname)

        self.file_id += 1

        return fname

    def save(self):
        for query in self.results:
            if query not in self.idx:
                self.idx[query] = []

            print('Saving %s files' % query)

            for ii, result in enumerate(self.results[query]):
                fname = self.file_id
                try:
                    fname = self.saveFile(result)
                except:
                    print('Fetching file for %s failed (url=%s, error=%s)' \
                        % (query, result.url, sys.exc_info()[1]))
                    continue
                if fname is None: continue

                self.idx[query].append(fname)

                if self.save_after_every_query:
                    pickle.dump(self.idx, open('%s/index.pkl' % self.save_dir, 'wb'))

        pickle.dump(self.idx, open('%s/index.pkl' % self.save_dir, 'wb'))
