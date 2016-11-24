import numpy
import re
import requests

from bs4 import BeautifulSoup
from common import create_stats_array, read_team_stats_file
from datetime import datetime
from predictor import Predictor
from teams import TEAMS


AWAY = 0
HOME = 1
SCORES_PAGE = 'http://www.sports-reference.com/cbb/boxscores/index.cgi?month='


def retrieve_todays_url():
    today = datetime.now()
    url = '%s%s&day=%s&year=%s' % (SCORES_PAGE,
                                   today.month,
                                   today.day,
                                   today.year)
    return url


def extract_teams_from_game(game_table):
    teams = game_table.find_all('a')
    try:
        away_team = re.findall('schools/.*?/2017.html', str(teams[AWAY]))[0]
        away_team = away_team.replace('schools/', '').replace('/2017.html', '')
    except IndexError:
        return None, None
    try:
        home_team = re.findall('schools/.*?/2017.html', str(teams[HOME]))[0]
        home_team = home_team.replace('schools/', '').replace('/2017.html', '')
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


def parse_boxscores(boxscore_html, predictor):
    predictions = []

    games_table = boxscore_html.find('div', {'class': 'game_summaries'})
    games = games_table.find_all('tbody')
    for game in games:
        away, home = extract_teams_from_game(game)
        if away is None or home is None:
            # Occurs when a DI school plays a non-DI school
            # The parser does not save stats for non-DI schools
            continue
        away_name, away_stats = read_team_stats_file('team-stats/%s' % away)
        home_name, home_stats = read_team_stats_file('team-stats/%s' % home)
        match_stats = create_stats_array(eval(away_stats), eval(home_stats))
        match_stats = numpy.array([match_stats])
        prediction = predictor.predict(match_stats)
        if prediction[0] == AWAY:
            predictions.append(['%s vs. %s' % (away_name, home_name),
                                away_name])
        else:
            predictions.append(['%s vs. %s' % (away_name, home_name),
                                home_name])
    display_predictions(predictions)
    save_predictions(predictions)


def find_todays_games(predictor):
    url = retrieve_todays_url()
    boxscores = requests.get(url)
    boxscore_html = BeautifulSoup(boxscores.text, 'html5lib')
    parse_boxscores(boxscore_html, predictor)


def main():
    predictor = Predictor()
    find_todays_games(predictor)


if __name__ == "__main__":
    main()
