import difflib
import numpy
import pandas as pd
import re
import requests


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
    'home_steal_percentage': 'away_steal_percentage',
    'home_steals': 'away_steals',
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


def read_team_stats_file(team_filename):
    team_filename = re.sub('\(\d+\) +', '', team_filename)
    return pd.read_pickle('%s.plk' % team_filename)


def make_request(session, url):
    # Try a URL 3 times. If it still doesn't work, just skip the entry.
    for i in xrange(3):
        try:
            response = session.get(url)
            return response
        except requests.exceptions.ConnectionError:
            continue
    return None


def include_wins_and_losses(stats, wins, losses, away=False):
    wins = float(wins)
    losses = float(losses)
    win_percentage = float(wins / (wins + losses))

    if away:
        stats['opp_wins'] = wins
        stats['opp_losses'] = losses
        stats['opp_win_pct'] = win_percentage
    else:
        stats['wins'] = wins
        stats['losses'] = losses
        stats['win_pct'] = win_percentage
    return stats


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


def find_name_from_nickname(nickname):
    from teams import TEAMS

    nickname = difflib.get_close_matches(nickname, TEAMS.values())[0]
    for key, value in TEAMS.items():
        if value == nickname:
            return key


def find_nickname_from_name(name):
    from teams import TEAMS

    try:
        nickname = TEAMS[name]
    except KeyError:
        name = difflib.get_close_matches(name, TEAMS.keys())[0]
        nickname = TEAMS[name]
    return nickname
