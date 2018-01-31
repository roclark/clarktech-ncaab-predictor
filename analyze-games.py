import argparse
import json
import os
import pandas as pd
import random
import re
import requests
from bs4 import BeautifulSoup
from common import (differential_vector,
                    read_team_stats_file)
from conferences import CONFERENCES
from constants import YEAR
from datetime import datetime
from predictor import Predictor
from save_json import save_predictions_json
from teams import TEAMS


AWAY = 0
HOME = 1
NUM_SIMS = 100
TEAM_NAME_REGEX = 'schools/.*?/%s.html' % YEAR
HOME_PAGE = 'http://www.sports-reference.com/cbb/'
FIELDS_TO_RENAME = {'win_loss_pct': 'win_pct'}


class MatchInfo:
    def __init__(self, away, home, away_nickname, home_nickname, top_25,
                 game_time, match_stats):
        self.away = away
        self.away_nickname = away_nickname
        self.game_time = game_time
        self.home = home
        self.home_nickname = home_nickname
        self.match_stats = match_stats
        self.top_25 = top_25


def team_ranked(team):
    with open('team-stats/%s.json' % team) as json_data:
        team_stats = json.load(json_data)
        if team_stats['rank'] != 'NR':
            return team_stats['rank']
        return None


def extract_team(team_link, top_25=False):
    try:
        team = re.findall(TEAM_NAME_REGEX, str(team_link))[0]
        team = team.replace('schools/', '')
        team = team.replace('/%s.html' % YEAR, '')
        name = team_link.get_text().strip()
        rank = team_ranked(team)
        if rank:
            name = '(%s) %s' % (rank, name)
            top_25 = True
        return team, name, top_25
    except IndexError:
        return None, None, None


def extract_teams_from_game(game_table):
    top_25 = False

    teams = game_table.find_all('a')
    try:
        away_team, away_name, top_25 = extract_team(teams[AWAY])
        home_team, home_name, top_25 = extract_team(teams[HOME], top_25)
    except IndexError:
        return None, None, None, None, None
    if not away_team or not home_team:
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


def create_prediction_data(match_data, inverted_conferences, winner, loser):
    tags = []
    if match_data.top_25:
        tags = ['Top 25']
    tags.append(inverted_conferences[match_data.home])
    tags.append(inverted_conferences[match_data.away])
    tags = list(set(tags))
    prediction = [tags, match_data.home_nickname, match_data.home,
                  match_data.away_nickname, match_data.away, winner,
                  loser, match_data.game_time]
    return prediction


def invert_conference_dict():
    new_dict = {}

    for conference, value in CONFERENCES.items():
        for team in value:
            new_dict[team] = conference
    return new_dict


def create_variance(stats, stdev_dict):
    local_stats = {}

    for stat in stats:
        min_val = -1 * float(stdev_dict[stat])
        max_val = abs(min_val)
        variance = random.uniform(min_val, max_val)
        new_value = float(stats[stat]) + variance
        local_stats[stat] = new_value
    return pd.DataFrame([local_stats])


def get_stats(stats_filename, stdev_dict, away=False):
    stats = read_team_stats_file(stats_filename)
    if stdev_dict:
        stats = create_variance(stats, stdev_dict)
    return extract_stats_components(stats, away)


def get_game_information(game, stdev_dict):
    away, home, away_name, home_name, top_25 = extract_teams_from_game(game)
    # Occurs when a DI school plays a non-DI school
    # The parser does not save stats for non-DI schools
    if away is None or home is None:
        return None
    game_time = find_game_time(game)
    away_stats = get_stats('team-stats/%s' % away, stdev_dict, away=True)
    home_stats = get_stats('team-stats/%s' % home, stdev_dict, away=False)
    match_stats = pd.concat([away_stats, home_stats], axis=1)
    m = MatchInfo(away, home, away_name, home_name, top_25, game_time,
                  match_stats)
    return m


def get_winner(probability):
    winner = max(probability, key=probability.get)
    loser = min(probability, key=probability.get)
    return winner, loser


def make_predictions(prediction_stats, games_list, match_info, predictor):
    prediction_list = []
    inverted_conferences = invert_conference_dict()

    prediction_data = pd.concat(prediction_stats)
    prediction_data = differential_vector(prediction_data)
    prediction_data.rename(columns=FIELDS_TO_RENAME, inplace=True)
    prediction_data = predictor.simplify(prediction_data)
    predictions = predictor.predict(prediction_data, int)
    probabilities = predictor.predict_probability(prediction_data)
    for sim in range(len(games_list) / NUM_SIMS):
        total_probability = {}
        for i in range(NUM_SIMS):
            x = sim * NUM_SIMS + i
            winner = games_list[x][1][predictions[x]]
            loser = games_list[x][1][abs(predictions[x]-1)]
            winner_prob = probabilities[x][predictions[x]]
            loser_prob = probabilities[x][abs(predictions[x]-1)]
            try:
                total_probability[winner] += winner_prob
            except KeyError:
                total_probability[winner] = winner_prob
            try:
                total_probability[loser] += loser_prob
            except KeyError:
                total_probability[loser] = loser_prob
        winner, loser = get_winner(total_probability)
        display_prediction(games_list[sim*NUM_SIMS][0], winner)
        p = create_prediction_data(match_info[sim*NUM_SIMS],
                                   inverted_conferences, winner, loser)
        prediction_list.append(p)
    return prediction_list


def find_stdev_for_every_stat():
    stats_list = []
    stdev_dict = {}

    for team in TEAMS.values():
        stats_list.append(get_stats('team-stats/%s' % team, None))
    stats_dataframe = pd.concat(stats_list)
    for col in stats_dataframe:
        stdev_dict[col] = stats_dataframe[col].std()
    return stdev_dict


def parse_boxscores(boxscore_html, predictor):
    games_list = []
    match_info = []
    prediction_stats = []

    stdev_dict = find_stdev_for_every_stat()
    games_table = boxscore_html.find('div', {'class': '', 'id': 'games'})
    # The value at index 0 corresponds to today's games
    games_table = games_table.find_all('div')[0]
    games = games_table.find_all('span')
    for game in games:
        for sim in range(NUM_SIMS):
            g = get_game_information(game, stdev_dict)
            if not g:
                continue
            games_list.append(['%s at %s' % (g.away_nickname, g.home_nickname),
                              [g.home_nickname, g.away_nickname]])
            prediction_stats.append(g.match_stats)
            match_info.append(g)
    predictions = make_predictions(prediction_stats, games_list, match_info,
                                   predictor)
    save_predictions(predictions)


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
