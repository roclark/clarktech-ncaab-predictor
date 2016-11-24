import re
import requests

from bs4 import BeautifulSoup
from teams import TEAMS


TEAM_PAGE = 'http://www.sports-reference.com/cbb/schools/%s/2017.html'


def write_team_stats_file(team_link, name, stats):
    team_stats = {}
    opponent_stats = {}

    for key, value in stats.items():
        if key.startswith('opp_'):
            opponent_stats[key] = value
        else:
            team_stats[key] = value

    with open('team-stats/%s' % team_link, 'w') as team_stats_file:
        team_stats_file.write('# %s\n' % name)
        team_stats_file.write('%s\n%s\n' % (team_stats, opponent_stats))


def parse_team_stats(team_html):
    team_stats = {}

    for item in team_html.find_all('tr'):
        if 'Opponent' in str(item) or 'Team' in str(item):
            for tag in item.find_all('td'):
                field = re.findall('data-stat="\S+"', str(tag))[0]
                field = re.findall('"\S+"', field)[0].replace('"', '')
                if 'Opponent' in str(item) and field == 'g':
                    field = 'opp_g'
                elif 'Opponent' in str(item) and field == 'mp':
                    field = 'opp_mp'
                team_stats[field] = str(tag.get_text())
    return team_stats


def traverse_teams_list():
    teams_parsed = 0

    for name, team in TEAMS.items():
        teams_parsed += 1
        print '[%s/%s] Extracting stats for: %s' % (str(teams_parsed).rjust(3),
                                                    len(TEAMS),
                                                    name)
        team_page = requests.get(TEAM_PAGE % team)
        team_html = BeautifulSoup(team_page.text, 'html5lib')
        team_stats = parse_team_stats(team_html)
        write_team_stats_file(team, name, team_stats)


def main():
    traverse_teams_list()


if __name__ == "__main__":
    main()
