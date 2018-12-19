import os
from predictor import Predictor
from monte_carlo_simulation import start_simulations, NUM_SIMS
from save_json import Simulation, save_simulation
from sportsreference.ncaab.conferences import Conferences


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
    save_simulation(NUM_SIMS, results_dict, points_dict, 'simulations/simulation.json')


if __name__ == "__main__":
    if not os.path.exists('simulations'):
        os.makedirs('simulations')
    main()
