import json
from common import find_nickname_from_name
from mascots import MASCOTS


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
        prediction_json.append(prediction)
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
