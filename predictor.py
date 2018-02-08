import pandas as pd
import numpy as np
from common import differential_vector
from glob import glob
from sklearn import tree
from sklearn.externals.six import StringIO
from sklearn.metrics import accuracy_score
from sklearn.model_selection import train_test_split
from sklearn.ensemble import RandomForestRegressor
from sklearn.feature_selection import SelectFromModel


class Predictor:
    def __init__(self, data_directory='matches'):
        self._classifier = None
        self._model = None
        self._X_train = None
        self._X_test = None
        self._y_train = None
        self._y_test = None

        data = self._read_data(data_directory)
        self._create_features(data)
        self._create_classifier()
        self._train_model()

    @property
    def accuracy(self):
        predicted = self.predict(self._X_test, int)
        accuracy = round(accuracy_score(self._y_test, predicted) * 100.0, 2)
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
        test_data = test_data.loc[:, test_data.columns.isin(self._filtered_features)]
        test_data = test_data.reindex(self._filtered_features, axis=1)
        self._X_test = self._X_test.reindex(self._filtered_features, axis=1)
        parameters = {'bootstrap': False,
                      'min_samples_leaf': 3,
                      'n_estimators': 50,
                      'min_samples_split': 10,
                      'max_features': 'sqrt',
                      'max_depth': 6}
        self._model = RandomForestRegressor(**parameters)
        self._model.fit(self._X_train, self._y_train)
        return test_data

    def predict(self, test_data, output_datatype):
        return self._model.predict(test_data).astype(output_datatype)

    def _read_data(self, data_directory):
        frames = [pd.read_csv(match) for match in glob('%s/*' % data_directory) \
                  if not match.endswith('.json')]
        data = pd.concat(frames)
        data.drop('home_win', 1)
        return differential_vector(data)

    def _create_features(self, data):
        X = data.drop('pts', 1)
        X = data.drop('opp_pts', 1)
        X = data.drop('home_win', 1)
        y = data.as_matrix(columns=['pts', 'opp_pts'])
        split_data = train_test_split(X, y)
        self._X_train, self._X_test, self._y_train, self._y_test = split_data

    def _create_classifier(self):
        clf = RandomForestRegressor(n_estimators=50, max_features='sqrt')
        self._classifier = clf.fit(self._X_train, self._y_train)

    def _train_model(self):
        train = self._X_train
        self._model = SelectFromModel(self._classifier, prefit=True)
        self._X_train = self._model.transform(self._X_train)
        new_columns = train.columns[self._model.get_support()]
        self._filtered_features = [str(col) for col in new_columns]
