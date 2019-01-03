import json
from mascots import MASCOTS


class Simulation:
    def __init__(self, num_sims, results_dict, points_dict):
        conferences_list = []
        for conference, standings in results_dict.items():
            teams_list = []
            conf_name = standings['name']
            for nickname, standings in standings['results'].items():
                position = standings['points'].index(max(standings['points']))
                win_prob = float(standings['points'][0]) / float(num_sims)
                seed_prob = float(standings['points'][position]) / \
                            float(num_sims)
                points = points_dict[conference]['points'][nickname]
                name = standings['name']
                mascot = MASCOTS[nickname]
                team_dict = {
                    "name": name,
                    "abbreviation": nickname,
                    "mascot": mascot,
                    "standings": standings['points'],
                    "projectedWins": float(points) / float(num_sims),
                    "seedProbability": seed_prob,
                    "winProbability": win_prob
                }
                teams_list.append(team_dict)
            conferences_list.append({'teams': teams_list,
                                     'conferenceAbbreviation': conference,
                                     'conferenceName': conf_name,
                                     'latest': True,
                                     'num_sims': num_sims})
        self.simulation = {
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
    return simulation


def save_json(json_data, output_file):
    with open(output_file, 'w') as fp:
        json.dump(json_data, fp)
