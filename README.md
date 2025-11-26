# Portfolio Tracker
This project is a Flask web application for tracking an investment portfolio. It supports uploading CSV exports from brokerage accounts, and provides a visualization dashboard for portfolio monitoring.

## To Run Locally

### Clone the repo
```
git clone https://github.com/shauncampbell20/portfolio-tracker.git
cd portfolio-tracker
```

### Set up environment
```
python -m venv .venv
.venv\scripts\activate
pip install -r requirments.txt
```

### Initialize the database
```
flask --app portfolio_tracker init-db
```

### Run locally
```
flask --app portfolio_tracker run
```
