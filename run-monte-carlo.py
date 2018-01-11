import os
from predictor import Predictor
from conferences import CONFERENCES
from monte_carlo_simulation import start_simulations, NUM_SIMS
from save_json import Simulation, save_simulation


def main():
    predictor = Predictor()
    results_dict = {}

    for conference in CONFERENCES:
        results = start_simulations(predictor, conference)
        results_dict[conference] = results
    save_simulation(NUM_SIMS, results_dict, 'simulations/simulation.json')


if __name__ == "__main__":
    if not os.path.exists('simulations'):
        os.makedirs('simulations')
    main()
