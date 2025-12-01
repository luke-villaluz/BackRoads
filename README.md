# BackRoads
The Backroads API is a Python routing service that recommends scenic or alternative routes given the origin and destination coordinates using data from OpenStreetMaps. The system focuses on identifying routes that are more scenic than routes provided by popular GPS services. The goal is to provide users with routes they would not typically take, allowing them to explore the less-traveled roads of San Luis Obispo County.


## Prerequisites
- Python 3.11+
- Git, `pip`, and the ability to create virtual environments (`python -m venv` or `virtualenv`)
- No external services; everything runs offline after the first graph download

## Project Setup 
1. Clone the repository
2. Install the dependencies:

   `pip install -r requirements.txt`

3. Create virtual environment

   `python3 -m venv venv`
4. Activate environment

   Mac: `source venv/bin/activate`

   Windows: `venv\Scripts\activate`
5. Set up env file

## Running the API 
1. Run API Server at root
      ` PYTHONPATH=src uvicorn src.backroads.api.main:app --reload`
2. Access the server locally at
      http://127.0.0.1:8000/

## Project Structure 

## API EndPoints 

## About The Data
The graph of San Luis Obispo was loaded from OpenStreetMaps (OMSnx) in October 2025. 
