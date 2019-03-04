import json
from datetime import datetime, timedelta
from sportsreference.ncaab.boxscore import Boxscores


def retrieve_yesterdays_date():
    yesterday = datetime.now() - timedelta(days=1)
    return '%s-%s-%s' % (yesterday.month, yesterday.day, yesterday.year)


def find_yesterdays_results():
    results = []

    games = Boxscores(datetime.now() - timedelta(days=1)).games
    yesterday = retrieve_yesterdays_date()
    for game in games[yesterday]:
        results.append([game['winning_abbr'], game['losing_abbr']])
    return results


def get_predictions_filename():
    yesterday = retrieve_yesterdays_date()
    filename = 'predictions/%s.json' % yesterday
    return filename


def open_json(filename):
    with open(filename) as f:
        data = json.loads(f.read())
    return data


def get_result(prediction):
    winner = str(prediction['predictedWinnerAbbreviation'])
    loser = str(prediction['predictedLoserAbbreviation'])
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
    print('='*80)
    print('  Accuracy: %s%%' % round(100.0 * float(correct) / \
                                     float(matches), 2))
    print('='*80)


def main():
    results = find_yesterdays_results()
    check_saved_predictions(results)


if __name__ == "__main__":
    main()
