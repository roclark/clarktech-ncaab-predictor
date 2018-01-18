import json
import os
from save_json import save_json


def read_json_stats():
    json_files = []

    for filename in os.listdir("team-stats"):
        if filename.endswith(".json"):
            with open("team-stats/%s" % filename) as json_file:
                json_files.append(json.load(json_file))
    return json_files


def parse_json_files(json_files):
    stats_dict = {}

    for json_file in json_files:
        for key in json_file:
            key = str(key)
            if key not in stats_dict:
                stats_dict[key] = {"max": json_file[key],
                                   "min": json_file[key]}
                continue
            if stats_dict[key]["max"] < json_file[key]:
                stats_dict[key]["max"] = json_file[key]
            if stats_dict[key]["min"] > json_file[key]:
                stats_dict[key]["min"] = json_file[key]
    return stats_dict


def save_stats_dict(stats_dict):
    save_json(stats_dict, "stats.json")


def main():
    json_files = read_json_stats()
    stats_dict = parse_json_files(json_files)
    save_stats_dict(stats_dict)


if __name__ == "__main__":
    main()
