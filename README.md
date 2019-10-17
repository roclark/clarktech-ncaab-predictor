<p align="center">
  <img src="assets/BasketballLogo.png" height="200" width="200">
</p>

# NCAAB Basketball Predictor
![Docker Pulls](https://img.shields.io/docker/pulls/roclark/clarktech-ncaab-predictor?style=flat-square)

This tool uses machine learning to predict the outcomes of NCAAB Men's
Division-I Basketball games. Included are several algorithms which can forecast
different events, such as a daily matchup simulator, conference tournament
predictor, and a preview of the NCAA tournament field.

## Setup
It is _highly_ recommended to pull the latest Docker container from Docker Hub
as this image contains a pre-populated dataset containing multiple years worth
of data as well as optimizations to the data which cannot be reproduced
retro-actively. A new image is pushed to the registry daily, so it is
recommended to setup a workflow which scans for newer images prior to running
one of the provided algorithms. To pull the latest image, first ensure Docker is
installed on your system by following the [documentation](https://docs.docker.com/install/).
Next, pull the latest image with:

```
docker pull roclark/clarktech-ncaab-predictor
```

This will download and extract the most recent image to your local machine which
can be viewed with:

```
$ docker images
REPOSITORY                          TAG      IMAGE ID       CREATED       SIZE
roclark/clarktech-ncaab-predictor   latest   0cfaab9aa82a   4 hours ago   525MB
```

### MongoDB
In addition to the pulling the predictor image from Docker Hub, it is
recommended to use MongoDB as a database to save and retrieve results for future
usage. While this isn't a strict requirement, many of the algorithms provide
better handling and verbosity when saving results into a Mongo database.
Luckily, if a Mongo database isn't already installed and configured on your
system, it is straightforward to do so with a Docker container. Simply pull the
latest image from Docker Hub, then run a container in detached mode so it will
run persistently on the host:

```
docker pull mongo
docker run -it -d mongo
```

You now have a MongoDB instance running inside a container which can be accessed
anywhere on the host using the default `mongodb` url.

If you choose to skip MongoDB, you will need to add `--skip-save-to-mongodb` to
all commands while running the application (more on usage below).

## Usage
Once setup is complete, the tool is now ready to be used to predict NCAAB
outcomes. The general usage of the application with Docker is as follows:

```
docker run --rm -it roclark/clarktech-ncaab-predictor [options] algorithm [algorithm-specific options]
```

More information on the usage can be retrieved with the following:

```
docker run --rm -it roclark/clarktech-ncaab-predictor --help
```

### Daily Simulator
The daily simulator is designed to simulate the outcome of all games scheduled
for the current day. It is suggested to run this algorithm in the morning to
retrieve a list of the scheduled games and determine which team is expected to
win. Sample text output is as follows:

```
$ docker run --rm -it roclark/clarktech-ncaab-predictor daily-simulation
Army at (4) Duke  =>  (4) Duke
George Washington at (5) Virginia  =>  (5) Virginia
Florida Gulf Coast at (10) Michigan State  =>  (10) Michigan State
```

Additional information such as the predicted spread and further details on each
team is included in the database.

### Conference Simulator
The conference simulator will forecast the remaining schedule for a conference
and, based on the existing conference standings, determine the final projected
standings as well as the likelihood a particular team will earn their projected
position and their overall probability that they will finish first. The
algorithm also displays the projected number of games the team will win in the
conference by the end of the season. This can be triggered as follows:

```
docker run --rm -it roclark/clarktech-ncaab-predictor monte-carlo-simulation
```

The output generated from this command is saved to a database which is required
as a baseline for several algorithms listed below.

### Conference Tournament Simulator
This simulator runs through each conference's post-season tournament and
predicts the overall winner and the potential route each team takes to the
finals. In order to generate the initial seeds, a forecast of the final
conference standings needs to be run prior to this algorithm using the
Conference Simulator above. Each conference has its own unique tournament format
and is handled differently, as specified in the brackets library. Run this
simulation with the following:

```
docker run --rm -it roclark/clarktech-ncaab-predictor conference-tourney-simulator
```

Prior to running the algorithm, ensure a `simulation.json` file has been
generated using the Conference Simulator above.

### Matchup
A matchup between two specific teams can be simulated with the matchup
algorithm. This will run several games between the requested teams and determine
the overall winner and the expected difference in score. Due to the difference
between playing at home and on the road, the results could vary depending on
which team is specified as the home team. For example, the following will test a
matchup between Purdue and Indiana with Purdue designated as the home team:

```
docker run --rm -it roclark/clarktech-ncaab-predictor matchup purdue indiana
```

### Power Rankings
Power rankings can be generated for all NCAA Men's Division-I basketball teams
to determine the comparative performance relative to one another. This algorithm
runs a home-and-home matchup between each team in the division and tallies the
collective spread for each team. After all simulations are complete, the team
with the highest positive spread will be the number one team overall with the
team with the second highest spread being number two, and so on. This system
works under the philosophy that the team which can beat the highest number of
teams by the highest margin is the strongest team in the league. This does not
look specifically at what a team has accomplished so far in the season, but
instead how strong they are at this point in time. The rankings can be generated
with the following:

```
docker run --rm -it roclark/clarktech-ncaab-predictor power-rankings
```

### NCAA Field Filler
The NCAA Field Filler will populate the 68-team NCAA Tournament field based on
both automatic and at-large bids. The automatic bids are identified by
simulating every conference tournament and determining the winner. These winners
will receive automatic bids to the tournament. The remaining spots will be
awarded on a priority basis based on the power rankings. The rankings need to be
generated prior to running this algorithm. Attached to each team is their
expected seed. After generating power rankings using the command above, run this
algorithm with the following:

```
docker run --rm -it roclark/clarktech-ncaab-predictor fill-ncaa-field
```

### NCAA Tournament Simulator
Lastly, the NCAA Tournament Simulator runs a simulation of the NCAA tournament.
This requires a CSV file of the expected teams and seeds in the tournament to be
used as a baseline for the bracket. An example of this CSV file is provided in
the repository. To simulate the tournament, run the following:

```
docker run --rm -it roclark/clarktech-ncaab-predictor tournament-simulator 2019-ncaa.csv
```

### Other options
In addition to the algorithms listed above, some additional options are
available.

#### Num Sims
Given the unpredictability of sports, especially with men's college basketball,
some randomness is injected into the algorithms. The randomness is generated by
applying a random variance within the league's standard deviant for every
category for each team tested on a per-simulation basis. For example, in a
single simulation, one team could have a +0.7 * STDEV improvement to their
shooting percentage, and a -0.3 * STDEV punishment to their rebounds. As this is
done on a per-simulation basis, it is recommended to increase the number of
simulations run to improve the variance of data tested and get a more accurate
view of the overall trend for each team instead of relying solely on a limited
number of varied results. Please note that while increasing the number of
simulations is recommended, every additional pass will increase the time to
completion.

#### Skip Saving to MongoDB
By default, all results will be saved to a Mongo database at a specified URL.
The results in the database provide additional context and can easily be
archived for future use as needed. If desired, this can be avoided by requesting
to skip saving to MongoDB, and results will be saved in the local directory as
applicable.
