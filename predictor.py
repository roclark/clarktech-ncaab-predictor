import numpy
import tensorflow.contrib.learn as skflow
from sklearn import datasets, metrics
from glob import glob
from common import create_stats_array, read_match_stats_file, read_team_stats_file


AWAY = 0
HOME = 1
WINNER = {'away': AWAY,
          'home': HOME}


class Predictor:
    def __init__(self):
        self._classifier = None
        self._statistics = None
        self._results = None

        self._read_data()
        self._create_classifier()

    def _read_data(self):
        self._statistics = []
        self._results = []

        for match in glob('matches/*'):
            winner, away_stats, home_stats = read_match_stats_file(match)
            self._statistics.append(create_stats_array(eval(away_stats),
                                                             eval(home_stats)))
            self._results.append([float(WINNER[winner])])
        self._statistics = numpy.array(self._statistics)
        self._target = numpy.array(self._results)

    def _create_classifier(self):
        self._classifier = skflow.TensorFlowLinearClassifier(n_classes=2)
        self._classifier.fit(self._statistics, self._results)

    def accuracy(self):
        return metrics.accuracy_score(self._results,
                                      self._classifier.predict(self._statistics))

    def predict(self, stats):
        return self._classifier.predict(stats)

    def probability(self, stats):
        return self._classifier.predict_proba(stats)
