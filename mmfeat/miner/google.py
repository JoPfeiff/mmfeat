'''
Google Custom Search API miner
'''

import requests
import time
# import urllib.request as urllib2
import urllib2

from mmfeat.miner.base import BaseMiner, DailyLimitException

class GoogleResult(object):
    def __init__(self, result):
        self.ID     = None # Google has no unique IDs
        if 'title' not in result:
            self.title = 'Anonymous'
        else:
            self.title  = result['title']
        self.url    = result['image']['thumbnailLink']
        self.format = 'image/jpg' # default thumbnail format
        # self.format = result['mime']

class GoogleMiner(BaseMiner):
    def __init__(self, save_dir, config_path='./miner.yaml'):
        super(GoogleMiner, self).__init__(save_dir, config_path)
        self.__engine__ = 'google'

        self.search_id   = self.config['google']['search-id']
        self.api_keys   = self.config['google']['api-keys']
        self.lang       = self.config['google']['lang']
        self.format_url = 'https://www.googleapis.com/customsearch/v1?cx={}&key={}&q={}' \
                            + '&searchType=image&imgType=photo&start={}&lr={}'

    def getUrl(self, query, offset):
        query = urllib2.quote("'{}'".format(query))
        search_id = urllib2.quote(self.search_id)
        return self.format_url.format(search_id, self.api_keys[self.cur_api_key], query, \
            offset, self.lang)

    def _search(self, query, offset=1):
        url = self.getUrl(query, offset)
        r = requests.get(url)
        try:
            results = r.json()
            if r.status_code in [403, 429, 503]:
                raise ValueError('Status code indicates error')
        except ValueError:
            print('ERR: Request returned with code %s' % (r.status_code))
            if r.status_code == 429 or r.status_code == 503:
                print('ERR (Google): Too many requests, sleeping..')
                time.sleep(self.sleep_time)
                self.sleep_time *= self.sleep_time
                if self.sleep_time > self.max_sleep_time:
                    self.sleep_time = 5
            elif r.status_code == 403:
#                if 'error' in results and 'message' in results['error'] \
#                    and (results['error']['message'].startswith('Daily Limit Exceeded.') or results['error']['message'].startswith('Project blocked;')):
                print('ERR (Google): Daily limit exceeded, trying other key..')
                if self.cur_api_key >= len(self.api_keys)-1:
                    raise DailyLimitException('Daily limit reached (and no more API keys available).')
                else:
                    self.cur_api_key += 1
                    return self._search(query, offset)
            else:
                time.sleep(self.sleep_time)

        if 'items' not in results or 'searchInformation' not in results:
            return [], 0

        total = int(results['searchInformation']['totalResults'])

        return [GoogleResult(res) for res in results['items']], total

    def search(self, query, limit=20):
        results, total = self._search(query, 1) # Google is 1-indexed
        while total > len(results) and len(results) < limit:
            more_results, _ = self._search(query, len(results))
            results += more_results
        return results
