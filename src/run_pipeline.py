"""Run the full pipeline: download -> clean -> analyse -> figures.

    python src/run_pipeline.py               # download fresh data from the API
    python src/run_pipeline.py --offline     # reuse the raw files in data/raw/
"""

import argparse

import clean_data
import download_data
import make_figures
import statistical_analysis

if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--offline", action="store_true", help="skip the download and use the existing data/raw files")
    args = ap.parse_args()
    if not args.offline:
        download_data.main()
    clean_data.main()
    statistical_analysis.run_all()
    make_figures.main()
    print("Pipeline finished.")
