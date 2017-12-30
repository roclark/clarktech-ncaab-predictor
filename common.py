import difflib
import numpy
import pandas as pd
import re
import requests


FIELDS_TO_COMBINE = {
    'pts': 'opp_pts',
    'fg2a': 'opp_fg2a',
    'losses': 'opp_losses',
    'sos': 'opp_sos',
    'trb': 'opp_trb',
    'fg_pct': 'opp_fg_pct',
    'fg2': 'opp_fg2',
    'fg3': 'opp_fg3',
    'win_pct': 'opp_win_pct',
    'weighted_sos': 'opp_weighted_sos',
    'fg3_pct': 'opp_fg3_pct',
    'tov': 'opp_tov',
    'fta': 'opp_fta',
    'mp': 'opp_mp',
    'stl': 'opp_stl',
    'fg3a': 'opp_fg3a',
    'pf': 'opp_pf',
    'blk': 'opp_blk',
    'ft_pct': 'opp_ft_pct',
    'ft': 'opp_ft',
    'orb': 'opp_orb',
    'ast': 'opp_ast',
    'fg': 'opp_fg',
    'fga': 'opp_fga',
    'tov': 'opp_tov',
    'wins': 'opp_wins',
    'drb': 'opp_drb',
    'fg2_pct': 'opp_fg2_pct',
    'ranked': 'opp_ranked',
    'win_loss_pct': 'opp_win_loss_pct'
}


def include_team_rank(team_stats, ranking, away=False):
    tier1 = 'rank1-5'
    tier2 = 'rank6-10'
    tier3 = 'rank11-15'
    tier4 = 'rank16-20'
    tier5 = 'rank21-25'
    overall = 'ranked'

    if away:
        tier1 = 'opp_rank1-5'
        tier2 = 'opp_rank6-10'
        tier3 = 'opp_rank11-15'
        tier4 = 'opp_rank16-20'
        tier5 = 'opp_rank21-25'
        overall = 'opp_ranked'

    team_stats[tier1] = 0
    team_stats[tier2] = 0
    team_stats[tier3] = 0
    team_stats[tier4] = 0
    team_stats[tier5] = 0
    team_stats[overall] = 0

    try:
        ranking = int(ranking)
    except ValueError:
        return team_stats

    if ranking < 6:
        team_stats[tier1] = 1
    elif ranking < 11:
        team_stats[tier2] = 1
    elif ranking < 16:
        team_stats[tier3] = 1
    elif ranking < 21:
        team_stats[tier4] = 1
    elif ranking < 26:
        team_stats[tier5] = 1
    team_stats[overall] = 1
    return team_stats


def read_team_stats_file(team_filename):
    team_filename = re.sub('\(\d+\) +', '', team_filename)
    return pd.read_csv(team_filename)


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
    fields_to_drop = ['pts', 'opp_pts', 'g', 'opp_g']
    fields_to_rename = {'win_loss_pct': 'win_pct',
                        'opp_win_loss_pct': 'opp_win_pct'}
    for field in fields_to_drop:
        match_stats.drop(field, 1, inplace=True)
    match_stats.rename(columns=fields_to_rename, inplace=True)
    return match_stats


def weighted_sos(stats, sos, win_pct, max_sos=None, min_sos=None, away=False):
    try:
        from sos import MAX_SOS
        from sos import MIN_SOS
        min_sos = MIN_SOS
        max_sos = MAX_SOS
    except ImportError:
        pass
    sos_range = max_sos - min_sos
    weighted_sos = sos - min_sos
    weighted_sos *= win_pct
    if away:
        stats['opp_weighted_sos'] = weighted_sos
    else:
        stats['weighted_sos'] = weighted_sos
    return stats


def differential_vector(stats):
    for home_feature, away_feature in FIELDS_TO_COMBINE.items():
        try:
            stats[home_feature] = stats[home_feature] - stats[away_feature]
            stats.drop(away_feature, 1, inplace=True)
        except KeyError:
            continue
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
