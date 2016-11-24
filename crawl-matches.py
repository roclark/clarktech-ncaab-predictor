import os
import re
import requests

from bs4 import BeautifulSoup
from teams import TEAMS


BOXSCORES = 'http://www.sports-reference.com/cbb/boxscores'
SCHEDULE = 'http://www.sports-reference.com/cbb/schools/%s/2017-schedule.html'


def create_stats_dict(totals):
    stats = {}
    for stat in totals.find_all('td'):
        field = re.findall('data-stat=".*?"', str(stat))[0]
        field = re.sub('data-stat=', '', field)
        field = re.sub('"', '', field)
        value = stat.get_text()
        stats[field] = str(value)
    return stats


def find_winner(scores):
    try:
        away_score = scores[0].get_text()
        home_score = scores[1].get_text()
    except IndexError:
        return None
    if int(away_score) > int(home_score):
        return 'away'
    else:
        return 'home'


def save_match_stats(match_name, winner, away_stats, home_stats):
    match_filename = 'matches/%s' % match_name

    with open(match_filename, 'w') as match_file:
        match_file.write('%s\n' % winner)
        match_file.write('%s\n' % away_stats)
        match_file.write('%s\n' % home_stats)


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
        winner = find_winner(match_soup.find_all('div', {'class': 'score'}))
        team_totals = match_soup.find_all('tfoot')
        try:
            away_stats = create_stats_dict(team_totals[0])
            home_stats = create_stats_dict(team_totals[1])
        except IndexError:
            continue
        save_match_stats(match_name, winner, away_stats, home_stats)


def crawl_team_matches():
    count = 0
    matches = set()

    for name, team in TEAMS.items():
        count += 1
        print '[%s/%s] Extracting matches for %s' % (str(count).rjust(3),
                                                     len(TEAMS),
                                                     name)
        team_schedule = requests.get(SCHEDULE % team)
        team_soup = BeautifulSoup(team_schedule.text, 'html5lib')
        games = team_soup.find_all('table', {'class': 'sortable stats_table'})

        for game in games[-1].tbody.find_all('tr'):
            if game.find('a') and 'boxscores' in str(game.a):
                url = 'http://www.sports-reference.com%s' % str(game.a['href'])
                matches.add(url)
        get_match_data(matches)


if __name__ == "__main__":
    crawl_team_matches()
