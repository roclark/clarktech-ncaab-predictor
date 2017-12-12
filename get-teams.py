import re
import sys
from bs4 import BeautifulSoup
from common import make_request
from constants import YEAR


TEAMS_URL = 'http://www.sports-reference.com/cbb/seasons/%s-school-stats.html' % YEAR


def request_teams_list():
    teams_request = make_request(TEAMS_URL)
    if not teams_request:
        return None
    teams_html_page = BeautifulSoup(teams_request.text, 'lxml')
    return teams_html_page.find('tbody')


def parse_team(team_tag):
    team_name = team_tag.get_text()
    team_name = re.sub('&amp;', '&', team_name)
    team_link = re.findall('schools/.*/%s.html' % YEAR, str(team_tag))[0]
    team_link = re.sub('schools/', '', team_link)
    team_link = re.sub('/.*', '', team_link)
    return team_name, team_link


def parse_teams_list(teams_list):
    num_teams = 0

    with open('teams.py', 'w') as teams_file:
        teams_file.write('TEAMS = {\n')
        for team in teams_list.find_all('tr'):
            if team.a is None:
                continue
            team_name, team_link = parse_team(team.a)
            teams_file.write('    "%s": "%s",\n' % (team_name, team_link))
            num_teams += 1
            print 'Team found: %s' % team_name
        print '%s total teams found' % num_teams
        teams_file.write('}\n')


def main():
    teams_list = request_teams_list()
    if not teams_list:
        print 'Error: Could not capture teams'
        sys.exit(1)
    parse_teams_list(teams_list)


if __name__ == "__main__":
    main()
