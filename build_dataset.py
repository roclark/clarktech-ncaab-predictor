import pandas as pd
from common import filter_stats
from glob import iglob


DATASET_NAME = 'dataset.pkl'


def build_dataset(data_directory='matches'):
    data = pd.DataFrame()
    frames = []
    for i, match in enumerate(iglob('%s/*/*' % data_directory)):
        if not i % 1000:
            data = pd.concat([data] + frames)
            frames = []
            continue
        frames.append(pd.read_pickle(match))
    return data


def process_dataset(data):
    data.drop_duplicates(inplace=True)
    data = filter_stats(data)
    data = data.dropna()
    data['home_free_throw_percentage'].fillna(0, inplace=True)
    data['away_free_throw_percentage'].fillna(0, inplace=True)
    data['points_difference'] = data['home_points'] - data['away_points']
    data.to_pickle(DATASET_NAME)


if __name__ == '__main__':
    data = build_dataset()
    process_dataset(data)
