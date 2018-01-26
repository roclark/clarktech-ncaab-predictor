import json
import re
import requests
from bs4 import BeautifulSoup
from constants import YEAR
from os import listdir
from os.path import isfile, join
from save_json import save_json


SCORES_PAGE = 'http://www.sports-reference.com/cbb/boxscores/index.cgi?month='
TEAM_NAME_REGEX = 'schools/.*?/%s.html' % YEAR


def get_name(name):
    try:
        name = re.findall(TEAM_NAME_REGEX, str(name[0]))[0]
        name = name.replace('schools/', '')
        name = name.replace('/%s.html' % YEAR, '')
    except IndexError:
        return None
    return name


def find_teams(result):
    winner = get_name(result.find_all('tr', {'class': 'winner'}))
    loser = get_name(result.find_all('tr', {'class': 'loser'}))
    if not winner or not loser:
        return None, None
    return winner, loser


def corresponding_matchup(prediction, winner, loser):
    if prediction['teams']['home']['nickname'] == winner and \
       prediction['teams']['away']['nickname'] == loser:
        return True
    elif prediction['teams']['home']['nickname'] == loser and \
         prediction['teams']['away']['nickname'] == winner:
        return True
    return False


def correct_pick(teams, winner):
    if teams['winner']['nickname'] == winner:
        return True
    return False


def save_result(saved_data, winner, loser):
    for prediction in saved_data['predictions']:
        if corresponding_matchup(prediction['prediction'], winner, loser):
            correct = correct_pick(prediction['prediction']['prediction'],
                                   winner)
            prediction['prediction']['results'] = {'winner': winner,
                                                   'loser': loser,
                                                   'correct': correct}
            return saved_data, correct
    return saved_data, None


def parse_boxscore(boxscore, saved_data):
    results = boxscore.find_all('tbody')
    num_games = 0
    num_correct = 0
    for result in results:
        winner, loser = find_teams(result)
        if not winner or not loser:
            continue
        saved_data, correct = save_result(saved_data, winner, loser)
        if correct:
            num_correct += 1
        num_games += 1
    if num_games > 0:
        accuracy = 100.0 * float(num_correct) / float(num_games)
        saved_data['accuracy'] = accuracy
    return saved_data


def get_url(filename):
    month, day, year = filename.replace('.json', '').split('-')
    url = '%s%s&day=%s&year=%s' % (SCORES_PAGE, month.rjust(2, '0'), day, year)
    return url


def get_saved_prediction(filename):
    with open('predictions/%s' % filename) as prediction:
        return json.load(prediction)


def iterate_files(files):
    for filename in files:
        url = get_url(filename)
        saved_data = get_saved_prediction(filename)
        boxscores = requests.get(url)
        saved_data = parse_boxscore(BeautifulSoup(boxscores.text, 'lxml'),
                                    saved_data)
        save_json(saved_data, 'predictions/%s' % filename)


def get_files():
    return [f for f in listdir('predictions') if isfile(join('predictions', f))]


def main():
    files = get_files()
    iterate_files(files)


if __name__ == "__main__":
    main()
