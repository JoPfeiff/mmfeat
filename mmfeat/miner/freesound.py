'''
FreeSound API miner
'''

import os
import requests
import shutil
import time
import urllib

from .base import BaseMiner

class FreeSoundResult(object):
    def __init__(self, result, api_key):
        self.ID = result['id']
        self.format_url = 'http://www.freesound.org/apiv2/sounds/{}/?token={}'
        self.url = self.format_url.format(self.ID, api_key)
        self.format = 'audio/ogg' # FreeSound default

class FreeSoundMiner(BaseMiner):
    def __init__(self, save_dir, config_path='./miner.yaml'):
        super(FreeSoundMiner, self).__init__(save_dir, config_path)
        self.__engine__ = 'freesound'

        self.api_keys   = self.config['freesound']['api-keys']
        self.format_url = 'http://www.freesound.org/apiv2/search/text/?fields=id&{}'
        self.page_size  = 150 # maximum

    def getUrl(self, query, limit, offset):
        filters = {
            'tag': query,
            'duration': '[0 TO 120]'
        }
        self.filter = ' '.join([key + ':' + filters[key] for key in filters])
        full_query = urllib.urlencode({
            'token': self.api_keys[self.cur_api_key],
            'page_size': limit,
            'page': offset,
            'filter': self.filter
        })
        return self.format_url.format(full_query)

    def _search(self, query, limit=20, offset=1):
        url = self.getUrl(query, limit, offset)
        print (url)
        r = requests.get(url)
        try:
            results = r.json()
        except ValueError:
            print('ERR: Request returned with code %s (%s)' % (r.status_code, r.text))
            time.sleep(self.sleep_time)
        print (results)
        return [FreeSoundResult(res, self.api_keys[self.cur_api_key]) \
                for res in results['results']], results['next'] is not None

    def search(self, query, limit=20):
        page = 1
        results, isMoreLeft = self._search(query, limit, page)
        page = 2
        while isMoreLeft and len(results) < limit:
            print( page, isMoreLeft)
            max = limit - len(results)
            more_results, isMoreLeft = self._search(query, max, page)
            results += more_results
            page += 1
        return results

    def saveFile(self, result):
        '''
        result:     result object (FreesoundResult)
        '''
        if result.format in ['audio/ogg']:
            format = 'ogg'
        else: # unknown format, skipping
            return None

        fname = '%s.%s' % (result.ID, format)
        path = '%s/%s' % (self.save_dir, fname)
        if os.path.exists(path):
            print('%s - already exists' % fname)
            return

        # download the file (specifically, the high-quality ogg preview)
        try:
            r = requests.get(result.url, timeout=20)
            response = r.json()
            r = requests.get(response['previews']['preview-hq-ogg'], \
                stream=True, timeout=20)
            r.raw.decode_content = True
            with open(path, 'wb') as fw:
                shutil.copyfileobj(r.raw, fw)
        except:
            print(fname, 'error saving')
            return None

        print(fname)

        return fname
