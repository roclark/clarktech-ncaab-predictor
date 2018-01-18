import json
from common import find_nickname_from_name
from mascots import MASCOTS


class Prediction:
    def __init__(self, tags, home_name, home_nickname, away_name, away_nickname,
                 winner, loser):
        if winner == home_name:
            winner_nickname = home_nickname
            loser_nickname = away_nickname
        else:
            winner_nickname = away_nickname
            loser_nickname = home_nickname
        self.prediction = {
            "tags": tags,
            "teams": {
                "home": {
                    "name": home_name,
                    "nickname": home_nickname,
                    "mascot": MASCOTS[home_nickname],
                },
                "away": {
                    "name": away_name,
                    "nickname": away_nickname,
                    "mascot": MASCOTS[away_nickname],
                }
            },
            "prediction": {
                "winner": {
                    "name": winner,
                    "nickname": winner_nickname,
                    "mascot": MASCOTS[winner_nickname],
                },
                "loser": {
                    "name": loser,
                    "nickname": loser_nickname,
                    "mascot": MASCOTS[loser_nickname],
                }
            }
        }


class Simulation:
    def __init__(self, num_sims, results_dict, points_dict):
        conferences_list = []
        for conference, standings in results_dict.items():
            teams_list = []
            for name, standings in standings.items():
                nickname = find_nickname_from_name(name)
                points = points_dict[conference][nickname]
                mascot = MASCOTS[nickname]
                team_dict = {
                    "name": name,
                    "nickname": nickname,
                    "mascot": mascot,
                    "standings": standings,
                    "points": float(points) / float(num_sims),
                }
                teams_list.append(team_dict)
            conferences_list.append({conference: teams_list})
        self.simulation = {
            "num_sims": num_sims,
            "conferences": conferences_list
        }


def save_predictions_json(predictions, output_file):
    prediction_json = []
    for prediction in predictions:
        p = Prediction(*prediction)
        prediction_json.append(p.__dict__)
    prediction_json = {"predictions": prediction_json}
    with open(output_file, 'w') as fp:
        json.dump(prediction_json, fp)


def save_simulation(num_sims, results_dict, points_dict, output_file):
    simulation = Simulation(num_sims, results_dict, points_dict).__dict__
    with open(output_file, 'w') as fp:
        json.dump(simulation, fp)


def save_json(json_data, output_file):
    with open(output_file, 'w') as fp:
        json.dump(json_data, fp)
