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
            return saved_data
    return saved_data


def parse_boxscore(games, saved_data):
    for game in games:
        saved_data = save_result(saved_data, game)
    return saved_data


def get_date(filename):
    month, day, year = filename.replace('.json', '').split('-')
    return datetime(int(year), int(month), int(day))


def get_saved_prediction(filename):
    with open('predictions/%s' % filename) as prediction:
        return json.load(prediction)


def iterate_files(files):
    for filename in files:
        date = get_date(filename)
        saved_data = get_saved_prediction(filename)
        games = Boxscores(date).games[filename.replace('.json', '')]
        saved_data = parse_boxscore(games, saved_data)
        save_json(saved_data, 'predictions/%s' % filename)


def get_files():
    return [f for f in listdir('predictions') if isfile(join('predictions', f))]


def main():
    files = get_files()
    iterate_files(files)


if __name__ == "__main__":
    main()
