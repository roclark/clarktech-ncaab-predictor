import numpy
import pandas as pd
import re
import requests
from bs4 import BeautifulSoup
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


def read_team_stats_file(team_filename):
    return pd.read_csv(team_filename)


def extract_teams_from_game(game_table):
    teams = game_table.find_all('a')
    try:
        away_team = re.findall(TEAM_NAME_REGEX, str(teams[AWAY]))[0]
        away_team = away_team.replace('schools/', '')
        away_team = away_team.replace('/%s.html' % YEAR, '')
    except IndexError:
        return None, None
    try:
        home_team = re.findall(TEAM_NAME_REGEX, str(teams[HOME]))[0]
        home_team = home_team.replace('schools/', '')
        home_team = home_team.replace('/%s.html' % YEAR, '')
    except IndexError:
        return None, None
    return away_team, home_team


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

    for field in fields_to_average:
        stats[field] = float(stats[field]) / num_games
    return stats


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


def filter_stats(match_stats):
    fields_to_drop = ['pts', 'opp_pts', 'g', 'opp_g', 'opp_pts_per_g',
                      'pts_per_g']
    for field in fields_to_drop:
        match_stats.drop(field, 1, inplace=True)
    return match_stats


def parse_boxscores(boxscore_html, predictor):
    games_list = []
    prediction_stats = pd.DataFrame()

    games_table = boxscore_html.find('div', {'class': 'game_summaries'})
    games = games_table.find_all('tbody')
    for game in games:
        home, away = extract_teams_from_game(game)
        if away is None or home is None:
            # Occurs when a DI school plays a non-DI school
            # The parser does not save stats for non-DI schools
            continue
        away_stats = read_team_stats_file('team-stats/%s' % away)
        home_stats = read_team_stats_file('team-stats/%s' % home)
        away_filter = extract_stats_components(away_stats, away=True)
        home_filter = extract_stats_components(home_stats, away=False)
        match_stats = pd.concat([away_filter, home_filter], axis=1)
        match_stats = filter_stats(match_stats)
        prediction_stats = prediction_stats.append(match_stats)
        games_list.append(['%s at %s' % (away, home), [home, away]])
    match_stats_simplified = predictor.simplify(prediction_stats)
    predictions = predictor.predict(match_stats_simplified, int)
    for i in range(0, len(games_list)):
        print games_list[i][0], games_list[i][1][predictions[i]]


def find_todays_games(predictor):
    url = retrieve_todays_url()
    boxscores = requests.get(url)
    boxscore_html = BeautifulSoup(boxscores.text, 'html5lib')
    parse_boxscores(boxscore_html, predictor)


def main():
    predictor = Predictor()
    find_todays_games(predictor)
    predictor.accuracy


if __name__ == "__main__":
    main()
