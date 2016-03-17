'''
Vector space model bases
'''

import os

import cPickle as pickle

import numpy as np

from scipy.stats import spearmanr

from .sim import cosine

class Space(object):
    def __init__(self, descrs):
        if isinstance(descrs, str):
            self.space = pickle.load(open(descrs, 'rb'))
        elif isinstance(descrs, dict):
            self.space = descrs
        else:
            raise TypeError('Expecting file name or dictionary of descriptors')
    def __getitem__(self, key):
        return self.space[key]
    def __contains__(self, key):
        return key in self.space
    def sim(self, x, y):
        return cosine(self.space[x], self.space[y])
    def spearman(self, dataset):
        if not isinstance(dataset, list) \
                or len(dataset) == 0 \
                or len(dataset[0]) != 3 \
                or not isinstance(dataset[0][2], float):
            raise TypeError('Dataset is not of correct type, list of [str, str, float] triples expected.')
        gs_scores, sys_scores = [], []
        for one, two, gs_score in dataset:
            sys_score = self.sim(one, two)
            gs_scores.append(gs_score)
            sys_scores.append(sys_score)
        return spearmanr(gs_scores, sys_scores)
    def neighbours(self, key, n=None):
        sims = []
        for other_key in self.space:
            if other_key == key: continue
            sims = (other_key, self.sim(key, other_key))

        if n is None:
            n = len(sims)

        return sorted(sims, key = lambda x: x[1], reverse=True)[:n]

class AggSpace(Space):
    def __init__(self, descrs, aggFunc='mean', caching=True):
        self.caching = caching
        self.cached_file_name = None

        if isinstance(descrs, str):
            self.descrs_file = descrs
            self.descrs = pickle.load(open(self.descrs_file, 'rb'))
            self.cached_file_name = '%s-%s.pkl' % (self.descrs_file, aggFunc)
        elif isinstance(descrs, dict):
            self.descrs = descrs

        if self.cached_file_name is not None and os.path.exists(self.cached_file_name) and self.caching:
            self.space = pickle.load(open(self.cached_file_name, 'rb'))
        if aggFunc in ['mean', 'max']:
            if aggFunc == 'mean':
                f = self.aggMean
            elif aggFunc == 'max':
                f = self.aggMax
            self.space = {k:f(self.descrs[k].values()) for k in self.descrs}
            if self.caching:
                pickle.dump(self.space, open(self.cached_file_name, 'wb'))

    def aggMean(self, m):
        return np.mean(m, axis=0)
    def aggMax(self, m):
        return np.max(m, axis=0)

    def getDispersions(self):
        if self.caching:
            cached_dispersions_file = '%s-dispersions.pkl' % (self.descrs_file)
            if os.path.exists(cached_dispersions_file):
                self.dispersions = pickle.load(open(cached_dispersions_file, 'rb'))
                return

        def disp(M):
            l = len(M)
            d, cnt = 0, 0
            for i in range(l):
                for j in range(i) + range(i+1, l):
                    d += (1 - cosine(M[i], M[j]))
                    cnt += 1
            return d / cnt if cnt != 0 else 0

        self.dispersions = {}
        min_disp, max_disp = 1, 0
        for k in self.descrs:
            imgdisp = disp(self.descrs[k].values())
            self.dispersions[k] = imgdisp
            if imgdisp > max_disp:
                max_disp, max_key = imgdisp, k
            if imgdisp < min_disp:
                min_disp, min_key = imgdisp, k

        # rescale
        for k in self.dispersions:
            self.dispersions[k] = max(0, min(1, (self.dispersions[k] - min_disp) / (max_disp - min_disp)))

        if self.caching:
            pickle.dump(self.dispersions, open(cached_dispersions_file, 'wb'))