import json
import re
import requests
from bs4 import BeautifulSoup
from datetime import datetime, timedelta


SCORES_PAGE = 'http://www.sports-reference.com/cbb/boxscores/index.cgi?month='


def retrieve_yesterdays_url():
    yesterday = datetime.now() - timedelta(days=1)
    url = '%s%s&day=%s&year=%s' % (SCORES_PAGE,
                                   yesterday.month,
                                   yesterday.day,
                                   yesterday.year)
    return url


def parse_team(game):
    team = re.sub('/\d+.html.*', '', str(game.a))
    team = re.sub('.*/', '', team)
    return team


def find_result(game):
    winner = parse_team(game.find('tr', {'class': 'winner'}))
    loser = parse_team(game.find('tr', {'class': 'loser'}))
    # When a team plays a non-DI opponent, the result is 'a>'. Since we don't
    # predict non-DI games, we throw these results out.
    if winner == 'a>' or loser == 'a>':
        return None
    return [winner, loser]


def parse_boxscores(boxscore_html):
    results = []

    games_table = boxscore_html.find('div', {'class': 'game_summaries'})
    games = games_table.find_all('tbody')
    for game in games:
        result = find_result(game)
        if result:
            results.append(result)
    return results


def find_yesterdays_games():
    url = retrieve_yesterdays_url()
    boxscores = requests.get(url)
    boxscore_html = BeautifulSoup(boxscores.text, 'lxml')
    results = parse_boxscores(boxscore_html)
    return results


def get_predictions_filename():
    yesterday = datetime.now() - timedelta(days=1)
    filename = 'predictions/%s-%s-%s.json' % (yesterday.month,
                                              yesterday.day,
                                              yesterday.year)
    return filename


def open_json(filename):
    with open(filename) as f:
        data = json.loads(f.read())
    return data


def get_result(prediction):
    winner = str(prediction['prediction']['prediction']['winner']['nickname'])
    loser = str(prediction['prediction']['prediction']['loser']['nickname'])
    return [winner, loser]


def get_predictions(predictions):
    results = []

    for prediction in predictions:
        results.append(get_result(prediction))
    return results


def check_saved_predictions(results):
    filename = get_predictions_filename()
    data = open_json(filename)
    predictions = get_predictions(data['predictions'])

    correct = 0
    matches = len(results)
    for result in results:
        if result in predictions:
            correct += 1
    print '='*80
    print '  Accuracy: %s%%' % round(100.0 * float(correct) / float(matches), 2)
    print '='*80


def main():
    results = find_yesterdays_games()
    check_saved_predictions(results)


if __name__ == "__main__":
    main()
