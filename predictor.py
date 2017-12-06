import pandas as pd
import numpy as np
from glob import glob
from sklearn import tree
from sklearn.externals.six import StringIO
from sklearn.metrics import accuracy_score
from sklearn.ensemble import RandomForestClassifier
from sklearn.feature_selection import SelectFromModel


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
        predicted = self.predict(self._train, int)
        accuracy = round(accuracy_score(self._targets, predicted) * 100.0, 2)
        print 'Accuracy: %s%%' % accuracy

    def print_tree(self):
        dot_data = StringIO()
        i = 1
        for tree_in_forest in self._model.estimators_:
            dot_data = tree.export_graphviz(tree_in_forest,
                                            out_file='tree_%s.dot' % str(i),
                                            feature_names=self._filtered_features,
                                            class_names=['away_win', 'home_win'],
                                            filled=True,
                                            rounded=True,
                                            special_characters=True)
            i += 1

    def simplify(self, test_data):
        self._test = test_data.loc[:, test_data.columns.isin(self._filtered_features)]
        self._test = self._test.reindex(self._filtered_features, axis=1)
        parameters = {'bootstrap': False,
                      'min_samples_leaf': 3,
                      'n_estimators': 50,
                      'min_samples_split': 10,
                      'max_features': 'sqrt',
                      'max_depth': 6}
        self._model = RandomForestClassifier(**parameters)
        self._model.fit(self._train, self._targets)
        return self._test

    def predict(self, test_data, output_datatype):
        return self._model.predict(test_data).astype(output_datatype)

    def _read_data(self):
        data = pd.DataFrame()

        for match in glob('matches/*'):
            data = data.append(pd.read_csv(match))
        return data

    def _create_features(self, data):
        self._targets = data.home_win
        train = data.drop('home_win', 1)
        train.drop('pts', 1, inplace=True)
        self._train = train.drop('opp_pts', 1)

    def _create_classifier(self):
        clf = RandomForestClassifier(n_estimators=50, max_features='sqrt')
        self._classifier = clf.fit(self._train, self._targets)

    def _train_model(self):
        train = self._train
        self._model = SelectFromModel(self._classifier, prefit=True)
        self._train = self._model.transform(self._train)
        new_columns = train.columns[self._model.get_support()]
        self._filtered_features = [str(col) for col in new_columns]
