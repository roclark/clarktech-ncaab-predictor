import json
from datetime import datetime
from os import listdir
from os.path import isfile, join
from save_json import save_json
from sportsreference.ncaab.boxscore import Boxscores


def corresponding_matchup(prediction, winner, loser):
    if prediction['homeAbbreviation'] == winner and \
       prediction['awayAbbreviation'] == loser:
        return True
    elif prediction['homeAbbreviation'] == loser and \
         prediction['awayAbbreviation'] == winner:
        return True
    return False


def correct_pick(predicted_winner, actual_winner):
    if predicted_winner == actual_winner:
        return True
    return False


def get_mascots(winner, loser, prediction):
    if winner == prediction['homeAbbreviation']:
        return prediction['homeMascot'], prediction['awayMascot']
    return prediction['awayMascot'], prediction['homeMascot']


def save_result(saved_data, game):
    winner, loser = game['winning_abbr'], game['losing_abbr']
    for prediction in saved_data['predictions']:
        if corresponding_matchup(prediction, winner, loser):
            correct = correct_pick(prediction['predictedWinnerAbbreviation'],
                                   winner)
            winning_mascot, losing_mascot = get_mascots(winner, loser,
                                                        prediction)
            prediction['actualWinner'] = game['winning_name']
            prediction['actualWinnerAbbreviation'] = game['winning_abbr']
            prediction['actualWinnerMascot'] = winning_mascot
            prediction['actualLoser'] = game['losing_name']
            prediction['actualLoserAbbreviation'] = game['losing_abbr']
            prediction['actualLoserMascot'] = losing_mascot
            prediction['actualHomeScore'] = game['home_score']
            prediction['actualAwayScore'] = game['away_score']
            prediction['accuratePick'] = correct
            return saved_data, correct
    return saved_data, None


def parse_boxscore(games, saved_data):
    num_games = 0
    num_correct = 0

    for game in games:
        saved_data, correct = save_result(saved_data, game)
        if correct:
            num_correct += 1
        num_games += 1
    return saved_data, num_games, num_correct


def get_date(filename):
    month, day, year = filename.replace('.json', '').split('-')
    return datetime(int(year), int(month), int(day))


def get_saved_prediction(filename):
    with open('predictions/%s' % filename) as prediction:
        return json.load(prediction)


def iterate_files(files):
    total_games = 0
    total_correct = 0

    for filename in files:
        date = get_date(filename)
        saved_data = get_saved_prediction(filename)
        games = Boxscores(date).games[filename.replace('.json', '')]
        saved_data, num_games, num_correct = parse_boxscore(games, saved_data)
        total_games += num_games
        total_correct += num_correct
        save_json(saved_data, 'predictions/%s' % filename)
    print('=' * 80)
    print('  Accuracy: %s%%' % round(100.0 * float(total_correct) / \
                                     float(total_games), 2))
    print('=' * 80)


def get_files():
    return [f for f in listdir('predictions') if isfile(join('predictions', f))]


def main():
    files = get_files()
    iterate_files(files)


if __name__ == "__main__":
    main()
