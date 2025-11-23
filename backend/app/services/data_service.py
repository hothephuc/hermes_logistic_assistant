import os

import pandas as pd

# Get data for shipments.csv
DATA_FILE = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
    "data",
    "shipments.csv",
)


def load_data():
    """Load shipment data from CSV."""
    try:
        df = pd.read_csv(DATA_FILE)
        # Ensure date is datetime
        df["date"] = pd.to_datetime(df["date"])
        return df
    except FileNotFoundError:
        print(f"Error: {DATA_FILE} not found.")
        return pd.DataFrame()


def get_unique_values(df, column):
    """Get unique values for a column."""
    if column in df.columns:
        return df[column].unique().tolist()
    return []
