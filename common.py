import numpy
import requests


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
