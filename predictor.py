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
from sklearn.ensemble import RandomForestRegressor
from cuml.ensemble import RandomForestRegressor as curfc
from sklearn.feature_selection import SelectFromModel


DATASET_NAME = 'dataset.pkl'
HYPER_PARAMETERS = {'bootstrap': False,
                    'n_estimators': 50,
                    'max_features': 'sqrt',
                    'max_depth': 6}


class Predictor:
    def __init__(self):
        self._regressor = None
        self._model = None
        self._X_train = None
        self._X_test = None
        self._y_train = None
        self._y_test = None

        data = self._read_data()
        self._optimal_features = self._optimize_features(data)
        optimal_dataset = self._optimize_dataset(data, self._optimal_features)

    def simplify(self, test_data):
        data = test_data.loc[:, test_data.columns.isin(self._optimal_features)]
        self._model = curfc(**HYPER_PARAMETERS)
        self._model.fit(self._X_train, self._y_train)
        return data.to_numpy()

    def predict(self, test_data, output_datatype):
        print(self._model)
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

    def _optimize_features(self, data):
        #cudf_data = cudf.DataFrame.from_pandas(data)
        #X = cudf_data.drop('points_difference', 1)
        #y = cudf_data['points_difference']
        X = data.drop('points_difference', 1)
        y = data['points_difference']
        X_train, _, y_train, _ = train_test_split(X, y)
        regressor = self._create_regressor(X_train, y_train)
        features = self._select_features(regressor, X_train)
        return features

    def _create_regressor(self, X_train, y_train):
        reg = RandomForestRegressor(**HYPER_PARAMETERS)
        regressor = reg.fit(X_train, y_train)
        return regressor

    def _select_features(self, regressor, X_train):
        train = X_train
        model = SelectFromModel(regressor, prefit=True, threshold=0.01)
        X_train = model.transform(X_train)
        new_columns = train.columns[model.get_support()]
        return [str(col) for col in new_columns]

    def _optimize_dataset(self, data, optimal_features):
        #cudf_data = cudf.DataFrame.from_pandas(data)
        #X = data.drop('points_difference', 1)
        X = data.loc[:, optimal_features].to_numpy()
        #y = data['points_difference']
        y = data['points_difference'].to_numpy()
        split_data = train_test_split(X, y)
        self._X_train, self._X_test, self._y_train, self._y_test = split_data
