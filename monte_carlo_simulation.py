import argparse
import itertools
import numpy
import pandas as pd
import random
from common import (differential_vector,
                    extract_stats_components,
                    read_team_stats_file)
from datetime import datetime
from predictor import Predictor
from sportsreference.ncaab.teams import Teams
from sportsreference.ncaab.schedule import Schedule


FIELDS_TO_DROP = ['abbreviation', 'conference', 'name']
NUM_SIMS = 100


def get_winner(game, prediction):
    return game[list(prediction).index(max(list(prediction)))]


def get_totals(games_list, predictions, team_wins, conference_wins):
    for i in range(0, len(games_list)):
        winner = get_winner(games_list[i], predictions[i])
        team_wins[winner] += 1
    for team, wins in conference_wins.items():
        team_wins[team] += wins
    return team_wins


def teams_list(conference, with_names=False):
    teams = []
    names = {}
    if not conference:
        for team in Teams():
            teams.append({team.abbreviation: team})
            names[team.abbreviation] = team.name
    else:
        for abbreviation, name in conference['teams'].items():
            teams.append(abbreviation)
            names[abbreviation] = name
    if with_names:
        return teams, names
    return teams


def predict_all_matches(predictor, stats_dict, conference, schedule,
                        conference_wins):
    games_list = []
    prediction_stats = pd.DataFrame()
    match_stats = []
    team_wins = {}

    for team in teams_list(conference):
        team_wins[team] = 0

    for matchup in schedule:
        home, away = matchup
        home_stats = stats_dict[home]
        away_stats = stats_dict['%s_away' % away]
        match_stats.append(pd.concat([away_stats, home_stats], axis=1))
    prediction_stats = pd.concat(match_stats)
    match_vector = differential_vector(prediction_stats)
    match_vector['points_difference'] = match_vector['home_points'] - \
        match_vector['away_points']
    match_stats_simplified = predictor.simplify(match_vector)
    predictions = predictor.predict(match_stats_simplified, int)
    team_wins = get_totals(schedule, predictions, team_wins, conference_wins)
    return team_wins


def create_variance(stats_dict, stdev_dict):
    local_stats_dict = {}

    for team, stats in stats_dict.items():
        local_stats = {}
        for stat in stats:
            min_val = -1 * float(stdev_dict[stat])
            max_val = abs(min_val)
            variance = random.uniform(min_val, max_val)
            new_value = float(stats[stat]) + variance
            local_stats[stat] = new_value
        local_stats_dict[team] = pd.DataFrame([local_stats])
    return local_stats_dict


def initialize_standings_dict(conference):
    standings_dict = {}
    overall_standings_dict = {}
    teams, names = teams_list(conference, with_names=True)

    for team in teams:
        overall_standings_dict[team] = {
            'name': names[team],
            'points': [0] * len(teams)
        }
    return overall_standings_dict


def print_probabilities_ordered(probabilities):
    sorted_ranks = [(v,k) for k,v in probabilities.iteritems()]
    sorted_ranks.sort(reverse=True)
    for probability, team in sorted_ranks:
        print '%s: %s%%' % (team, probability * 100.0)


def print_simulation_results(standings_dict, num_sims):
    for i in range(len(standings_dict)):
        print '=' * 80
        print '  Place: %s' % (i+1)
        print '=' * 80
        probabilities = {}
        for team, standings in standings_dict.items():
            probability = float(standings['points'][i]) / float(num_sims)
            probabilities[team] = probability
        print_probabilities_ordered(probabilities)


def add_points_total(points_dict, team_wins):
    for team, wins in team_wins.items():
        if team in points_dict:
            points_dict[team] += wins
        else:
            points_dict[team] = wins
    return points_dict


def predict_all_simulations(predictor, stats_dict, stdev_dict, conference,
                            num_sims, schedule, conference_wins):
    standings_dict = initialize_standings_dict(conference)
    points_dict = {}

    for iteration in range(num_sims):
        local_stats_dict = create_variance(stats_dict, stdev_dict)
        team_wins = predict_all_matches(predictor, local_stats_dict, conference,
                                        schedule, conference_wins)
        points_dict = add_points_total(points_dict, team_wins)
        rankings = print_rankings(team_wins)
        for rank in range(len(rankings)):
            for team in rankings[rank]:
                standings_dict[team]['points'][rank] += 1
    print_simulation_results(standings_dict, num_sims)
    return standings_dict, points_dict


def get_conference_wins(team):
    stats = read_team_stats_file('team-stats/%s' % team)
    return int(stats['conference_wins'])


def get_remaining_schedule(conference):
    # remaining_schedule is a list of lists with the inner list being
    # the home first, followed by the away team (ie. [home, away])
    remaining_schedule = []
    current_records = {}
    conference_name_short = conference['name'].replace(' Conference', '')

    for team in teams_list(conference):
        schedule = Schedule(team)
        conference_wins = get_conference_wins(team)
        current_records[team] = conference_wins
        for game in schedule:
            # Find all conference matchups that the team hasn't played yet.
            if game.opponent_abbr in teams_list(conference) and \
               not game.points_for:
                if game.location == 'AWAY':
                    remaining_schedule.append([game.opponent_abbr, team])
                else:
                    remaining_schedule.append([team, game.opponent_abbr])
    remaining_schedule.sort()
    # Return a list of non-duplicate matches
    schedule = list(s for s, _ in itertools.groupby(remaining_schedule))
    return schedule, current_records


def drop_stats(home_stats, away_stats):
    for field in FIELDS_TO_DROP:
        home_stats.drop('home_%s' % field, 1, inplace=True)
        away_stats.drop('away_%s' % field, 1, inplace=True)
    return home_stats, away_stats


def update_stats(stats):
    if 'defensive_rating' not in stats and \
       'offensive_rating' in stats and \
       'net_rating' in stats:
        stats['defensive_rating'] = stats['offensive_rating'] - \
            stats['net_rating']
    return stats


def create_stats_dictionary(conference):
    stats_dict = {}
    stdev_dict = {}
    combined_stats = pd.DataFrame()

    for team in teams_list(conference):
        stats = read_team_stats_file('team-stats/%s' % team)
        stats = update_stats(stats)
        home_stats = extract_stats_components(stats)
        away_stats = extract_stats_components(stats, away=True)
        home_stats, away_stats = drop_stats(home_stats, away_stats)
        stats_dict[team] = home_stats
        stats_dict['%s_away' % team] = away_stats
        combined_stats = combined_stats.append(home_stats)
        combined_stats = combined_stats.append(away_stats)
    for col in combined_stats.columns.values:
        stdev_dict[col] = combined_stats[col].std()
    return stats_dict, stdev_dict


def print_rankings(team_wins):
    rankings = [[] for i in range(len(team_wins))]
    sorted_ranks = [(v,k) for k,v in team_wins.iteritems()]
    sorted_ranks.sort(reverse=True)
    rank = 1
    previous_wins = None
    for i in range(len(sorted_ranks)):
        wins, team = sorted_ranks[i]
        if previous_wins != wins:
            rank = i + 1
        print '%s. %s: %s (rank %s)' % (str(i+1).rjust(3), team, wins, rank)
        previous_wins = wins
        rankings[rank-1].append(team)
    return rankings


def parse_arguments():
    parser = argparse.ArgumentParser()
    parser.add_argument('--conference', help='Optionally specify a particular '
    'conference to analyze the power rankings for. For example, specify "Big '
    'Ten Conference" to get power rankings only comprising the Big Ten teams.',
    default=None)
    parser.add_argument('--num-sims', '-n', help='Optionally specify the '
    'number of simulations to run. Default value is %s simulations.' % NUM_SIMS,
    default=NUM_SIMS)
    parser.add_argument('--dataset', help='Specify which dataset to use. For '
    'testing purposes, use the "sample-data" directory. For production '
    'deployments, use "matches" with current data that was pulled.',
    default='matches')
    return parser.parse_args()


def start_simulations(predictor, conference, num_sims=NUM_SIMS):
    stats_dict, stdev_dict = create_stats_dictionary(conference)
    schedule, conference_wins = get_remaining_schedule(conference)
    team_wins, points_dict = predict_all_simulations(predictor, stats_dict,
                                                     stdev_dict, conference,
                                                     num_sims, schedule,
                                                     conference_wins)
    return team_wins, points_dict


def main():
    args = parse_arguments()
    predictor = Predictor(args.dataset)
    start_simulations(predictor, args.conference, int(args.num_sims))


if __name__ == "__main__":
    main()
