import numpy


def include_team_rank(team_stats, ranking, away=False):
    tier1 = 'rank1-5'
    tier2 = 'rank6-10'
    tier3 = 'rank11-15'
    tier4 = 'rank16-20'
    tier5 = 'rank21-25'

    if away:
        tier1 = 'opp_rank1-5'
        tier2 = 'opp_rank6-10'
        tier3 = 'opp_rank11-15'
        tier4 = 'opp_rank16-20'
        tier5 = 'opp_rank21-25'

    team_stats[tier1] = 0
    team_stats[tier2] = 0
    team_stats[tier3] = 0
    team_stats[tier4] = 0
    team_stats[tier5] = 0

    try:
        int(ranking)
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
    return team_stats


def read_match_stats_file(filename):
    match_file = open(filename, 'r')
    winner = match_file.readline().strip()
    away_stats = match_file.readline().strip()
    home_stats = match_file.readline().strip()
    return (winner, away_stats, home_stats)


def read_team_stats_file(filename):
    stats_file = open(filename, 'r')
    team_name = stats_file.readline().strip().replace('# ', '')
    team_stats = stats_file.readline().strip()
    return (team_name, team_stats)


def create_stats_array(away, home):
    stats = [float(away['mp']), float(away['fg']), float(away['fga']),
             float(away['fg_pct']), float(away['fg2']), float(away['fg2a']),
             float(away['fg2a']), float(away['fg2_pct']), float(away['fg3']),
             float(away['fg3a']), float(away['fg3_pct']), float(away['ft']),
             float(away['fta']), float(away['ft_pct']), float(away['orb']),
             float(away['drb']), float(away['trb']), float(away['ast']),
             float(away['stl']), float(away['blk']), float(away['tov']),
             float(home['mp']), float(home['fg']), float(home['fga']),
             float(home['fg_pct']), float(home['fg2']), float(home['fg2a']),
             float(home['fg2a']), float(home['fg2_pct']), float(home['fg3']),
             float(home['fg3a']), float(home['fg3_pct']), float(home['ft']),
             float(home['fta']), float(home['ft_pct']), float(home['orb']),
             float(home['drb']), float(home['trb']), float(home['ast']),
             float(home['stl']), float(home['blk']), float(home['tov'])]
    return stats
