import pandas as pd
from sklearn.linear_model import LinearRegression
import numpy as np
from datetime import timedelta

def predict_delay(df):
    """
    Predict average delay for the next week using Linear Regression.
    """
    if df.empty:
        return "No data available for prediction."

    # Prepare data
    # We will use 'day of year' as feature for simplicity in this prototype
    df['day_of_year'] = df['date'].dt.dayofyear
    
    # Group by date to get daily average delay
    daily_avg = df.groupby('day_of_year')['delay_minutes'].mean().reset_index()
    
    X = daily_avg[['day_of_year']]
    y = daily_avg['delay_minutes']
    
    if len(X) < 2:
         return "Not enough data points for prediction."

    # Train model
    model = LinearRegression()
    model.fit(X, y)
    
    # Predict for next 7 days
    last_day = df['day_of_year'].max()
    next_week_days = [last_day + i for i in range(1, 8)]
    X_pred = pd.DataFrame(next_week_days, columns=['day_of_year'])
    
    predictions = model.predict(X_pred)
    avg_predicted_delay = predictions.mean()
    
    return f"{avg_predicted_delay:.2f}"
