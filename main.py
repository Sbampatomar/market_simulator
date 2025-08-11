# main.py
import argparse
from logger_setup import setup_logger
from simulation import run_simulation

def parse_args():
    parser = argparse.ArgumentParser(description="Run investment portfolio simulation")
    parser.add_argument('--start-date', type=str, help='Simulation start date (YYYY-MM-DD)')
    parser.add_argument('--end-date', type=str, help='Simulation end date (YYYY-MM-DD)')
    parser.add_argument('--threshold', type=str, help='Dividend reinvestment threshold (e.g., "250")')
    return parser.parse_args()

if __name__ == "__main__":
    setup_logger()
    args = parse_args()
    run_simulation(
        start_date=args.start_date,
        end_date=args.end_date,
        reinvestment_threshold=args.threshold
    )