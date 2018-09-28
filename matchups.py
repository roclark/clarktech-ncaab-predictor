import argparse
import numpy
import pandas as pd
import re
from common import differential_vector, filter_stats, read_team_stats_file
from constants import YEAR
from datetime import datetime
from predictor import Predictor
from teams import TEAMS


AWAY = 1
HOME = 0
TEAM_NAME_REGEX = 'schools/.*?/%s.html' % YEAR
SCORES_PAGE = 'http://www.sports-reference.com/cbb/boxscores/index.cgi?month='


def retrieve_todays_url():
    today = datetime.now()
    url = '%s%s&day=%s&year=%s' % (SCORES_PAGE,
                                   today.month,
                                   today.day,
                                   today.year)
    return url


def save_predictions(predictions):
    today = datetime.now()
    filename = 'predictions/%s-%s-%s' % (today.month, today.day, today.year)
    with open(filename, 'w') as prediction_file:
        for prediction in predictions:
            prediction_file.write('%s,%s\n' % (prediction[0], prediction[1]))


def display_predictions(predictions):
    max_word_length = max(len(prediction[0]) for prediction in predictions)
    for prediction in predictions:
        teams = prediction[0].ljust(max_word_length + 3)
        print '%s => %s' % (teams, prediction[1])


def convert_team_totals_to_averages(stats):
    fields_to_average = ['mp', 'fg', 'fga', 'fg2', 'fg2a', 'fg3', 'fg3a', 'ft',
                         'fta', 'orb', 'drb', 'trb', 'ast', 'stl', 'blk', 'tov',
                         'pf', 'pts']
    num_games = stats['g']
    new_stats = stats.copy()

    for field in fields_to_average:
        new_value = float(stats[field]) / num_games
        new_stats.loc[:,field] = new_value
    return new_stats


def extract_stats_components(stats, away=False):
    # Get all of the stats that don't start with 'opp', AKA all of the
    # stats that are directly related to the indicated team.
    filtered_columns = [col for col in stats if not str(col).startswith('opp')]
    stats = stats[filtered_columns]
    stats = convert_team_totals_to_averages(stats)
    if away:
        # Prepend all stats with 'opp_' to signify the away team as such.
        away_columns = ['opp_%s' % col for col in stats]
        stats.columns = away_columns
    return stats


def create_matchup_stats(home_team, away_team):
    away_stats = read_team_stats_file('team-stats/%s' % away_team)
    home_stats = read_team_stats_file('team-stats/%s' % home_team)
    away_stats = extract_stats_components(away_stats, away=True)
    home_stats = extract_stats_components(home_stats)
    match_stats = pd.concat([away_stats, home_stats], axis=1)
    return match_stats


def arguments():
    parser = argparse.ArgumentParser()
    parser.add_argument('home', help='Specify the home team in the matchup.')
    parser.add_argument('away', help='Specify the away team in the matchup.')
    parser.add_argument('--dataset', help='Specify which dataset to use. For '
    'testing purposes, use the "sample-data" directory. For production '
    'deployments, use "matches" with current data that was pulled.',
    default='matches')
    return parser.parse_args()


def main():
    fields_to_rename = {'win_loss_pct': 'win_pct',
                        'opp_win_loss_pct': 'opp_win_pct'}

    args = arguments()
    predictor = Predictor(args.dataset)
    match_stats = create_matchup_stats(args.home, args.away)
    match_stats.rename(columns=fields_to_rename, inplace=True)
    match_stats = differential_vector(match_stats)
    match_stats_simplified = predictor.simplify(match_stats)
    prediction = predictor.predict(match_stats_simplified, int)
    if prediction[0] == 1:
        print args.home
    else:
        print args.away
    predictor.accuracy


if __name__ == "__main__":
    main()
