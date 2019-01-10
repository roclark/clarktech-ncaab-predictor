import argparse
import numpy
import pandas as pd
import re
from common import (differential_vector,
                    extract_stats_components,
                    read_team_stats_file)
from datetime import datetime
from math import ceil, sqrt
from predictor import Predictor
from pymongo import MongoClient
from sportsreference.ncaab.teams import Teams


def get_totals(games_list, predictions, team_mov):
    for i in range(0, len(games_list)):
        winner_index = numpy.argmax(predictions[i])
        loser_index = abs(winner_index - 1)
        winner = games_list[i][winner_index]
        loser = games_list[i][loser_index]
        margin_of_victory = max(predictions[i]) - min(predictions[i])
        team_mov[winner] += margin_of_victory
        team_mov[loser] -= margin_of_victory
    return team_mov


def teams_list(conference):
    if not conference:
        return Teams()
    else:
        teams = []
        for abbreviation, name in conference['teams'].items():
            teams.append(abbreviation)
        return teams


def split_datasets(dataset):
    set_size = int(ceil(sqrt(len(dataset)))) * 2
    for i in xrange(0, len(dataset), set_size):
        yield dataset[i:i+set_size]


def initialize_team_mov(teams):
    team_mov = {}

    for team in teams:
        team_mov[team.abbreviation.lower()] = 0
    return team_mov


def update_rankings(rankings, team_mov, dataset):
    sorted_ranks = [(v,k) for k,v in team_mov.iteritems()]
    sorted_ranks.sort(reverse=True)
    for value, team in sorted_ranks:
        if team not in rankings and team in dataset:
            rankings.append(team)
    return rankings


def predict_all_matches(predictor, stats_dict, simple_rating_system, teams):
    team_mov = initialize_team_mov(teams)
    rankings = []

    for dataset in split_datasets(simple_rating_system):
        games_list = []
        prediction_stats = pd.DataFrame()
        match_stats = []
        for home_team in dataset:
            team_mov[home_team] = 0
            print(home_team)
            for away_team in dataset:
                if home_team == away_team:
                    continue
                home_stats = stats_dict[home_team].reset_index(drop=True)
                away_stats = stats_dict['%s_away' % away_team] \
                    .reset_index(drop=True)
                match_stats.append(pd.concat([away_stats, home_stats], axis=1))
                games_list.append([home_team, away_team])
        try:
            prediction_stats = pd.concat(match_stats)
        # Occurs when only one team is left in a pool. For example, if the teams
        # are divided into approximately 10 groups, there will be a single team
        # leftover which will automatically be the lowest-tier team, so add them
        # to the end of the rankings.
        except ValueError:
            rankings.append(home_team)
            continue
        match_vector = differential_vector(prediction_stats)
        match_vector['points_difference'] = match_vector['home_points'] - \
            match_vector['away_points']
        match_stats_simplified = predictor.simplify(match_vector)
        predictions = predictor.predict(match_stats_simplified, int)
        team_mov = get_totals(games_list, predictions, team_mov)
        rankings = update_rankings(rankings, team_mov, dataset)
    return rankings


def create_stats_dictionary(teams):
    stats_dict = {}
    simple_rating_system = {}

    for team in teams:
        abbreviation = team.abbreviation.lower()
        stats = read_team_stats_file('team-stats/%s' % abbreviation)
        if 'defensive_rating' not in stats and \
           'offensive_rating' in stats and \
           'net_rating' in stats:
            stats['defensive_rating'] = stats['offensive_rating'] - \
                stats['net_rating']
        home_stats = extract_stats_components(stats)
        simple_rating_system[abbreviation] = team.simple_rating_system
        away_stats = extract_stats_components(stats, away=True)
        stats_dict[abbreviation] = home_stats
        stats_dict['%s_away' % abbreviation] = away_stats
    return stats_dict, simple_rating_system


def sort_by_simple_rating_system(simple_rating_system):
    sorted_ranks = []
    for key, value in sorted(simple_rating_system.iteritems(),
                             key=lambda (k,v): (v,k),
                             reverse=True):
        sorted_ranks.append(key)
    return sorted_ranks


def print_rankings(rankings):
    i = 1

    for team in rankings:
        print '%s. %s' % (str(i).rjust(3), team)
        i += 1


def save_rankings(rankings, skip_mongo, teams_class):
    if skip_mongo:
        return
    overall_rankings = []
    client = MongoClient()
    db = client.clarktechsports
    db.power_rankings.update_many({}, {'$set': {'latest': False}})
    for rank in rankings:
        team_details = {
            rank: {
                'wins': teams_class(rank).wins,
                'losses': teams_class(rank).losses,
                'conference': teams_class(rank).conference
            }
        }
        overall_rankings.append(team_details)
    db.power_rankings.insert({'latest': True,
                              'rankings': overall_rankings})


def parse_arguments():
    parser = argparse.ArgumentParser()
    parser.add_argument('--conference', help='Optionally specify a particular '
    'conference to analyze the power rankings for. For example, specify "Big '
    'Ten Conference" to get power rankings only comprising the Big Ten teams.',
    default=None)
    parser.add_argument('--skip-save-to-mongodb', help='Optionally skip saving'
    ' results to a MongoDB database.', action='store_true')
    return parser.parse_args()


def main():
    args = parse_arguments()
    predictor = Predictor()
    teams_class = teams_list(args.conference)
    teams = [team for team in teams_class]
    stats_dict, simple_rating_system = create_stats_dictionary(teams)
    sorted_rating_system = sort_by_simple_rating_system(simple_rating_system)
    rankings = predict_all_matches(predictor, stats_dict, sorted_rating_system,
                                   teams)
    print_rankings(rankings)
    save_rankings(rankings, args.skip_save_to_mongodb, teams_class)


if __name__ == "__main__":
    main()
