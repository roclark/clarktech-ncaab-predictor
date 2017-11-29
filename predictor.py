import pandas as pd
import numpy as np
from glob import glob
from sklearn.ensemble import RandomForestClassifier
from sklearn.feature_selection import SelectFromModel
from sklearn.cross_validation import cross_val_score


class Predictor:
    def __init__(self):
        self._classifier = None
        self._model = None
        self._targets = None
        self._test = None
        self._train = None

        data = self._read_data()
        self._create_features(data)
        self._create_classifier()
        self._train_model()

    @property
    def accuracy(self):
        xval = cross_val_score(self._classifier,
                               self._train,
                               self._targets,
                               cv = 5,
                               scoring='accuracy')
        print 'Accuracy: %s%%' % round(np.mean(xval) * 100.0, 2)

    def _read_data(self):
        data = pd.DataFrame()

        for match in glob('matches/*'):
            data = data.append(pd.read_csv(match))
        return data

    def _create_features(self, data):
        train_length = int(len(data) * 0.75)
        self._targets = data.home_win.head(train_length)
        train = data.drop('home_win', 1)
        train.drop('pts', 1, inplace=True)
        train.drop('opp_pts', 1, inplace=True)
        self._test = train.iloc[train_length:]
        self._train = train.head(train_length)

    def _create_classifier(self):
        clf = RandomForestClassifier(n_estimators=50, max_features='sqrt')
        self._classifier = clf.fit(self._train, self._targets)

    def _train_model(self):
        model = SelectFromModel(self._classifier, prefit=True)
        train_reduced = model.transform(self._train)

        parameters = {'bootstrap': False,
                      'min_samples_leaf': 3,
                      'n_estimators': 50,
                      'min_samples_split': 10,
                      'max_features': 'sqrt',
                      'max_depth': 6}
        self._model = RandomForestClassifier(**parameters)
        self._model.fit(train_reduced, self._targets)
