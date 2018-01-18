import csv
import json
import re
import os
from bs4 import BeautifulSoup
from common import include_team_rank, make_request, weighted_sos
from constants import YEAR
from mascots import MASCOTS
from requests import Session


CONFERENCE_PAGE = 'https://www.sports-reference.com/cbb/seasons/%s.html'
RANKINGS_PAGE = 'https://www.sports-reference.com/cbb/seasons/%s-polls.html'
STATS_PAGE = 'http://www.sports-reference.com/cbb/seasons/%s-school-stats.html'


def parse_name(href):
    name = href.replace('/cbb/schools/', '')
    name = re.sub('/.*', '', name)
    return name


def add_categories(stats):
    fg2 = stats['fg'] - stats['fg3']
    fg2a = stats['fga'] - stats['fg3a']
    fg2_pct = float(fg2 / fg2a)
    drb = stats['trb'] - stats['orb']
    stats['fg2'] = fg2
    stats['fg2a'] = fg2a
    stats['fg2_pct'] = fg2_pct
    stats['drb'] = drb
    return stats


def parse_stats_page(stats_page, rankings, conferences):
    sos_list = []
    teams_list = []

    stats_html = BeautifulSoup(stats_page.text, 'lxml')
    sos_tags = stats_html.find_all('td', attrs={'data-stat': 'sos'})
    sos_tags = [float(tag.get_text()) for tag in sos_tags]
    min_sos = min(sos_tags)
    max_sos = max(sos_tags)

    # The first row just describes the stats. Skip it as it is irrelevant.
    team_stats = stats_html.find_all('tr', class_='')[1:]
    for team in team_stats:
        name = None
        sos = None
        stats = {}
        for stat in team.find_all('td'):
            if str(dict(stat.attrs).get('data-stat')) == 'school_name':
                nickname = parse_name(str(stat.a['href']))
                name = stat.get_text()
                continue
            if str(dict(stat.attrs).get('data-stat')) == 'sos':
                sos = stat.get_text()
            field = str(dict(stat.attrs).get('data-stat'))
            if field == 'x':
                continue
            if field == 'opp_pts':
                field = 'away_pts'
            value = float(stat.get_text())
            stats[field] = value
        try:
            rank = rankings[nickname]
        except KeyError:
            rank = '-'
        stats = add_categories(stats)
        stats = include_team_rank(stats, rank)
        stats = weighted_sos(stats, float(sos), stats['win_loss_pct'], max_sos,
                             min_sos)
        write_team_stats_file(nickname, stats, name, rankings, conferences)
        teams_list.append([name, nickname])
        sos_list.append([str(nickname), str(sos)])
    write_teams_list(teams_list)
    return sos_list, max_sos, min_sos


def get_stats_page(session):
    stats_page = make_request(session, STATS_PAGE % YEAR)
    return stats_page


def save_sos_list(sos_list, max_sos, min_sos):
    with open('sos.py', 'w') as sos_file:
        sos_file.write('SOS = {\n')
        for pair in sos_list:
            name, sos = pair
            sos_file.write('    "%s": %s,\n' % (name, sos))
        sos_file.write('}\n')
        sos_file.write('MIN_SOS = %s\n' % min_sos)
        sos_file.write('MAX_SOS = %s\n' % max_sos)


def save_conferences(conferences_dict):
    with open('conferences.py', 'w') as conf_file:
        conf_file.write('CONFERENCES = {\n')
        for conf_name, teams in conferences_dict.items():
            conf_file.write('    "%s": %s,\n' % (conf_name, teams))
        conf_file.write('}\n')


def write_team_stats_file(nickname, stats, name, rankings, conferences):
    header = stats.keys()

    with open('team-stats/%s' % nickname, 'w') as team_stats_file:
        dict_writer = csv.DictWriter(team_stats_file, header)
        dict_writer.writeheader()
        dict_writer.writerows([stats])
    with open('team-stats/%s.json' % nickname, 'w') as stats_json_file:
        stats["name"] = name
        try:
            stats["rank"] = rankings[nickname]
        except KeyError:
            stats["rank"] = "NR"
        for key, value in conferences.items():
            if nickname in value:
                stats["conference"] = key
                break
        stats["mascot"] = MASCOTS[nickname]
        json.dump(stats, stats_json_file)


def write_teams_list(teams_list):
    with open('teams.py', 'w') as teams_file:
        teams_file.write('TEAMS = {\n')
        for team in teams_list:
            name, nickname = team
            teams_file.write('    "%s": "%s",\n' % (name, nickname))
        teams_file.write('}\n')


def get_rankings(session):
    rankings_dict = {}

    rankings_page = make_request(session, RANKINGS_PAGE % YEAR)
    rankings_html = BeautifulSoup(rankings_page.text, 'lxml')
    body = rankings_html.tbody
    # Only parse the first 25 results as these are the most recent rankings.
    for row in body.find_all('tr')[:25]:
        rank = None
        nickname = None
        for stat in row.find_all('td'):
            if str(dict(stat.attrs).get('data-stat')) == 'school_name':
                nickname = parse_name(str(stat.a['href']))
            if str(dict(stat.attrs).get('data-stat')) == 'rank':
                rank = stat.get_text()
        rankings_dict[nickname] = int(rank)
    return rankings_dict


def get_conference_teams(session, conference_uri):
    teams = []

    url = 'http://www.sports-reference.com%s' % conference_uri
    conference_page = make_request(session, url)
    conference_html = BeautifulSoup(conference_page.text, 'lxml')
    body = conference_html.tbody
    for row in body.find_all('tr'):
        for stat in row.find_all('td'):
            if str(dict(stat.attrs).get('data-stat')) == 'school_name':
                name = str(stat).replace('<a href="/cbb/schools/', '')
                name = re.sub('/.*', '', name)
                name = re.sub('.*>', '', name)
                teams.append(name)
    return teams


def get_conferences(session):
    conference_dict = {}

    conference_page = make_request(session, CONFERENCE_PAGE % YEAR)
    conference_html = BeautifulSoup(conference_page.text, 'lxml')
    body = conference_html.tbody
    for row in body.find_all('tr'):
        for stat in row.find_all('td'):
            if str(dict(stat.attrs).get('data-stat')) == 'conf_name':
                conf_name = stat.get_text()
                conf_uri = stat.a['href']
                teams = get_conference_teams(session, conf_uri)
                conference_dict[conf_name] = teams
    return conference_dict


def main():
    session = Session()
    session.trust_env = False

    conferences = get_conferences(session)
    rankings = get_rankings(session)
    stats_page = get_stats_page(session)
    if not stats_page:
        print 'Error retrieving stats page'
        return None
    sos_list, max_sos, min_sos = parse_stats_page(stats_page, rankings,
                                                  conferences)
    save_sos_list(sos_list, max_sos, min_sos)
    save_conferences(conferences)


if __name__ == "__main__":
    if not os.path.exists('team-stats'):
        os.makedirs('team-stats')
    main()
