import argparse
import json
import pandas as pd
from common import (differential_vector,
                    extract_stats_components,
                    read_team_stats_file)
from conference_tournaments import BRACKETS
from predictor import Predictor


def get_team_from_seed(seed, seeds):
    return seeds[seed-1]


def include_teams(game, games_list, seeds):
    for team in ['top_team', 'bottom_team']:
        try:
            seed = int(game[team])
            game[team] = get_team_from_seed(seed, seeds)
        except ValueError:
            game[team] = games_list[game[team]]['winner']
    return game


def get_team_stats(team):
    team = read_team_stats_file('team-stats/%s' % team)
    away_stats = extract_stats_components(team, away=True)
    home_stats = extract_stats_components(team, away=False)
    return home_stats, away_stats


def get_match_stats(top_team, bottom_team):
    top_home, top_away = get_team_stats(top_team)
    bottom_home, bottom_away = get_team_stats(bottom_team)
    first_game_stats = pd.concat([top_home, bottom_away], axis=1)
    second_game_stats = pd.concat([bottom_home, top_away], axis=1)
    return pd.concat([first_game_stats, second_game_stats])


def determine_winner(predictions, teams):
    # The predictions are shown as [top, bottom] then [bottom, top]
    first_game = 0
    second_game = 1
    result = {teams[0]: 0,
              teams[1]: 0}
    result[teams[0]] += predictions[first_game][0] + predictions[second_game][1]
    result[teams[0]] += predictions[first_game][1] + predictions[second_game][0]
    # For now, default to the higher seed advancing
    if result[teams[1]] > result[teams[0]]:
        return teams[1]
    else:
        return teams[0]


def simulate_tournament(seeds, games_list, predictor):
    fields_to_rename = {'win_loss_pct': 'win_pct'}
    winner = None

    for game_name, game_data in sorted(games_list.iteritems()):
        game_data = include_teams(game_data, games_list, seeds)
        match_stats = get_match_stats(game_data['top_team'],
                                      game_data['bottom_team'])
        match_stats = differential_vector(match_stats)
        match_stats.rename(columns=fields_to_rename, inplace=True)
        match_stats_simplified = predictor.simplify(match_stats)
        predictions = predictor.predict(match_stats_simplified, int)
        winner = determine_winner(predictions, [game_data['top_team'],
                                                game_data['bottom_team']])
        game_data['winner'] = winner
    # This winner is the last winner of the last game, AKA the champion
    return winner


def get_teams_dict(simulation, conference):
    for conf in simulation['simulation']['conferences']:
        key = conf.keys()[0]
        if key == conference:
            return conf[key]


def build_projected_points(teams_dict):
    conf_points = {}

    for team in teams_dict:
        name = str(team['nickname'])
        points = team['points']
        conf_points[name] = points
    return conf_points


def find_projected_seeds(simulation, conference):
    teams_dict = get_teams_dict(simulation, conference)
    conf_points = build_projected_points(teams_dict)
    return sorted(conf_points, key=conf_points.get, reverse=True)


def load_simulation():
    with open('simulations/simulation.json') as json_data:
        return json.load(json_data)


def parse_arguments():
    parser = argparse.ArgumentParser()
    parser.add_argument('--conference', help='Optionally specify a particular '
    'conference to analyze the power rankings for. For example, specify "Big '
    'Ten Conference" to get power rankings only comprising the Big Ten teams.',
    default=None)
    return parser.parse_args()


def main():
    args = parse_arguments()
    predictor = Predictor()
    simulation = load_simulation()
    seeds = find_projected_seeds(simulation, args.conference)
    winner = simulate_tournament(seeds, BRACKETS[args.conference], predictor)
    print winner


if __name__ == '__main__':
    main()
