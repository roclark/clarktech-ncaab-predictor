import json


class Prediction:
    def __init__(self, tags, home_name, home_nickname, away_name, away_nickname,
                 winner, loser):
        self.prediction = {
            "tags": tags,
            "teams": {
                "home": {
                    "name": home_name,
                    "nickname": home_nickname,
                },
                "away": {
                    "name": away_name,
                    "nickname": away_nickname,
                }
            },
            "prediction": {
                "winner": winner,
                "loser": loser,
            }
        }


def save_json(predictions, output_file):
    prediction_json = []
    for prediction in predictions:
        p = Prediction(*prediction)
        prediction_json.append(p.__dict__)
    prediction_json = {"predictions": prediction_json}
    with open(output_file, 'w') as fp:
        json.dump(prediction_json, fp)