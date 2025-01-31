from models import db
import numpy as np
from models import Product, Category, forcasting_value
from datetime import datetime , timedelta
import pandas as pd
from sklearn.preprocessing import MinMaxScaler
from statsmodels.tsa.statespace.sarimax import SARIMAX

class Forecast:
    def __init__(self, product_id):
        self.product_id = product_id

    def trend_data(self):
        forcasting_db = forcasting_value.query.filter_by(product_id=self.product_id).all()
        data = [{
            "time": db.time,
            "temp": db.temp,
            "rain": db.rain,
            "trend_value": db.trend_value
        } for db in forcasting_db]

        df = pd.DataFrame(data)
        df["time"] = pd.to_datetime(df["time"])  # Convert 'time' to datetime

        # Get today's date and the first day of the current month
        today = datetime.today() 
        first_day_of_current_month = today.replace(day=1)
        print("First Day of Current Month:", first_day_of_current_month)

        # Split data into historical and future
        historical_df = df[df["time"] < first_day_of_current_month]
        future_df = df[df["time"] >= first_day_of_current_month]

        historical_df.set_index('time', inplace=True)  # Fixing incorrect indexing
        future_df.set_index('time', inplace=True)

        print("Historical Data:\n", historical_df)
        print("\nFuture Exogenous Data:\n", future_df)

        # Scaling the features
        scaler = MinMaxScaler()
        scaled_features = scaler.fit_transform(historical_df[['temp', 'rain', 'trend_value']])
        historical_df[['temp', 'rain', 'trend_value']] = scaled_features

        # Prepare endogenous & exogenous variables
        endog = historical_df['trend_value']
        exog = historical_df[['temp', 'rain']]

        # SARIMAX Model
        sarimax_model = SARIMAX(endog, exog=exog, order=(1, 1, 1), seasonal_order=(1, 1, 1, 12))
        results = sarimax_model.fit(disp=0)  # Corrected `disp=False` to `disp=0`

        # Forecasting using actual future exogenous data
        if not future_df.empty:
            future_exog = future_df[['temp', 'rain']]
        else:
            # If no future data is available, replicate the last known values
            last_exog_values = exog.iloc[[-1]].values
            future_exog = pd.DataFrame(
                np.tile(last_exog_values, (12, 1)), 
                columns=exog.columns
            )

        # Scale future exogenous data using the same scaler
        future_exog_scaled = scaler.transform(
            np.column_stack([future_exog, np.zeros((len(future_exog), 1))])
        )[:, :-1]  # Exclude the extra column

        forecast_scaled = results.get_forecast(steps=len(future_exog), exog=future_exog_scaled)
        forecast_mean_scaled = forecast_scaled.predicted_mean.to_numpy().reshape(-1, 1)

        # Inverse transform correctly
        forecast_mean_actual = scaler.inverse_transform(
            np.column_stack((future_exog, forecast_mean_scaled))
        )[:, -1]  # Extract only the forecasted `trend_value`

        print("\nNext Forecast for Available trend Future Data:")
        for i, (date, forecast) in enumerate(zip(future_df.index, forecast_mean_actual), 1):
            print(f"{date.strftime('%Y-%m-%d')}: {forecast:.2f}")
            fv = forcasting_value.query.filter_by(time= date.strftime('%Y-%m-%d'),product_id=self.product_id).first()
            if fv:
                fv.trend_value = forecast//1
                db.session.commit()
                


    def forcast_data(self):
        forcasting_db = forcasting_value.query.filter_by(product_id=self.product_id).all()
        data = [{
            "time": db.time,
            "temp": db.temp,
            "rain": db.rain,
            "trend_value": db.trend_value,
            "original_value": db.original_value
        } for db in forcasting_db]

        df = pd.DataFrame(data)
        df["time"] = pd.to_datetime(df["time"])  # Convert 'time' to datetime

        # Get today's date and the first day of the current month
        today = datetime.today() 
        first_day_of_current_month = today.replace(day=1)
        print("First Day of Current Month:", first_day_of_current_month)

        # Split data into historical and future
        historical_df = df[df["time"] < first_day_of_current_month]
        future_df = df[df["time"] >= first_day_of_current_month]

        
        historical_df.set_index('time', inplace=True)  # Fixing incorrect indexing
        future_df.set_index('time', inplace=True)

        # Scaling the features
        scaler = MinMaxScaler()
        scaled_features = scaler.fit_transform(historical_df[['temp', 'rain', 'trend_value' , 'original_value']])
        historical_df[['temp', 'rain', 'trend_value','original_value']] = scaled_features

        # Prepare endogenous & exogenous variables
        endog = historical_df['original_value']
        exog = historical_df[['temp', 'rain', 'trend_value']]

        # SARIMAX Model
        sarimax_model = SARIMAX(endog, exog=exog, order=(1, 1, 1), seasonal_order=(1, 1, 1, 12))
        results = sarimax_model.fit(disp=0)  # Corrected `disp=False` to `disp=0`

        # Forecasting using actual future exogenous data
        if not future_df.empty:
            future_exog = future_df[['temp', 'rain', 'trend_value']]
        else:
            # If no future data is available, replicate the last known values
            last_exog_values = exog.iloc[[-1]].values
            future_exog = pd.DataFrame(
                np.tile(last_exog_values, (12, 1)), 
                columns=exog.columns
            )

        # Scale future exogenous data using the same scaler
        future_exog_scaled = scaler.transform(
            np.column_stack([future_exog, np.zeros((len(future_exog), 1))])
        )[:, :-1]  # Exclude the extra column

        forecast_scaled = results.get_forecast(steps=len(future_exog), exog=future_exog_scaled)
        forecast_mean_scaled = forecast_scaled.predicted_mean.to_numpy().reshape(-1, 1)

        # Inverse transform correctly
        forecast_mean_actual = scaler.inverse_transform(
            np.column_stack((future_exog, forecast_mean_scaled))
        )[:, -1]  # Extract only the forecasted `trend_value`

        # Now iterate and print
        print("\nNext Forecast for Available Future Data:")
        for i, (date, forecast) in enumerate(zip(future_df.index, forecast_mean_actual), 1):

            print(f"{date.strftime('%Y-%m-%d')}: {forecast:.2f}")
            fv = forcasting_value.query.filter_by(time= date.strftime('%Y-%m-%d'),product_id=self.product_id).first()
            if fv:
                fv.forecasting_value = forecast//1
                db.session.commit()
            
                




# Running the forecast within the app context
# with app.app_context():
#     products = Product.query.join(Category).filter(Category.store_id == 1).all()
#     for product in products:
#         forecast = Forecast(product.id)
#         forecast.trend_data()
#         forecast.forcast_data()
