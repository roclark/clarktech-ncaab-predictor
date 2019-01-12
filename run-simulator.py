import itertools
import json
import pandas as pd
from argparse import ArgumentParser
from common import (accumulate_points_and_wins,
                    aggregate_match_stats,
                    create_predictions,
                    create_variance,
                    determine_outcomes,
                    find_stdev_for_every_stat,
                    populate_game_info)
from conference_tournaments import BRACKETS
from csv import reader
from datetime import datetime
from mascots import MASCOTS
from math import ceil, sqrt
from os import path, makedirs
from predictor import Predictor
from save_json import save_predictions_json, save_simulation
from sportsreference.constants import AWAY, REGULAR_SEASON
from sportsreference.ncaab.boxscore import Boxscores
from sportsreference.ncaab.conferences import Conferences
from sportsreference.ncaab.rankings import Rankings
from sportsreference.ncaab.teams import Teams


CONFERENCE_TOURNAMENT = 'conference-tourney-simulator'
DAILY_SIMULATION = 'daily-simulation'
MATCHUP = 'matchup'
MONTE_CARLO_SIMULATION = 'monte-carlo-simulation'
POWER_RANKINGS = 'power-rankings'
TOURNAMENT_SIMULATOR = 'tournament-simulator'

NUM_SIMS = 100


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


def save_to_mongodb(simulation, algorithm):
    client = MongoClient()
    db = client.clarktechsports
    # Clear all of the existing simulations and add simulation for the current
    # day
    db.conference_predictions.update_many({}, {'$set': {'latest': False}})
    if algorithm == DAILY_SIMULATION:
        db.predictions.insert_many(simulation)
    elif algorithm == MONTE_CARLO_SIMULATION:
        post = simulation['simulation']['conference']
        db.conference_predictions.insert_many(post)


def save_predictions(predictions, skip_save_to_mongodb):
    today = datetime.now()
    if not path.exists('predictions'):
        makedirs('predictions')
    filename = 'predictions/%s-%s-%s.json' % (today.month,
                                              today.day,
                                              today.year)
    save_predictions_json(predictions, filename)
    if not skip_save_to_mongodb:
        save_to_mongodb(predictions, DAILY_SIMULATION)


def display_predictions(predictions):
    for prediction in predictions:
        print('%s at %s  =>  %s' % (prediction['awayName'],
                                    prediction['homeName'],
                                    prediction['predictedWinner']))


def create_prediction_data(match_data, winner, loser, winner_prob, loser_prob,
                           winner_points, loser_points):
    tags = ['all']
    if match_data.top_25:
        tags += ['top-25']
    tags.append(match_data.home.conference)
    tags.append(match_data.away.conference)
    tags = list(set(tags))
    if winner == match_data.home_abbreviation:
        winner_name = match_data.home_name
        loser_name = match_data.away_name
    else:
        winner_name = match_data.away_name
        loser_name = match_data.home_name
    prediction = {
        'latest': True,
        'homeName': match_data.home_name,
        'homeAbbreviation': match_data.home_abbreviation,
        'homeMascot': MASCOTS[match_data.home_abbreviation],
        'awayName': match_data.away_name,
        'awayAbbreviation': match_data.away_abbreviation,
        'awayMascot': MASCOTS[match_data.away_abbreviation],
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


def get_winner(num_wins, home, away):
    if home not in num_wins:
        winner = away
        loser = home
    elif away not in num_wins:
        winner = home
        loser = away
    else:
        probability = {key:num_wins[key] for key in (home, away)}
        winner = max(probability, key=probability.get)
        loser = min(probability, key=probability.get)
        # Default to home team winning in case of tie
        if winner == loser:
            winner = home
            loser = away
    return winner, loser


def pad_probability(probability):
    if probability > 0.99:
        return 0.99
    return probability


def get_probability(num_wins, winner, loser, num_sims):
    winner_prob = pad_probability(float(num_wins[winner]) / float(num_sims))
    try:
        loser_prob = pad_probability(float(num_wins[loser]) / float(num_sims))
    except:
        loser_prob = 0.01
    return winner_prob, loser_prob


def get_points(points, winner, loser, num_sims):
    winner_points = float(points[winner]) / float(num_sims)
    loser_points = float(points[loser]) / float(num_sims)
    return winner_points, loser_points


def determine_overall_results(matchups, total_points, num_wins, num_sims):
    prediction_list = []

    for matchup in matchups:
        winner, loser = get_winner(num_wins,
                                   matchup.home_abbreviation,
                                   matchup.away_abbreviation)
        winner_probability, loser_probability = get_probability(num_wins,
                                                                winner,
                                                                loser,
                                                                num_sims)
        winner_points, loser_points = get_points(total_points, winner, loser,
                                                 num_sims)
        p = create_prediction_data(matchup, winner, loser, winner_probability,
                                   loser_probability, winner_points,
                                   loser_points)
        prediction_list.append(p)
    return prediction_list


def find_todays_games(teams):
    games_list = []
    today = datetime.today()
    today_string = '%s-%s-%s' % (today.month, today.day, today.year)

    for game in Boxscores(today).games[today_string]:
        # Skip the games that are not between two DI teams since stats are not
        # saved for those teams.
        if game['non_di']:
            continue
        games_list.append(populate_game_info(teams, game))
    return games_list


def teams_list(conference, teams):
    teams_dict = {}

    for abbreviation in conference:
        teams_dict[abbreviation] = teams(abbreviation)
    return teams_dict


def initialize_standings_dict(teams):
    standings_dict = {}

    for team in teams:
        standings_dict[team] = {
            'name': team,
            'points': [0] * len(teams)
        }
    return standings_dict


def get_remaining_schedule(conference_teams, teams, rankings):
    # remaining_schedule is a list of lists with the inner list being
    # the home first, followed by the away team (ie. [home, away])
    remaining_schedule = []
    current_records = {}

    for abbreviation, team in conference_teams.items():
        current_records[abbreviation] = team.conference_wins
        for game in team.schedule:
            # Find all conference matchups that the team hasn't played yet.
            if game.opponent_abbr in conference_teams and \
               not game.points_for and \
               game.type == REGULAR_SEASON:
                top_25 = rankings.get(team.abbreviation.lower(), None) or \
                         rankings.get(game.opponent_abbr.lower(), None)
                if game.location == AWAY:
                    game = {
                        'home_name': game.opponent_name,
                        'home_abbr': game.opponent_abbr.lower(),
                        'home_rank': game.opponent_rank,
                        'away_name': team.name,
                        'away_abbr': team.abbreviation.lower(),
                        'away_rank': rankings.get(team.abbreviation.lower(),
                                                  None),
                        'top_25': top_25
                    }
                else:
                    game = {
                        'home_name': team.name,
                        'home_abbr': team.abbreviation.lower(),
                        'home_rank': rankings.get(team.abbreviation.lower(),
                                                  None),
                        'away_name': game.opponent_name,
                        'away_abbr': game.opponent_abbr.lower(),
                        'away_rank': game.opponent_rank,
                        'top_25': top_25
                    }
                remaining_schedule.append(populate_game_info(teams, game))
    remaining_schedule.sort()
    # Return a list of non-duplicate matches
    schedule = list(s for s, _ in itertools.groupby(remaining_schedule))
    return schedule, current_records


def simulate_conference(predictor, details, rankings, teams, num_sims):
    conference_teams = teams_list(details['teams'].keys(), teams)
    standings_dict = initialize_standings_dict(conference_teams)
    stats_dict, stdev_dict = find_stdev_for_every_stat(teams, rankings)
    schedule, conference_wins = get_remaining_schedule(conference_teams, teams,
                                                       rankings)
    match_stats, games = aggregate_match_stats(stats_dict, stdev_dict,
                                               schedule, num_sims)
    predictions = create_predictions(match_stats, predictor)
    standings_dict, total_wins = determine_outcomes(predictions, games,
                                                    standings_dict,
                                                    conference_wins, num_sims)
    return standings_dict, total_wins


def power_ranking_matchups(matchups, teams, rankings):
    matches = []

    for match in matchups:
        home, away = match
        game = {
            'away_abbr': away,
            'away_name': teams(away).name,
            'away_rank': rankings.get(away, None),
            'home_abbr': home,
            'home_name': teams(home).name,
            'home_rank': rankings.get(home, None),
            'top_25': rankings.get(away, None) or rankings.get(home, None)
        }
        matches.append(populate_game_info(teams, game))
    return matches


def split_power_rankings_data(dataset):
    set_size = int(ceil(sqrt(len(dataset)))) * 2

    for i in xrange(0, len(dataset), set_size):
        subset = dataset[i:i+set_size]
        yield map(list, list(itertools.permutations(subset, 2)))


def sort_by_simple_rating_system(stats_dict):
    sorted_ranks = []
    simple_rating_system = {}

    for team, stats in stats_dict.items():
        if '_away' in team:
            continue
        simple_rating_system[team] = stats.iloc[0]['home_simple_rating_system']

    for key, value in sorted(simple_rating_system.iteritems(),
                             key=lambda (k,v): (v,k),
                             reverse=True):
        sorted_ranks.append(key)
    return sorted_ranks


def get_totals(matches, predictions, team_mov):
    for i in range(len(matches)):
        home_score, away_score = predictions[i]
        home_team = matches[i].home_abbreviation
        away_team = matches[i].away_abbreviation
        team_mov[home_team] = team_mov.get(home_team, 0) + home_score - \
            away_score
        team_mov[away_team] = team_mov.get(away_team, 0) + away_score - \
            home_score
    return team_mov


def print_rankings(rankings):
    i = 1

    for team in rankings:
        print('%s. %s' % (str(i).rjust(3), team))
        i += 1


def update_rankings(rankings, team_mov, dataset):
    sorted_ranks = [(v,k) for k,v in team_mov.iteritems()]
    sorted_ranks.sort(reverse=True)
    dataset = list(set([team for matchup in dataset for team in matchup]))
    for _, team in sorted_ranks:
        if team not in rankings and team in dataset:
            rankings.append(team)
    return rankings


def save_rankings(rankings, skip_mongo):
    if skip_mongo:
        return
    overall_rankings = []
    client = MongoClient()
    db = client.clarktechsports
    db.power_rankings.update_many({}, {'$set': {'latest': False}})
    db.power_rankings.insert({'latest': True, 'rankings': rankings})


def load_ncaa_tournament_csv(filename):
    tourney_dict = {}
    team_seeds = {}

    with open(filename, 'rb') as csvfile:
        tournament = reader(csvfile, delimiter=';')
        header = next(tournament)
        seeds = header[-1].split(',')
        for region, teams in tournament:
            tourney_dict[region] = teams
            team_seeds.update(dict(zip(teams.split(','), seeds)))
    return tourney_dict, team_seeds


def create_matches(matchups, teams, rankings):
    matches = []

    for matchup in matchups:
        home_abbr, away_abbr = matchup
        home = teams(home_abbr)
        away = teams(away_abbr)
        game = {
            'home_name': home.name,
            'home_abbr': home_abbr,
            'home_rank': rankings.get(home_abbr, None),
            'away_name': away.name,
            'away_abbr': away_abbr,
            'away_rank': rankings.get(away_abbr, None),
            'top_25': rankings.get(home_abbr, None) or \
                      rankings.get(away_abbr, None)
        }
        matches.append(populate_game_info(teams, game))
    return matches


def reduce_field(prediction_list, field):
    for prediction in prediction_list:
        field.remove(prediction['predictedLoserAbbreviation'])
    return field


def load_simulation():
    with open('simulations/simulation.json') as json_data:
        return json.load(json_data)


def get_teams_dict(simulation, conference):
    for conf in simulation['simulation']['conferences']:
        if conf['conferenceName'] == conference:
            return conf['teams']


def build_projected_points(teams_dict):
    conf_points = {}

    for team in teams_dict:
        abbreviation = str(team['abbreviation'])
        points = team['projectedWins']
        conf_points[abbreviation] = points
    return conf_points


def find_projected_seeds(simulation, conference):
    teams_dict = get_teams_dict(simulation, conference)
    conf_points = build_projected_points(teams_dict)
    return sorted(conf_points, key=conf_points.get, reverse=True)


def team_from_seed(seed, seeds):
    return seeds[seed - 1]


def include_teams(game, games_list, seeds):
    for team in ['top_team', 'bottom_team']:
        try:
            seed = int(game[team])
            game[team] = team_from_seed(seed, seeds)
        except ValueError:
            game[team] = games_list[game[team]]['winner']
    return game


def simulate_conference_tournament(predictor, seeds, bracket, teams, rankings,
                                   stats_dict, stdev_dict, num_sims):
    winner = None

    for game_name, game_data in sorted(bracket.iteritems()):
        game_data = include_teams(game_data, bracket, seeds)
        matchup = [[game_data['top_team'], game_data['bottom_team']]]
        match = create_matches(matchup, teams, rankings)
        match_stats, games = aggregate_match_stats(stats_dict, stdev_dict,
                                                   match, num_sims)
        predictions = create_predictions(match_stats, predictor)
        total_points, num_wins = determine_outcomes(predictions, games)
        prediction_list = determine_overall_results(match, total_points,
                                                    num_wins, num_sims)
        winner = prediction_list[0]['predictedWinnerAbbreviation']
        game_data['winner'] = winner
        display_predictions(prediction_list)
    # This winner is the last winner of the last game, AKA the champion
    return winner


def start_daily_simulations(predictor, teams, skip_save_to_mongodb, rankings,
                            num_sims):
    matchups = find_todays_games(teams)
    if len(matchups) == 0:
        print("Couldn't find games scheduled for today. Exiting...")
        return
    stats_dict, stdev_dict = find_stdev_for_every_stat(teams, rankings)
    match_stats, games = aggregate_match_stats(stats_dict, stdev_dict,
                                               matchups, num_sims)
    predictions = create_predictions(match_stats, predictor)
    total_points, num_wins = determine_outcomes(predictions, games)
    prediction_list = determine_overall_results(matchups, total_points,
                                                num_wins, num_sims)
    display_predictions(prediction_list)
    save_predictions(prediction_list, skip_save_to_mongodb)


def start_monte_carlo_simulations(predictor, rankings, teams,
                                  num_sims=NUM_SIMS,
                                  skip_save_to_mongodb=False):
    results_dict = {}
    points_dict = {}

    for abbreviation, details in Conferences().conferences.items():
        results, points = simulate_conference(predictor, details, rankings,
                                              teams, num_sims)
        results_dict[abbreviation] = {'results': results,
                                      'name': details['name']}
        points_dict[abbreviation] = {'points': points,
                                     'name': details['name']}
    simulation = save_simulation(num_sims, results_dict, points_dict,
                                 'simulations/simulation.json')
    if not skip_save_to_mongodb:
        save_to_mongodb(simulation, MONTE_CARLO_SIMULATION)


def start_matchup_simulation(predictor, teams, rankings, num_sims, home, away):
    matches = []

    game = {
        'away_abbr': away,
        'away_name': teams(away).name,
        'away_rank': rankings.get(away, None),
        'home_abbr': home,
        'home_name': teams(home).name,
        'home_rank': rankings.get(home, None),
        'top_25': rankings.get(away, None) or rankings.get(home, None)
    }
    game = populate_game_info(teams, game)
    matches = [game] * num_sims
    stats_dict, stdev_dict = find_stdev_for_every_stat(teams, rankings)
    match_stats, games = aggregate_match_stats(stats_dict, stdev_dict,
                                               matches, num_sims)
    predictions = create_predictions(match_stats, predictor)
    total_points, num_wins = determine_outcomes(predictions, games)
    prediction_list = determine_overall_results([game], total_points,
                                                num_wins, num_sims)
    display_predictions(prediction_list)


def start_power_rankings(predictor, teams, rankings, num_sims,
                         skip_save_to_mongodb):
    matches = []
    team_mov = {}
    power_rankings = []

    stats_dict, stdev_dict = find_stdev_for_every_stat(teams, rankings)
    simple_rating_system = sort_by_simple_rating_system(stats_dict)
    for subset in split_power_rankings_data(simple_rating_system):
        matches = power_ranking_matchups(subset, teams, rankings)
        match_stats, games = aggregate_match_stats(stats_dict, stdev_dict,
                                                   matches, num_sims)
        predictions = create_predictions(match_stats, predictor)
        team_mov = get_totals(matches, predictions, team_mov)
        power_rankings = update_rankings(power_rankings, team_mov, subset)
    print_rankings(power_rankings)
    save_rankings(power_rankings, skip_save_to_mongodb)


def start_conference_tournament_simulator(predictor, teams, rankings,
                                          num_sims):
    simulation = load_simulation()
    stats_dict, stdev_dict = find_stdev_for_every_stat(teams, rankings)
    for conference, bracket in BRACKETS.items():
        seeds = find_projected_seeds(simulation, conference)
        winner = simulate_conference_tournament(predictor, seeds, bracket,
                                                teams, rankings, stats_dict,
                                                stdev_dict, num_sims)
        print('=' * 80)
        print(' %s Champion: %s' % (conference, winner))
        print('=' * 80)


def start_ncaa_tournament_simulator(predictor, teams, rankings, num_sims,
                                    filename):
    rounds = ['Round of 64', 'Round of 32', 'Sweet 16', 'Elite 8', 'Final 4',
              'Championship']
    stats_dict, stdev_dict = find_stdev_for_every_stat(teams, rankings)
    tourney_dict, seeds = load_ncaa_tournament_csv(filename)
    field = ','.join(tourney_dict.values()).split(',')
    for r in rounds:
        print('=' * 80)
        print(' %s' % r)
        print('=' * 80)
        matchups = [[x, y] for x,y in zip(field[0::2], field[1::2])]
        matches = create_matches(matchups, teams, seeds)
        match_stats, games = aggregate_match_stats(stats_dict, stdev_dict,
                                                   matches, num_sims)
        predictions = create_predictions(match_stats, predictor)
        total_points, num_wins = determine_outcomes(predictions, games)
        prediction_list = determine_overall_results(matches, total_points,
                                                    num_wins, num_sims)
        display_predictions(prediction_list)
        field = reduce_field(prediction_list, field)


def initiate_algorithm(args, predictor, teams, rankings):
    if args.algorithm == DAILY_SIMULATION:
        start_daily_simulations(predictor, teams, args.skip_save_to_mongodb,
                                rankings, args.num_sims)
    elif args.algorithm == MONTE_CARLO_SIMULATION:
        start_monte_carlo_simulations(predictor, rankings, teams,
                                      args.num_sims, args.skip_save_to_mongodb)
    elif args.algorithm == MATCHUP:
        start_matchup_simulation(predictor, teams, rankings, args.num_sims,
                                 args.home, args.away)
    elif args.algorithm == POWER_RANKINGS:
        start_power_rankings(predictor, teams, rankings, args.num_sims,
                             args.skip_save_to_mongodb)
    elif args.algorithm == CONFERENCE_TOURNAMENT:
        if not path.isfile('simulations/simulation.json'):
            print('Conference simulation does not yet exist')
            print('Simulating conferences now...')
            start_monte_carlo_simulations(predictor, rankings, teams,
                                          args.num_sims,
                                          args.skip_save_to_mongodb)
        start_conference_tournament_simulator(predictor, teams, rankings,
                                              args.num_sims)
    elif args.algorithm == TOURNAMENT_SIMULATOR:
        start_ncaa_tournament_simulator(predictor, teams, rankings,
                                        args.num_sims, args.filename)


def check_dir(directory):
    if not path.exists(directory):
        makedirs(directory)


def check_path(filepath, name, match_data_location):
    if path.exists(filepath):
        return True
    else:
        if not path.exists('%s/%s' % (match_data_location, name)):
            makedirs('%s/%s' % (match_data_location, name))
        return False


def determine_location(game, team, sos, srs, opp_sos, opp_srs):
    if game.location == 'Away' or (game.location == 'Neutral' and \
       team.abbreviation not in game.boxscore_index):
        return opp_sos, opp_srs, sos, srs
    else:
        return sos, srs, opp_sos, opp_srs


def get_sos_and_srs(game, teams, team):
    sos = team.strength_of_schedule
    srs = team.simple_rating_system
    opponent = teams(game.opponent_abbr)
    opponent_sos = opponent.strength_of_schedule
    opponent_srs = opponent.simple_rating_system
    return determine_location(game, team, sos, srs, opponent_sos, opponent_srs)


def add_sos_and_srs(game, teams, team):
    df = game.dataframe_extended
    home_sos, home_srs, away_sos, away_srs = get_sos_and_srs(game, teams, team)
    try:
        df['home_strength_of_schedule'] = home_sos
        df['home_simple_rating_system'] = home_srs
        df['away_strength_of_schedule'] = away_sos
        df['away_simple_rating_system'] = away_srs
    except TypeError:
        return None
    return df


def pull_match_stats(dataset, teams, rankings):
    for team in teams:
        for game in team.schedule:
            path = '%s/%s/%s.plk' % (dataset, team.abbreviation.lower(),
                                     game.boxscore_index)
            if check_path(path, team.abbreviation.lower(), dataset) or \
               not game.boxscore_index:
                continue
            # Occurs when the opponent is Non-DI and the game should be skipped
            # since only DI matchups should be analyzed.
            if game.opponent_abbr == game.opponent_name:
                continue
            opponent = teams(game.opponent_abbr)
            df = add_sos_and_srs(game, teams, team)
            try:
                df.to_pickle(path)
            except AttributeError:
                continue


def arguments():
    parser = ArgumentParser()
    subparser = parser.add_subparsers(dest='algorithm', metavar='algorithm')
    subparser.add_parser(DAILY_SIMULATION, help='Run a simulation for all of '
    'the matchups taking place on the current day and save the predicted '
    'outcomes.')
    subparser.add_parser(MONTE_CARLO_SIMULATION, help='Simulate the final '
    'standings for each conference by predicting the outcomes of all remaining'
    'conference matchups for each team.')
    subparser.add_parser(POWER_RANKINGS, help='Create power rankings to '
    'determine relative strength in the league.')
    tournament = subparser.add_parser(TOURNAMENT_SIMULATOR, help='Run a '
    'simulation of the NCAA tournament to determine the overall winner and the'
    ' outcome of all games leading to the final.')
    tournament.add_argument('filename', help='Name of the .csv file containing'
    ' the bracket for the desired year, such as "2018-ncaa.csv"')
    subparser.add_parser(CONFERENCE_TOURNAMENT, help='Run a simulation of each'
    'conference tournament to determine the overall outcome. Seeds are based '
    'on projected final position in the conference standings according to the '
    'conference simulator algorithm.')
    matchup = subparser.add_parser(MATCHUP, help='Simulate the outcome between'
    ' two specific teams and determine the overall winner.')
    matchup.add_argument('home', help='Specify the home team\'s abbreviation, '
    'such as "purdue".')
    matchup.add_argument('away', help='Specify the away team\'s abbreviation, '
    'such as "indiana".')
    parser.add_argument('--num-sims', '-n', help='Optionally specify the '
    'number of simulations to run. Default value is %s simulations.' %
    NUM_SIMS, default=NUM_SIMS, type=int)
    parser.add_argument('--dataset', help='Specify which dataset to use. For '
    'testing purposes, use the "sample-data" directory. For production '
    'deployments, use "matches" with current data that was pulled.',
    default='matches')
    parser.add_argument('--skip-pulling-matches', help='Optionally choose to '
    'skip saving individual match data.', action='store_true')
    parser.add_argument('--skip-save-to-mongodb', help='Optionally skip saving'
    ' results to a MongoDB database.', action='store_true')
    return parser.parse_args()


def main():
    args = arguments()
    teams = Teams()
    rankings = Rankings().current
    if not args.skip_pulling_matches:
        pull_match_stats(args.dataset, teams, rankings)
    predictor = Predictor(args.dataset)
    initiate_algorithm(args, predictor, teams, rankings)


if __name__ == "__main__":
    main()
