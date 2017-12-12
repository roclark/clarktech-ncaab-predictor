import re
from bs4 import BeautifulSoup
from common import make_request
from constants import YEAR
from requests import Session


STATS_PAGE = 'http://www.sports-reference.com/cbb/seasons/%s-school-stats.html'


def parse_name(href):
    name = href.replace('/cbb/schools/', '')
    name = re.sub('/.*', '', name)
    return name


def parse_stats_page(stats_page):
    sos_list = []

    stats_html = BeautifulSoup(stats_page.text, 'lxml')
    # The first row just describes the stats. Skip it as it is irrelevant.
    team_stats = stats_html.find_all('tr', class_='')[1:]
    for team in team_stats:
        name = None
        sos = None
        for stat in team.find_all('td'):
            if str(dict(stat.attrs).get('data-stat')) == 'school_name':
                nickname = parse_name(str(stat.a['href']))
                name = stat.get_text()
            if str(dict(stat.attrs).get('data-stat')) == 'sos':
                sos = stat.get_text()
        sos_list.append([str(nickname), str(sos)])
    return sos_list


def get_stats_page():
    session = Session()
    session.trust_env = False
    stats_page = make_request(session, STATS_PAGE % YEAR)
    return stats_page


def save_list(sos_list):
    with open('sos.py', 'w') as sos_file:
        sos_file.write('SOS = {\n')
        for pair in sos_list:
            name, sos = pair
            sos_file.write('    "%s": %s,\n' % (name, sos))
        sos_file.write('}\n')


def main():
    stats_page = get_stats_page()
    if not stats_page:
        print 'Error retrieving stats page'
        return None
    sos_list = parse_stats_page(stats_page)
    save_list(sos_list)


if __name__ == "__main__":
    main()
