import cudf
import pandas as pd
import numpy as np
from common import differential_vector, filter_stats
from glob import glob
from os import path
from sklearn import tree
from sklearn.externals.six import StringIO
from sklearn.metrics import accuracy_score
from sklearn.model_selection import train_test_split
#from sklearn.ensemble import RandomForestRegressor
from cuml.ensemble import RandomForestRegressor
from sklearn.feature_selection import SelectFromModel


DATASET_NAME = 'dataset.pkl'


class Predictor:
    def __init__(self):
        self._regressor = None
        self._model = None
        self._X_train = None
        self._X_test = None
        self._y_train = None
        self._y_test = None

        data = self._read_data()
        self._create_features(data)
        self._create_regressor()
        self._train_model()

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

    def _read_data(self):
        if path.exists(DATASET_NAME):
            data = pd.read_pickle(DATASET_NAME)
            return differential_vector(data)
        frames = [pd.read_pickle(match) for match in \
                  glob('matches/*/*')]
        data = pd.concat(frames)
        data.drop_duplicates(inplace=True)
        data = filter_stats(data)
        data = data.dropna()
        data['home_free_throw_percentage'].fillna(0, inplace=True)
        data['away_free_throw_percentage'].fillna(0, inplace=True)
        data['points_difference'] = data['home_points'] - data['away_points']
        return differential_vector(data)

    def _create_features(self, data):
        cudf_data = cudf.DataFrame.from_pandas(data)
        X = cudf_data.drop('points_difference', 1)
        y = cudf_data['points_difference']
        split_data = train_test_split(X, y)
        self._X_train, self._X_test, self._y_train, self._y_test = split_data

    def _create_regressor(self):
        reg = RandomForestRegressor(n_estimators=50, max_features='sqrt')
        self._regressor = reg.fit(self._X_train, self._y_train)

    def _train_model(self):
        train = self._X_train
        self._model = SelectFromModel(self._regressor, prefit=True,
                                      threshold=0.01)
        self._X_train = self._model.transform(self._X_train)
        new_columns = train.columns[self._model.get_support()]
        self._filtered_features = [str(col) for col in new_columns]
