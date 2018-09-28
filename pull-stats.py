import argparse
from os import path, makedirs
from sportsreference.ncaab.teams import Teams


def check_dir(directory):
    if not path.exists(directory):
        makedirs(directory)


def check_path(filepath, name, match_data_location):
    if path.exists(filepath):
        return True
    else:
        if not path.exists('%s/%s' % (match_data_location, name)):
            makedirs('%s/%s' % (match_data_location, name))
        return False


def arguments():
    parser = argparse.ArgumentParser()
    parser.add_argument('--match-data-location', help='Specify the name of the'
                        ' directory to store match data, such as "matches". If'
                        ' this directory does not yet exist, it will be '
                        'created.', default='matches')
    parser.add_argument('--team-stats-location', help='Specify the name of '
                        'the directory to store team stats, such as '
                        '"team-stats". If this directory does not yet exist, '
                        'it will be created.', default='team-stats')
    parser.add_argument('--skip-pulling-matches', help='Optionally choose to '
                        'skip saving individual match data and instead just '
                        'pull team stats data.', action='store_true')
    return parser.parse_args()


def determine_location(game, team, sos, srs, opp_sos, opp_srs):
    if game.location == 'Away' or (game.location == 'Neutral' and \
       team.abbreviation not in game.boxscore_index):
        return opp_sos, opp_srs, sos, srs
    else:
        return sos, srs, opp_sos, opp_srs


def get_sos_and_srs(game, teams, team):
    sos = team.strength_of_schedule
    srs = team.simple_rating_system
    opponent = teams(game.opponent_abbr)
    opponent_sos = opponent.strength_of_schedule
    opponent_srs = opponent.simple_rating_system
    return determine_location(game, team, sos, srs, opponent_sos, opponent_srs)


def add_sos_and_srs(game, teams, team):
    df = game.dataframe_extended
    home_sos, home_srs, away_sos, away_srs = get_sos_and_srs(game, teams, team)
    try:
        df['home_strength_of_schedule'] = home_sos
        df['home_simple_rating_system'] = home_srs
        df['away_strength_of_schedule'] = away_sos
        df['away_simple_rating_system'] = away_srs
    except TypeError:
        return None
    return df


def main():
    args = arguments()
    check_dir(args.match_data_location)
    check_dir(args.team_stats_location)
    teams = Teams()
    for team in teams:
        df = team.dataframe
        defensive_rebound_percentage = 100.0 * df['defensive_rebounds'] /\
            (df['defensive_rebounds'] + df['opp_offensive_rebounds'])
        df['defensive_rebound_percentage'] = defensive_rebound_percentage
        df.to_pickle('%s/%s.plk' % (args.team_stats_location,
                                    team.abbreviation.lower()))
        if args.skip_pulling_matches:
            continue
        for game in team.schedule:
            path = '%s/%s/%s.plk' % (args.match_data_location,
                                     team.abbreviation.lower(),
                                     game.boxscore_index)
            if check_path(path, team.abbreviation.lower(),
                          args.match_data_location) or \
               not game.boxscore_index:
                continue
            # Occurs when the opponent is Non-DI and the game should be skipped
            # since only DI matchups should be analyzed.
            if game.opponent_abbr == game.opponent_name:
                continue
            opponent = teams(game.opponent_abbr)
            opponent.strength_of_schedule, opponent.simple_rating_system
            df = add_sos_and_srs(game, teams, team)
            try:
                df.to_pickle(path)
            except AttributeError:
                continue


if __name__ == '__main__':
    main()
