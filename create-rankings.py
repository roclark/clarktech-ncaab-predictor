import numpy
import pandas as pd
import re
import requests
from bs4 import BeautifulSoup
from constants import YEAR
from datetime import datetime
from predictor import Predictor
from teams import TEAMS


AWAY = 1
HOME = 0
TEAM_NAME_REGEX = 'schools/.*?/%s.html' % YEAR
SCORES_PAGE = 'http://www.sports-reference.com/cbb/boxscores/index.cgi?month='


def read_team_stats_file(team_filename):
    return pd.read_csv(team_filename)


def convert_team_totals_to_averages(stats):
    fields_to_average = ['mp', 'fg', 'fga', 'fg2', 'fg2a', 'fg3', 'fg3a', 'ft',
                         'fta', 'orb', 'drb', 'trb', 'ast', 'stl', 'blk', 'tov',
                         'pf']
    num_games = stats['g']
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
        # Prepend all stats with 'opp_' to signify the away team as such.
        away_columns = ['opp_%s' % col for col in stats]
        stats.columns = away_columns
    return stats


def filter_stats(match_stats):
    fields_to_drop = ['pts', 'opp_pts', 'opp_g', 'opp_pts_per_g',
                      'pts_per_g']
    for field in fields_to_drop:
        match_stats.drop(field, 1, inplace=True)
    return match_stats


def get_totals(games_list, predictions, team_wins):
    for i in range(0, len(games_list)):
        winner = games_list[i][predictions[i]]
        team_wins[winner] += 1
    return team_wins


def predict_all_matches(predictor, stats_dict):
    games_list = []
    prediction_stats = pd.DataFrame()
    team_wins = {}

    for home_team in TEAMS.values():
        team_wins[home_team] = 0
        print home_team
        for away_team in TEAMS.values():
            if home_team == away_team:
                continue
            home_stats = stats_dict[home_team]
            away_stats = stats_dict['%s_away' % away_team]
            match_stats = pd.concat([away_stats, home_stats], axis=1)
            prediction_stats = prediction_stats.append(match_stats)
            games_list.append([home_team, away_team])
    match_stats_simplified = predictor.simplify(prediction_stats)
    predictions = predictor.predict(match_stats_simplified, int)
    team_wins = get_totals(games_list, predictions, team_wins)
    return team_wins


def create_stats_dictionary():
    stats_dict = {}

    for team in TEAMS.values():
        stats = read_team_stats_file('team-stats/%s' % team)
        stats = filter_stats(stats)
        home_stats = extract_stats_components(stats)
        away_stats = extract_stats_components(stats, away=True)
        stats_dict[team] = home_stats
        stats_dict['%s_away' % team] = away_stats
    return stats_dict


def print_rankings(team_wins):
    i = 1

    sorted_ranks = [(v,k) for k,v in team_wins.iteritems()]
    sorted_ranks.sort(reverse=True)
    for wins, team in sorted_ranks:
        print '%s. %s: %s' % (str(i).rjust(3), team, wins)
        i += 1


def main():
    predictor = Predictor()
    stats_dict = create_stats_dictionary()
    team_wins = predict_all_matches(predictor, stats_dict)
    print_rankings(team_wins)


if __name__ == "__main__":
    main()
