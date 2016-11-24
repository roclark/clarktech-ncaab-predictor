import re
import requests

from bs4 import BeautifulSoup


TEAMS_URL = 'http://www.sports-reference.com/cbb/seasons/2017-school-stats.html'


def request_teams_list():
    teams_request = requests.get(TEAMS_URL)
    teams_html_page = BeautifulSoup(teams_request.text, 'html5lib')
    return teams_html_page.find('tbody')


def parse_team(team_tag):
    team_name = re.findall('>.*<', team_tag)[0]
    team_name = re.sub('>', '', team_name)
    team_name = re.sub('<', '', team_name)
    team_name = re.sub('&amp;', '&', team_name)
    team_link = re.findall('schools/.*/2017.html', team_tag)[0]
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
            team_name, team_link = parse_team(str(team.a))
            teams_file.write('    "%s": "%s",\n' % (team_name, team_link))
            num_teams += 1
            print 'Team found: %s' % team_name
        print '%s total teams found' % num_teams
        teams_file.write('}\n')


def main():
    teams_list = request_teams_list()
    parse_teams_list(teams_list)


if __name__ == "__main__":
    main()
