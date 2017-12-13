import csv
import os
import re
from bs4 import BeautifulSoup
from common import include_team_rank, include_wins_and_losses, make_request
from constants import YEAR
from requests import Session
from sos import SOS
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


def include_sos(stats, name, away=False):
    print name, SOS[name]
    if away:
        stats['opp_sos'] = SOS[name]
    else:
        stats['sos'] = SOS[name]
    return stats


def get_names(names):
    home_name = None
    away_name = None

    for name in names.find_all('a'):
        if 'boxscores' in str(name):
            continue
        name = str(name).replace('<a href="/cbb/schools/', '')
        name = re.sub('/.*', '', name)
        if not away_name:
            away_name = name
        else:
            home_name = name
    return home_name, away_name


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


def parse_records(record_string):
    record = re.findall('\d+-\d+', record_string)[0]
    return str(record).split('-')


def get_wins_and_losses(html):
    regex_capture = '<div class="score">\d+</div><div>\d+-\d+</div>'
    records = re.findall(regex_capture, str(html))
    # Non-DI schools do not have their records saved. Skip these games as we
    # don't want them to throw off the classifier.
    if len(records) < 2:
        return None
    record_list = []
    for record in records:
        record_list.append(parse_records(record))
    #[[Home Wins, Home Losses], [Away Wins, Away Losses]]
    return record_list


def get_match_data(session, matches):
    for match in matches:
        match_name = match.replace(BOXSCORES, '')
        match_name = match_name.replace('.html', '')
        if match_already_saved(match_name):
            continue
        match_request = make_request(session, match)
        if not match_request:
            continue
        match_soup = BeautifulSoup(match_request.text, 'lxml')
        records = get_wins_and_losses(match_soup)
        # Skip any teams that don't have a record as they are non-DI.
        if not records:
            continue
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
        home_name, away_name = get_names(
            match_soup.find_all('div', class_='game_summary nohover current')[0]
        )
        stats['home_win'] = winner
        stats = include_team_rank(stats, home_rank)
        stats = include_team_rank(stats, away_rank, away=True)
        stats = include_wins_and_losses(stats, *records[0], away=True)
        stats = include_wins_and_losses(stats, *records[1])
        stats = include_sos(stats, home_name)
        stats = include_sos(stats, away_name, away=True)
        save_match_stats(match_name, stats)


def crawl_team_matches():
    count = 0
    session = Session()
    session.trust_env = False

    for name, team in TEAMS.items():
        matches = set()
        count += 1
        print '[%s/%s] Extracting matches for %s' % (str(count).rjust(3),
                                                     len(TEAMS),
                                                     name)
        team_schedule = make_request(session, SCHEDULE % (team, YEAR))
        if not team_schedule:
            continue
        team_soup = BeautifulSoup(team_schedule.text, 'lxml')
        games = team_soup.find_all('table', {'class': 'sortable stats_table'})

        for game in games[-1].tbody.find_all('tr'):
            if game.find('a') and 'boxscores' in str(game.a):
                url = 'http://www.sports-reference.com%s' % str(game.a['href'])
                matches.add(url)
        get_match_data(session, matches)


if __name__ == "__main__":
    if not os.path.exists('matches'):
        os.makedirs('matches')
    crawl_team_matches()
