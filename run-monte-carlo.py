import os
from predictor import Predictor
from conferences import CONFERENCES
from monte_carlo_simulation import start_simulations, NUM_SIMS
from save_json import Simulation, save_simulation


def main():
    predictor = Predictor()
    results_dict = {}
    points_dict = {}

    for conference in CONFERENCES:
        results, points, num_sims = start_simulations(predictor, conference)
        results_dict[conference] = results
        points_dict[conference] = points
    save_simulation(NUM_SIMS, results_dict, points_dict, 'simulations/simulation.json')


if __name__ == "__main__":
    if not os.path.exists('simulations'):
        os.makedirs('simulations')
    main()
