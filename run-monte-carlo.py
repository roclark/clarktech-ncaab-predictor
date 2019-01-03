import os
from predictor import Predictor
from pymongo import MongoClient
from monte_carlo_simulation import start_simulations, NUM_SIMS
from save_json import Simulation, save_simulation
from sportsreference.ncaab.conferences import Conferences


def save_to_mongodb(simulation):
    client = MongoClient()
    db = client.clarktechsports
    # Clear all of the existing simulations and add simulation for the current
    # day
    db.conference_predictions.update_many({}, {'$set': {'latest': False}})
    post = simulation['simulation']['conferences']
    db.conference_predictions.insert_many(post)


def main():
    predictor = Predictor()
    results_dict = {}
    points_dict = {}

    for abbreviation, details in Conferences().conferences.items():
        results, points = start_simulations(predictor, details)
        results_dict[abbreviation] = {'results': results,
                                      'name': details['name']}
        points_dict[abbreviation] = {'points': points,
                                     'name': details['name']}
    simulation = save_simulation(NUM_SIMS,
                                 results_dict,
                                 points_dict,
                                 'simulations/simulation.json')
    save_to_mongodb(simulation)


if __name__ == "__main__":
    if not os.path.exists('simulations'):
        os.makedirs('simulations')
    main()
