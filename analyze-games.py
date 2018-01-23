import argparse
import json
import numpy
import os
import pandas as pd
import re
import requests
from bs4 import BeautifulSoup
from common import (differential_vector,
                    find_name_from_nickname,
                    read_team_stats_file)
from conferences import CONFERENCES
from constants import YEAR
from datetime import datetime
from predictor import Predictor
from save_json import save_predictions_json
from teams import TEAMS


AWAY = 0
HOME = 1
TEAM_NAME_REGEX = 'schools/.*?/%s.html' % YEAR
HOME_PAGE = 'http://www.sports-reference.com/cbb/'


def team_ranked(team):
    with open('team-stats/%s.json' % team) as json_data:
        team_stats = json.load(json_data)
        if team_stats['rank'] != 'NR':
            return team_stats['rank']
        return None


def extract_teams_from_game(game_table):
    top_25 = False

    teams = game_table.find_all('a')
    try:
        away_team = re.findall(TEAM_NAME_REGEX, str(teams[AWAY]))[0]
        away_team = away_team.replace('schools/', '')
        away_team = away_team.replace('/%s.html' % YEAR, '')
        away_name = teams[AWAY].get_text().strip()
        rank = team_ranked(away_team)
        if rank:
            away_name = '(%s) %s' % (rank, away_name)
            top_25 = True
    except IndexError:
        return None, None, None, None, None
    try:
        home_team = re.findall(TEAM_NAME_REGEX, str(teams[HOME]))[0]
        home_team = home_team.replace('schools/', '')
        home_team = home_team.replace('/%s.html' % YEAR, '')
        home_name = teams[HOME].get_text().strip()
        rank = team_ranked(home_team)
        if rank:
            home_name = '(%s) %s' % (rank, home_name)
            top_25 = True
    except IndexError:
        return None, None, None, None, None
    return away_team, home_team, away_name, home_name, top_25


def find_game_time(game_table):
    time = re.findall('\d+:\d+ [A|P]M', str(game_table))
    return time[0]


def save_predictions(predictions):
    today = datetime.now()
    if not os.path.exists('predictions'):
        os.makedirs('predictions')
    filename = 'predictions/%s-%s-%s.json' % (today.month,
                                              today.day,
                                              today.year)
    save_predictions_json(predictions, filename)


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


def create_prediction_data(home_name, home_nickname, away_name, away_nickname,
                           top_25, winner, loser, inverted_conferences,
                           game_time):
    tags = []
    if top_25:
        tags = ['Top 25']
    tags.append(inverted_conferences[home_nickname])
    tags.append(inverted_conferences[away_nickname])
    tags = list(set(tags))
    prediction = [tags, home_name, home_nickname, away_name, away_nickname,
                  winner, loser, game_time]
    return prediction


def invert_conference_dict():
    new_dict = {}

    for conference, value in CONFERENCES.items():
        for team in value:
            new_dict[team] = conference
    return new_dict


def parse_boxscores(boxscore_html, predictor):
    games_list = []
    prediction_list = []
    t_25_games_list = []
    match_info = []
    t_25_match_info = []
    fields_to_rename = {'win_loss_pct': 'win_pct'}
    prediction_stats = pd.DataFrame()
    t_25_predictions = pd.DataFrame()
    inverted_conferences = invert_conference_dict()

    games_table = boxscore_html.find('div', {'class': '', 'id': 'games'})
    # The value at index 0 corresponds to today's games
    games_table = games_table.find_all('div')[0]
    games = games_table.find_all('span')
    for game in games:
        away, home, away_name, home_name, top_25 = extract_teams_from_game(game)
        game_time = find_game_time(game)
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
            t_25_match_info.append([home_name, home, away_name, away, top_25,
                                    game_time])
        else:
            games_list.append(['%s at %s' % (away_name, home_name),
                              [home_name, away_name]])
            prediction_stats = prediction_stats.append(match_stats)
            match_info.append([home_name, home, away_name, away, top_25,
                               game_time])

    t_25_data = [t_25_predictions, t_25_games_list, 'Top 25 Games',
                 t_25_match_info]
    d1_data = [prediction_stats, games_list, 'NCAA Division-I Games',
               match_info]
    games_parsed = 0
    for dataset in [t_25_data, d1_data]:
        prediction_stats, games_list, heading, match_info = dataset
        if len(games_list) == 0:
            continue
        print '=' * 80
        print '  %s' % heading
        print '=' * 80
        differential_stats_vector = differential_vector(prediction_stats)
        differential_stats_vector.rename(columns=fields_to_rename, inplace=True)
        match_stats_simplified = predictor.simplify(differential_stats_vector)
        predictions = predictor.predict(match_stats_simplified, int)
        probabilities = predictor.predict_probability(match_stats_simplified)
        for i in range(0, len(games_list)):
            winner = games_list[i][1][predictions[i]]
            loser = games_list[i][1][abs(predictions[i]-1)]
            display_prediction(games_list[i][0], winner)
            home, home_nickname, away, away_nickname, top_25, game_time = \
                match_info[i]
            p = create_prediction_data(home, home_nickname, away, away_nickname,
                                       top_25, winner, loser,
                                       inverted_conferences, game_time)
            prediction_list.append(p)
            games_parsed += 1
    print '=' * 80
    if games_parsed == 0:
        print '  No games scheduled for today'
        print '=' * 80
        return
    save_predictions(prediction_list)


def find_todays_games(predictor):
    boxscores = requests.get(HOME_PAGE)
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
