import argparse
import json
import os
import pandas as pd
import random
import re
from common import (differential_vector,
                    extract_stats_components,
                    read_team_stats_file)
from constants import YEAR
from datetime import datetime
from mascots import MASCOTS
from predictor import Predictor
from pymongo import MongoClient
from save_json import save_predictions_json
from sportsreference.ncaab.boxscore import Boxscores
from sportsreference.ncaab.conferences import Conferences
from sportsreference.ncaab.teams import Teams


AWAY = 0
HOME = 1
NUM_SIMS = 100
FIELDS_TO_RENAME = {'win_loss_pct': 'win_pct'}
FIELDS_TO_DROP = ['abbreviation', 'conference', 'name']


class GameInfo:
    def __init__(self, home, away, title):
        self.home = home
        self.away = away
        self.title = title


class Team:
    def __init__(self, name, abbreviation):
        self.name = name
        self.abbreviation = abbreviation


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


def save_to_mongodb(predictions):
    client = MongoClient()
    db = client.clarktechsports
    # Clear all of the existing predictions and add predictions for the
    # current day
    db.predictions.update_many({}, {'$set': {'latest': False}})
    db.predictions.insert_many(predictions)


def save_predictions(predictions, skip_save_to_mongodb):
    today = datetime.now()
    if not os.path.exists('predictions'):
        os.makedirs('predictions')
    filename = 'predictions/%s-%s-%s.json' % (today.month,
                                              today.day,
                                              today.year)
    save_predictions_json(predictions, filename)
    if not skip_save_to_mongodb:
        save_to_mongodb(predictions)


def display_prediction(matchup, result):
    print '%s => %s' % (matchup, result)


def convert_team_totals_to_averages(stats):
    fields_to_average = ['assists', 'blocks', 'defensive_rebounds',
                         'field_goal_attempts', 'field_goals',
                         'free_throw_attempts', 'free_throws',
                         'minutes_played', 'offensive_rebounds',
                         'personal_fouls', 'points', 'steals',
                         'three_point_field_goal_attempts',
                         'three_point_field_goals', 'total_rebounds',
                         'turnovers', 'two_point_field_goal_attempts',
                         'two_point_field_goals']
    num_games = stats['games_played']
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
        # Prepend all stats with 'away_' to signify the away team as such.
        away_columns = ['away_%s' % col for col in stats]
        stats.columns = away_columns
    else:
        # Prepend all stats with 'home_' to signify the home team as such.
        home_columns = ['home_%s' % col for col in stats]
        stats.columns = home_columns
    return stats


def create_prediction_data(match_data, inverted_conferences, winner, loser,
                           winner_prob, loser_prob, winner_points,
                           loser_points):
    tags = ['all']
    if match_data.top_25:
        tags += ['top-25']
    tags.append(inverted_conferences[match_data.home_nickname])
    tags.append(inverted_conferences[match_data.away_nickname])
    tags = list(set(tags))
    if winner == match_data.home_nickname:
        winner_name = match_data.home
        loser_name = match_data.away
    else:
        winner_name = match_data.away
        loser_name = match_data.home
    prediction = {
        'latest': True,
        'homeName': match_data.home,
        'homeAbbreviation': match_data.home_nickname,
        'homeMascot': MASCOTS[match_data.home_nickname],
        'awayName': match_data.away,
        'awayAbbreviation': match_data.away_nickname,
        'awayMascot': MASCOTS[match_data.away_nickname],
        'time': match_data.game_time,
        'predictedWinner': winner_name,
        'predictedWinnerAbbreviation': winner,
        'predictedWinnerMascot': MASCOTS[winner],
        'predictedLoser': loser_name,
        'predictedLoserAbbreviation': loser,
        'predictedLoserMascot': MASCOTS[loser],
        'winnerPoints': winner_points,
        'winnerProbability': winner_prob,
        'loserPoints': loser_points,
        'loserProbability': loser_prob,
        'tags': tags
    }
    return prediction


def create_variance(stats, stdev_dict):
    local_stats = {}

    for stat in stats:
        if stat.startswith('opp_'):
            continue
        min_val = -1 * float(stdev_dict[stat])
        max_val = abs(min_val)
        variance = random.uniform(min_val, max_val)
        new_value = float(stats[stat]) + variance
        local_stats[stat] = new_value
    return pd.DataFrame([local_stats])


def get_stats(stats_filename, stdev_dict, away=False):
    stats = read_team_stats_file(stats_filename)
    for field in FIELDS_TO_DROP:
        stats.drop(field, 1, inplace=True)
    if 'defensive_rating' not in stats and \
       'offensive_rating' in stats and \
       'net_rating' in stats:
        stats['defensive_rating'] = stats['offensive_rating'] - \
            stats['net_rating']
    if stdev_dict:
        stats = create_variance(stats, stdev_dict)
        stats = extract_stats_components(stats, away)
    else:
        # Get all of the stats that don't start with 'opp', AKA all of the
        # stats that are directly related to the indicated team.
        filtered_columns = [col for col in stats if not \
                            str(col).startswith('opp_')]
        stats = stats[filtered_columns]
        stats = convert_team_totals_to_averages(stats)
    return stats


def get_match_stats(game, stdev_dict):
    # No stats are saved for non-DI schools, so ignore predictions for matchups
    # that include non-DI schools.
    if game['non_di']:
        return None
    away_stats = get_stats('team-stats/%s' % game['away_abbr'], stdev_dict,
                           away=True)
    home_stats = get_stats('team-stats/%s' % game['home_abbr'], stdev_dict,
                           away=False)
    match_stats = pd.concat([away_stats, home_stats], axis=1)
    return match_stats


def get_winner(probability, home, away):
    winner = max(probability, key=probability.get)
    loser = min(probability, key=probability.get)
    if winner == loser:
        # Default to home team winning in case of tie
        if len(probability) != 1:
            winner = str(home)
            loser = str(away)
        # One team is projected to win every simulation
        else:
            if winner == home:
                loser = away
            else:
                loser = home
    return winner, loser


def pad_probability(probability):
    if probability > 0.99:
        return 0.99
    return probability


def get_probability(num_wins, winner, loser):
    winner_prob = pad_probability(float(num_wins[winner]) / float(NUM_SIMS))
    try:
        loser_prob = pad_probability(float(num_wins[loser]) / float(NUM_SIMS))
    except:
        loser_prob = 0.01
    return winner_prob, loser_prob


def get_points(points, winner, loser):
    winner_points = float(points[winner]) / float(NUM_SIMS)
    loser_points = float(points[loser]) / float(NUM_SIMS)
    return winner_points, loser_points


def make_predictions(prediction_stats, games_list, match_info, predictor):
    prediction_list = []
    conferences = Conferences().team_conference

    prediction_data = pd.concat(prediction_stats)
    prediction_data = differential_vector(prediction_data)
    prediction_data['points_difference'] = prediction_data['home_points'] - \
        prediction_data['away_points']
    prediction_data.rename(columns=FIELDS_TO_RENAME, inplace=True)
    prediction_data = predictor.simplify(prediction_data)
    predictions = predictor.predict(prediction_data, int)
    for sim in range(len(games_list) / NUM_SIMS):
        total_points = {}
        num_wins = {}
        for i in range(NUM_SIMS):
            x = sim * NUM_SIMS + i
            winner_idx = list(predictions[x]).index(max(predictions[x]))
            loser_idx = list(predictions[x]).index(min(predictions[x]))
            # In the case of a tie, give precedence to the home team.
            if winner_idx == loser_idx:
                winner_idx = 0
                winner = games_list[x].home.abbreviation
                loser_idx = 1
                loser = games_list[x].away.abbreviation
            elif winner_idx == 0:
                winner = games_list[x].home.abbreviation
                loser = games_list[x].away.abbreviation
            else:
                winner = games_list[x].away.abbreviation
                loser = games_list[x].home.abbreviation
            home = games_list[x].home.abbreviation
            away = games_list[x].away.abbreviation
            winner_points = predictions[x][winner_idx]
            loser_points = predictions[x][loser_idx]
            try:
                total_points[winner] += winner_points
            except KeyError:
                total_points[winner] = winner_points
            try:
                total_points[loser] += loser_points
            except KeyError:
                total_points[loser] = loser_points
            try:
                num_wins[winner] += 1
            except KeyError:
                num_wins[winner] = 1
        winner, loser = get_winner(num_wins, home, away)
        winner_prob, loser_prob = get_probability(num_wins, winner, loser)
        winner_points, loser_points = get_points(total_points, winner, loser)
        display_prediction(games_list[sim*NUM_SIMS].title, winner)
        p = create_prediction_data(match_info[sim*NUM_SIMS], conferences,
                                   winner, loser, winner_prob, loser_prob,
                                   winner_points, loser_points)
        prediction_list.append(p)
    return prediction_list


def find_stdev_for_every_stat(teams):
    stats_list = []
    stdev_dict = {}

    for team in teams:
        filename = 'team-stats/%s' % team.abbreviation.lower()
        stats_list.append(get_stats(filename, None))
    stats_dataframe = pd.concat(stats_list)
    for col in stats_dataframe:
        if col in FIELDS_TO_DROP:
            continue
        stdev_dict[col] = stats_dataframe[col].std()
    return stdev_dict


def parse_boxscores(predictor, teams, skip_save_to_mongodb):
    games_list = []
    match_info = []
    prediction_stats = []

    stdev_dict = find_stdev_for_every_stat(teams)
    today = datetime.today()
    today_string = '%s-%s-%s' % (today.month, today.day, today.year)
    for game in Boxscores(today).games[today_string]:
        # Skip the games that are not between two DI teams since stats are not
        # saved for those teams.
        if game['non_di']:
            continue
        for sim in range(NUM_SIMS):
            home = Team(game['home_name'], game['home_abbr'])
            away = Team(game['away_name'], game['away_abbr'])
            title = '%s at %s' % (away.name, home.name)
            game_info = GameInfo(home, away, title)
            games_list.append(game_info)
            match_stats = get_match_stats(game, stdev_dict)
            prediction_stats.append(match_stats)
            home_name = game['home_name']
            away_name = game['away_name']
            if game['home_rank']:
                home_name = '(%s) %s' % (game['home_rank'], home_name)
            if game['away_rank']:
                away_name = '(%s) %s' % (game['away_rank'], away_name)
            g = MatchInfo(away_name, home_name, game['away_abbr'],
                          game['home_abbr'], game['top_25'], None, match_stats)
            match_info.append(g)
    predictions = make_predictions(prediction_stats, games_list, match_info,
                                   predictor)
    save_predictions(predictions, skip_save_to_mongodb)


def arguments():
    parser = argparse.ArgumentParser()
    parser.add_argument('--dataset', help='Specify which dataset to use. For '
    'testing purposes, use the "sample-data" directory. For production '
    'deployments, use "matches" with current data that was pulled.',
    default='matches')
    parser.add_argument('--skip-save-to-mongodb', help='Optionally skip saving'
    ' results to a MongoDB database.', action='store_true')
    return parser.parse_args()


def main():
    teams = []
    args = arguments()
    predictor = Predictor(args.dataset)
    for team in Teams():
        teams.append(Team(team.name, team.abbreviation))
    parse_boxscores(predictor, teams, args.skip_save_to_mongodb)


if __name__ == "__main__":
    main()
