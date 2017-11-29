import csv
import os
import re
import requests
from bs4 import BeautifulSoup
from common import include_team_rank
from constants import YEAR
from teams import TEAMS


BOXSCORES = 'http://www.sports-reference.com/cbb/boxscores/'
SCHEDULE = 'http://www.sports-reference.com/cbb/schools/%s/%s-schedule.html'


def create_stats_dict(stats_dict, totals, away=False):
    for tag in totals.find_all('td'):
        field = str(dict(tag.attrs).get('data-stat'))
        if away:
            field = 'opp_%s' % field
        try:
            value = float(tag.get_text())
        except ValueError:
            # Sometimes, there is no value, such as when a team doesn't attempt
            # a free throw. In that case, default to 0.
            value = 0
        stats_dict[field] = value
    return stats_dict


def check_if_home_team_won(scores):
    try:
        away_score = scores[0].get_text()
        home_score = scores[1].get_text()
    except IndexError:
        return None
    if int(away_score) > int(home_score):
        return 0
    else:
        return 1


def get_rank(team):
    ranking = team.find_all('span', class_='pollrank')
    if ranking:
        ranking = ranking[0].get_text()
        ranking = re.sub('.*\(', '', ranking)
        ranking = re.sub('\).*', '', ranking)
        return ranking
    return '-'


def check_if_team_ranked(teams):
    away_team, home_team = teams.find_all('tr')
    away_rank = get_rank(away_team)
    home_rank = get_rank(home_team)
    return away_rank, home_rank


def save_match_stats(match_name, stats):
    match_filename = 'matches/%s' % match_name
    header = stats.keys()

    with open(match_filename, 'w') as match_file:
        dict_writer = csv.DictWriter(match_file, header)
        dict_writer.writeheader()
        dict_writer.writerows([stats])


def match_already_saved(match_name):
    if os.path.isfile('matches/%s' % match_name):
        return True
    return False


def get_match_data(matches):
    for match in matches:
        match_name = match.replace(BOXSCORES, '')
        match_name = match_name.replace('.html', '')
        if match_already_saved(match_name):
            continue
        match_request = requests.get(match)
        match_soup = BeautifulSoup(match_request.text, 'html5lib')
        winner = check_if_home_team_won(match_soup.find_all('div',
                                                            {'class': 'score'}
                                                           ))
        team_totals = match_soup.find_all('tfoot')
        # Sometimes, sports-reference makes a mistake and doesn't sum the totals
        # in the bottom of the stats tables. Instead of calculating them, and
        # dramatically increasing the complexity of the parser, just skip the
        # game as the sample size is large enough for a game or two to be
        # largely insignificant.
        if len(team_totals) < 2:
            continue
        stats = create_stats_dict({}, team_totals[0])
        stats = create_stats_dict(stats, team_totals[1], away=True)
        home_rank, away_rank = check_if_team_ranked(
            match_soup.find_all('div', class_='game_summary nohover current')[0]
        )
        stats['home_win'] = winner
        stats = include_team_rank(stats, home_rank)
        stats = include_team_rank(stats, away_rank, away=True)
        save_match_stats(match_name, stats)


def crawl_team_matches():
    count = 0
    matches = set()

    for name, team in TEAMS.items():
        count += 1
        print '[%s/%s] Extracting matches for %s' % (str(count).rjust(3),
                                                     len(TEAMS),
                                                     name)
        team_schedule = requests.get(SCHEDULE % (team, YEAR))
        team_soup = BeautifulSoup(team_schedule.text, 'html5lib')
        games = team_soup.find_all('table', {'class': 'sortable stats_table'})

        for game in games[-1].tbody.find_all('tr'):
            if game.find('a') and 'boxscores' in str(game.a):
                url = 'http://www.sports-reference.com%s' % str(game.a['href'])
                matches.add(url)
        get_match_data(matches)


if __name__ == "__main__":
    if not os.path.exists('matches'):
        os.makedirs('matches')
    crawl_team_matches()
