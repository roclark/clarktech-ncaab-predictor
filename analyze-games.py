import argparse
import numpy
import pandas as pd
import re
import requests
from bs4 import BeautifulSoup
from common import (differential_vector,
                    find_name_from_nickname,
                    read_team_stats_file)
from constants import YEAR
from datetime import datetime
from predictor import Predictor
from teams import TEAMS


AWAY = 0
HOME = 1
TEAM_NAME_REGEX = 'schools/.*?/%s.html' % YEAR
SCORES_PAGE = 'http://www.sports-reference.com/cbb/boxscores/index.cgi?month='


def retrieve_todays_url():
    today = datetime.now()
    url = '%s%s&day=%s&year=%s' % (SCORES_PAGE,
                                   today.month,
                                   today.day,
                                   today.year)
    return url


def extract_teams_from_game(game_table):
    top_25 = False

    teams = game_table.find_all('a')
    ranks = re.findall('<a .*?</td>', str(game_table))
    try:
        away_team = re.findall(TEAM_NAME_REGEX, str(teams[AWAY]))[0]
        away_team = away_team.replace('schools/', '')
        away_team = away_team.replace('/%s.html' % YEAR, '')
        away_name = find_name_from_nickname(away_team)
        away_rank = re.findall('\(\d+\)', ranks[AWAY])
        if len(away_rank) > 0:
            away_name = '%s %s' % (away_rank[0], away_name)
            top_25 = True
    except IndexError:
        return None, None, None, None, None
    try:
        home_team = re.findall(TEAM_NAME_REGEX, str(teams[HOME]))[0]
        home_team = home_team.replace('schools/', '')
        home_team = home_team.replace('/%s.html' % YEAR, '')
        home_name = find_name_from_nickname(home_team)
        home_rank = re.findall('\(\d+\)', ranks[HOME])
        if len(home_rank) > 0:
            home_name = '%s %s' % (home_rank[0], home_name)
            top_25 = True
    except IndexError:
        return None, None, None, None, None
    return away_team, home_team, away_name, home_name, top_25


def save_predictions(predictions):
    today = datetime.now()
    filename = 'predictions/%s-%s-%s' % (today.month, today.day, today.year)
    with open(filename, 'w') as prediction_file:
        for prediction in predictions:
            prediction_file.write('%s,%s\n' % (prediction[0], prediction[1]))


def display_prediction(matchup, result):
    print '%s => %s' % (matchup, result)


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


def parse_boxscores(boxscore_html, predictor):
    games_list = []
    t_25_games_list = []
    fields_to_rename = {'win_loss_pct': 'win_pct'}
    prediction_stats = pd.DataFrame()
    t_25_predictions = pd.DataFrame()

    games_table = boxscore_html.find('div', {'class': 'game_summaries'})
    games = games_table.find_all('tbody')
    for game in games:
        away, home, away_name, home_name, top_25 = extract_teams_from_game(game)
        if away is None or home is None:
            # Occurs when a DI school plays a non-DI school
            # The parser does not save stats for non-DI schools
            continue
        away_stats = read_team_stats_file('team-stats/%s' % away)
        home_stats = read_team_stats_file('team-stats/%s' % home)
        away_filter = extract_stats_components(away_stats, away=True)
        home_filter = extract_stats_components(home_stats, away=False)
        match_stats = pd.concat([away_filter, home_filter], axis=1)
        if top_25:
            t_25_games_list.append(['%s at %s' % (away_name, home_name),
                                   [home_name, away_name]])
            t_25_predictions = t_25_predictions.append(match_stats)
        else:
            games_list.append(['%s at %s' % (away_name, home_name),
                              [home_name, away_name]])
            prediction_stats = prediction_stats.append(match_stats)
    for dataset in [[t_25_predictions, t_25_games_list, 'Top 25 Games'],
                    [prediction_stats, games_list, 'NCAA Division-I Games']]:
        prediction_stats, games_list, heading = dataset
        print '=' * 80
        print '  %s' % heading
        print '=' * 80
        differential_stats_vector = differential_vector(prediction_stats)
        differential_stats_vector.rename(columns=fields_to_rename, inplace=True)
        match_stats_simplified = predictor.simplify(differential_stats_vector)
        predictions = predictor.predict(match_stats_simplified, int)
        for i in range(0, len(games_list)):
            display_prediction(games_list[i][0],
                               games_list[i][1][predictions[i]])
    print '=' * 80


def find_todays_games(predictor):
    url = retrieve_todays_url()
    boxscores = requests.get(url)
    boxscore_html = BeautifulSoup(boxscores.text, 'lxml')
    parse_boxscores(boxscore_html, predictor)


def arguments():
    parser = argparse.ArgumentParser()
    parser.add_argument('--dataset', help='Specify which dataset to use. For '
    'testing purposes, use the "sample-data" directory. For production '
    'deployments, use "matches" with current data that was pulled.',
    default='matches')
    return parser.parse_args()


def main():
    args = arguments()
    predictor = Predictor(args.dataset)
    find_todays_games(predictor)
    predictor.accuracy


if __name__ == "__main__":
    main()
