import difflib
import numpy
import pandas as pd
import random
import re
import requests
from pymongo import MongoClient


FIELDS_TO_COMBINE = {
    'home_assist_percentage': 'away_assist_percentage',
    'home_assists': 'away_assists',
    'home_block_percentage': 'away_block_percentage',
    'home_blocks': 'away_blocks',
    'home_defensive_rating': 'away_defensive_rating',
    'home_defensive_rebound_percentage': 'away_defensive_rebound_percentage',
    'home_defensive_rebounds': 'away_defensive_rebounds',
    'home_effective_field_goal_percentage': 'away_effective_field_goal_percentage',
    'home_field_goal_attempts': 'away_field_goal_attempts',
    'home_field_goal_percentage': 'away_field_goal_percentage',
    'home_field_goals': 'away_field_goals',
    'home_free_throw_attempt_rate': 'away_free_throw_attempt_rate',
    'home_free_throw_attempts': 'away_free_throw_attempts',
    'home_free_throw_percentage': 'away_free_throw_percentage',
    'home_free_throws': 'away_free_throws',
    'home_losses': 'away_losses',
    'home_minutes_played': 'away_minutes_played',
    'home_offensive_rating': 'away_offensive_rating',
    'home_offensive_rebound_percentage': 'away_offensive_rebound_percentage',
    'home_offensive_rebounds': 'away_offensive_rebounds',
    'home_personal_fouls': 'away_personal_fouls',
    'home_simple_rating_system': 'away_simple_rating_system',
    'home_steal_percentage': 'away_steal_percentage',
    'home_steals': 'away_steals',
    'home_strength_of_schedule': 'away_strength_of_schedule',
    'home_three_point_attempt_rate': 'away_three_point_attempt_rate',
    'home_three_point_field_goal_attempts': 'away_three_point_field_goal_attempts',
    'home_three_point_field_goal_percentage': 'away_three_point_field_goal_percentage',
    'home_three_point_field_goals': 'away_three_point_field_goals',
    'home_total_rebound_percentage': 'away_total_rebound_percentage',
    'home_total_rebounds': 'away_total_rebounds',
    'home_true_shooting_percentage': 'away_true_shooting_percentage',
    'home_turnover_percentage': 'away_turnover_percentage',
    'home_turnovers': 'away_turnovers',
    'home_two_point_field_goal_attempts': 'away_two_point_field_goal_attempts',
    'home_two_point_field_goal_percentage': 'away_two_point_field_goal_percentage',
    'home_two_point_field_goals': 'away_two_point_field_goals',
    'home_win_percentage': 'away_win_percentage',
    'home_wins': 'away_wins',
    'pace': 'pace',
}
FIELDS_TO_DROP = ['abbreviation', 'conference', 'name']


class MatchInfo:
    def __init__(self, away, home, away_name, home_name, away_abbreviation,
                 home_abbreviation, top_25, game_time):
        self.away = away
        self.away_abbreviation = away_abbreviation
        self.away_name = away_name
        self.game_time = game_time
        self.home = home
        self.home_abbreviation = home_abbreviation
        self.home_name = home_name
        self.top_25 = top_25


def read_team_stats_file(team_filename):
    team_filename = re.sub('\(\d+\) +', '', team_filename)
    return pd.read_pickle('%s.plk' % team_filename)


def filter_stats(match_stats):
    fields_to_drop = ['abbreviation', 'date', 'location', 'name', 'pace',
                      'winning_abbr', 'winning_name', 'losing_abbr',
                      'losing_name', 'winner']
    for field in fields_to_drop:
        try:
            match_stats.drop(field, 1, inplace=True)
        except KeyError:
            continue
    match_stats['away_ranking'] = match_stats['away_ranking'] \
        .notnull().astype('int')
    match_stats['home_ranking'] = match_stats['home_ranking'] \
        .notnull().astype('int')
    return match_stats


def differential_vector(stats):
    for home_feature, away_feature in FIELDS_TO_COMBINE.items():
        try:
            feature = home_feature.replace('home_', '')
            stats[feature] = stats[home_feature] - stats[away_feature]
            stats.drop(away_feature, 1, inplace=True)
            stats.drop(home_feature, 1, inplace=True)
        except KeyError:
            continue
    return stats


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


def find_stdev_for_every_stat(teams, rankings):
    stats_dict = {}
    stdev_dict = {}
    combined_stats = pd.DataFrame()

    for team in teams:
        abbr = team.abbreviation.lower()
        stats = update_stats(team.dataframe, abbr, rankings)
        home_stats = extract_stats_components(stats)
        away_stats = extract_stats_components(stats, away=True)
        home_stats, away_stats = drop_stats(home_stats, away_stats)
        stats_dict[abbr] = home_stats
        stats_dict['%s_away' % abbr] = away_stats
        combined_stats = combined_stats.append(home_stats)
        combined_stats = combined_stats.append(away_stats)
    for col in combined_stats.columns.values:
        stdev_dict[col] = combined_stats[col].std()
    return stats_dict, stdev_dict


def drop_stats(home_stats, away_stats):
    for field in FIELDS_TO_DROP:
        home_stats.drop('home_%s' % field, 1, inplace=True)
        away_stats.drop('away_%s' % field, 1, inplace=True)
    return home_stats, away_stats


def update_stats(stats, abbreviation, rankings):
    defensive_rebound_percentage = 100.0 * stats['defensive_rebounds'] /\
        (stats['defensive_rebounds'] + stats['opp_offensive_rebounds'])
    stats['defensive_rebound_percentage'] = defensive_rebound_percentage
    if 'defensive_rating' not in stats and \
       'offensive_rating' in stats and \
       'net_rating' in stats:
        stats['defensive_rating'] = stats['offensive_rating'] - \
            stats['net_rating']
    if abbreviation.lower() in rankings.keys():
        stats['ranking'] = rankings[abbreviation.lower()]
    else:
        stats['ranking'] = 0
    return stats


def create_variance(stats, stdev_dict, away, location_specified=False):
    local_stats = {}

    for stat in stats:
        if stat.startswith('opp_'):
            continue
        if location_specified:
            min_val = -1 * float(stdev_dict[stat])
        elif away:
            min_val = -1 * float(stdev_dict['away_%s' % stat])
        else:
            min_val = -1 * float(stdev_dict['home_%s' % stat])
        max_val = abs(min_val)
        variance = random.uniform(min_val, max_val)
        new_value = float(stats[stat]) + variance
        local_stats[stat] = new_value
    return pd.DataFrame([local_stats])


def create_predictions(prediction_stats, predictor):
    prediction_data = pd.concat(prediction_stats)
    matches_vector = differential_vector(prediction_data)
    matches_vector['points_difference'] = matches_vector['home_points'] - \
        matches_vector['away_points']
    matches_vector = predictor.simplify(matches_vector)
    return predictor.predict(matches_vector, int)


def add_winner(num_wins, home, away, home_score, away_score):
    if away_score > home_score:
        num_wins[away] = num_wins.get(away, 0) + 1
    # In the case of a tie, give precedence to the home team.
    else:
        num_wins[home] = num_wins.get(home, 0) + 1
    return num_wins


def add_points(total_points, home, away, home_score, away_score):
    total_points[home] = total_points.get(home, 0) + home_score
    total_points[away] = total_points.get(away, 0) + away_score
    return total_points


def accumulate_points_and_wins(total_points, num_wins, prediction, game):
    home, away = game
    home_score, away_score = prediction
    total_points = add_points(total_points, home, away, home_score, away_score)
    num_wins = add_winner(num_wins, home, away, home_score, away_score)
    return total_points, num_wins


def update_total_wins(standings, total_wins):
    for team, points in standings.items():
        total_wins[team] = total_wins.get(team, 0) + points
    return total_wins


def update_standings(standings, standings_dict):
    sorted_standings = [(v,k) for k,v in standings.iteritems()]
    sorted_standings.sort(reverse=True)
    for position, standings in enumerate(sorted_standings):
        _, team = standings
        standings_dict[team]['points'][position] += 1
    return standings_dict


def determine_conference_standings(num_wins, conference_wins):
    standings_dict = {}

    for team in conference_wins:
        standings_dict[team] = num_wins.get(team, 0) + \
            conference_wins.get(team, 0)
    return standings_dict


def print_probabilities_ordered(probabilities):
    sorted_ranks = [(v,k) for k,v in probabilities.iteritems()]
    sorted_ranks.sort(reverse=True)
    for probability, team in sorted_ranks:
        print('%s: %s%%' % (team, probability * 100.0))


def print_simulation_results(standings_dict, num_sims):
    for i in range(len(standings_dict)):
        print('=' * 80)
        print('  Place: %s' % (i+1))
        print('=' * 80)
        probabilities = {}
        for team, standings in standings_dict.items():
            probability = float(standings['points'][i]) / float(num_sims)
            probabilities[team] = probability
        print_probabilities_ordered(probabilities)


def determine_outcomes(predictions, games_list, standings_dict=None,
                       conference_wins=None, num_sims=None):
    total_points = {}
    total_wins = {}
    num_wins = {}

    for i in range(len(games_list)):
        total_points, num_wins = accumulate_points_and_wins(total_points,
                                                            num_wins,
                                                            predictions[i],
                                                            games_list[i])
        if not standings_dict:
            continue
        if (i + 1) % (len(games_list) / num_sims) == 0:
            standings = determine_conference_standings(num_wins,
                                                       conference_wins)
            standings_dict = update_standings(standings, standings_dict)
            total_wins = update_total_wins(standings, total_wins)
            num_wins = {}
        if (i + 1) == len(games_list):
            print_simulation_results(standings_dict, num_sims)
            return standings_dict, total_wins
    return total_points, num_wins


def aggregate_match_stats(stats_dict, stdev_dict, games, num_sims):
    match_stats = []
    new_games = []

    for iteration in range(num_sims):
        for game in games:
            away = game.away_abbreviation
            home = game.home_abbreviation
            home_stats = create_variance(stats_dict[home],
                                         stdev_dict, False, True)
            away_stats = create_variance(stats_dict['%s_away' % away],
                                         stdev_dict, True, True)
            match_stats.append(pd.concat([away_stats, home_stats], axis=1))
            new_games.append([home, away])
    return match_stats, new_games


def create_team_name(game):
    home = game['home_name']
    away = game['away_name']
    if game['home_rank']:
        home = '(%s) ' % game['home_rank'] + home
    if game['away_rank']:
        away = '(%s) ' % game['away_rank'] + away
    return home, away


def populate_game_info(teams, game):
    home_name, away_name = create_team_name(game)
    away = teams(game['away_abbr'])
    home = teams(game['home_abbr'])
    match = MatchInfo(away, home, away_name, home_name, game['away_abbr'],
                      game['home_abbr'], game['top_25'], None)
    return match
