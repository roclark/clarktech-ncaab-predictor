import csv
import re
import os
from bs4 import BeautifulSoup
from common import include_team_rank, make_request
from constants import YEAR
from requests import Session
from teams import TEAMS


TEAM_PAGE = 'http://www.sports-reference.com/cbb/schools/%s/%s.html'
SCHEDULE_PAGE = 'http://www.sports-reference.com/cbb/schools/%s/%s-schedule.html'


def write_team_stats_file(team_link, name, stats):
    header = stats.keys()

    with open('team-stats/%s' % team_link, 'w') as team_stats_file:
        dict_writer = csv.DictWriter(team_stats_file, header)
        dict_writer.writeheader()
        dict_writer.writerows([stats])


def parse_team_stats(team_html):
    team_stats = {}

    for item in team_html.find_all('tr'):
        # Sometimes, a player has 'Team' in their high school name. In such
        # cases, skip over them as we only want the Team and Opponents Stats
        # section.
        if 'high_school' in str(item):
            continue
        if 'Opponent' in str(item) or 'Team' in str(item):
            for tag in item.find_all('td'):
                field = str(dict(tag.attrs).get('data-stat'))
                if 'Opponent' in str(item) and field == 'g':
                    field = 'opp_g'
                elif 'Opponent' in str(item) and field == 'mp':
                    field = 'opp_mp'
                team_stats[field] = float(tag.get_text())
    return team_stats


def parse_team_rank(schedule_html, team_stats):
    for item in schedule_html.find_all('tr'):
        if item.find_all('td'):
            ranking = str(item.find_all('td', class_='center')[-1].get_text())
            return include_team_rank(team_stats, ranking)


def traverse_teams_list():
    teams_parsed = 0
    session = Session()
    session.trust_env = False

    for name, team in TEAMS.items():
        teams_parsed += 1
        print '[%s/%s] Extracting stats for: %s' % (str(teams_parsed).rjust(3),
                                                    len(TEAMS),
                                                    name)
        team_page = make_request(session, TEAM_PAGE % (team, YEAR))
        if not team_page:
            continue
        team_html = BeautifulSoup(team_page.text, 'lxml')
        team_stats = parse_team_stats(team_html)
        schedule = make_request(session, SCHEDULE_PAGE % (team, YEAR))
        if not schedule:
            continue
        schedule_html = BeautifulSoup(schedule.text, 'lxml')
        team_stats = parse_team_rank(schedule_html, team_stats)
        write_team_stats_file(team, name, team_stats)


def main():
    traverse_teams_list()


if __name__ == "__main__":
    if not os.path.exists('team-stats'):
        os.makedirs('team-stats')
    main()
