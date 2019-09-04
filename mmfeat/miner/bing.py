'''
Bing Search API miner

Partially based on py-bing-search (https://github.com/tristantao/py-bing-search)
'''

import requests
import time
import urllib2
# import urllib.request as urllib2

from .base import BaseMiner

class BingResult(object):
    def __init__(self, result):
        self.ID     = result['ID']
        self.title  = result['Title']
        if 'Thumbnail' in result:
            self.url    = result['Thumbnail']['MediaUrl']
            self.format = result['Thumbnail']['ContentType']
        else:
            self.url    = result['MediaUrl']
            self.format = result['ContentType']

class BingMiner(BaseMiner):
    def __init__(self, save_dir, config_path='./miner.yaml'):
        super(BingMiner, self).__init__(save_dir, config_path)
        self.__engine__ = 'bing'

        self.api_keys   = self.config['bing']['api-keys']
        self.lang       = self.config['bing']['lang']
        self.format_url = 'https://api.datamarket.azure.com/Bing/Search/Image' \
                            + '?Query={}&$top={}&$skip={}&$format=json&Adult=%27Off%27&Market=%27{}%27'

    def getUrl(self, query, limit, offset):
        query = urllib2.quote("'{}'".format(query))
        return self.format_url.format(query, limit, offset, self.lang)

    def _search(self, query, limit=20, offset=0):
        url = self.getUrl(query, limit, offset)
        r = requests.get(url, auth=("", self.api_keys[self.cur_api_key]))
        try:
            results = r.json()
        except ValueError:
            print('ERR: Request returned with code %s (%s)' % (r.status_code, r.text))
            if r.status_code == 401:
                print ('ERR (Bing): It looks like your API key is invalid')
                quit()
            time.sleep(self.sleep_time)
        return [BingResult(res) for res in results['d']['results']], '__next' in results['d']

    def search(self, query, limit=20):
        results, isMoreLeft = self._search(query, limit, 0)
        while isMoreLeft and len(results) < limit:
            max = limit - len(results)
            more_results, isMoreLeft = self._search(query, max, len(results))
            results += more_results
        return results
