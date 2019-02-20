# The slim version of python is smaller than the Alpine version when using pandas
# and related libraries.
FROM python:3.7-slim

# Designate the working directory that code will reside at and be run from.
WORKDIR /app

# Copy the requirements now instead of re-copying after each source alteration
COPY requirements.txt /app

# Install the dependencies for the project.
# If the requirements don't change, the dependencies won't need to be re-installed.
RUN pip install -r requirements.txt

# Copy all files not listed in .dockerignore to the working directory.
COPY . /app

# Since the scripts are run in python, the 'python' entrypoint should be used to
# easily call the run script and parameters can be added at the end of the Docker
# command.
ENTRYPOINT ["python", "./run-simulator.py"]
