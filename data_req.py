from pytrends.request import TrendReq
import pandas as pd
import requests
from models import Product, Category, forcasting_value
from models import db
from datetime import datetime, timedelta
import requests_cache
from retry_requests import retry

# Initialize Pytrends
pytrends = TrendReq()
cache_session = requests_cache.CachedSession('.cache', expire_after=-1)
retry_session = retry(cache_session, retries=5, backoff_factor=0.2)


class data_Request:
    def __init__(self, product_id):
        self.product_id = product_id

        today = datetime.today() - timedelta(days=1)  # Adjust to prevent API range error
        first_day_of_current_month = today.replace(day=1)
        first_day_of_last_month = (first_day_of_current_month - timedelta(days=1)).replace(day=1)
        self.last_month = first_day_of_last_month.strftime('%Y-%m-%d')
        self.current_month = first_day_of_current_month.strftime('%Y-%m-%d')
        self.timeframe = f"{first_day_of_last_month.strftime('%Y-%m-%d')} {today.strftime('%Y-%m-%d')}"

    def get_weather_data(self):
        try:
            start_date, end_date = self.timeframe.split()

            latitude = 22.57
            longitude = 88.36
            timezone = "Asia/Kolkata"

            weather_url = "https://archive-api.open-meteo.com/v1/archive"
            weather_params = {
                "latitude": latitude,
                "longitude": longitude,
                "start_date": start_date,
                "end_date": end_date,
                "daily": ["temperature_2m_max", "rain_sum"],
                "timezone": timezone,
            }

            weather_response = requests.get(weather_url, params=weather_params)
            if weather_response.status_code != 200:
                raise Exception(f"Weather API error: {weather_response.status_code}")

            weather_data = weather_response.json()
            if not weather_data or 'daily' not in weather_data or not weather_data['daily']:
                raise Exception("Invalid or empty weather data received")

            df_weather = pd.DataFrame(weather_data['daily'])
            print(f"Weather data fetched:\n{df_weather}")

            df_weather['time'] = pd.to_datetime(df_weather['time'])
            df_weather['month'] = df_weather['time'].dt.to_period('M')

            monthly_data = df_weather.groupby('month').agg({
                    'temperature_2m_max': 'mean',
                    'rain_sum': 'mean',
                }).reset_index()
            
            monthly_data['month'] = monthly_data['month'].dt.to_timestamp()
            print(monthly_data)
            for idx, row in monthly_data.iterrows():
                time = row['month']
                fv = forcasting_value.query.filter_by(product_id=self.product_id, time=time).first()
                if fv:
                    print(fv.temp , fv.rain)
                    fv.temp = row['temperature_2m_max']
                    fv.rain = row['rain_sum']
                    db.session.commit()
                    print(f"Updated forecasting data for {time} , temp = {fv.temp} , rain = {fv.rain}")
        except Exception as e:
            print(f"Error while fetching weather data: {e}")     

    def trend_data(self):
        try:    
            product = Product.query.filter_by(id=self.product_id).first()
            if not product:
                raise Exception(f"Product {self.product_id} not found")

            c = Category.query.filter_by(id=product.category_id).first()
            if not c:
                raise Exception(f"Category not found for Product {self.product_id}")

            keyword = c.category_name  # Use category name as keyword
            print(f"Fetching trends for product {product.id} ({keyword})...")

            pytrends.build_payload(kw_list=[keyword], timeframe=self.timeframe, geo='IN')
            trends = pytrends.interest_over_time()
            if trends.empty:
                raise Exception(f"No trend data available for {keyword}")

            trends['date'] = trends.index
            print(trends.head())  # Display first few rows

            trends['date'] = pd.to_datetime(trends['date'])
            trends['month'] = trends['date'].dt.to_period('M')

            monthly_data = trends.groupby('month').agg({
                keyword: 'mean'
            }).reset_index()

            monthly_data['month'] = monthly_data['month'].dt.to_timestamp()
            print(monthly_data)

            for idx, row in monthly_data.iterrows():
                time = row['month']
                fv = forcasting_value.query.filter_by(product_id=self.product_id, time=time).first()
                if fv:
                    print(f"Updating trend value for {time} ({keyword})...")
                    fv.trend_value = row[keyword]
                    db.session.commit()
                    print(f"Updated forecasting data for {time}: {fv.trend_value}")
                else:
                    print(f"No forecasting record found for Product ID {self.product_id} at {time}")

        except Exception as e:
            print(f"Error while fetching trend data for Product ID {self.product_id}: {e}")
            

        



# if __name__ == "__main__":
#     with app.app_context():
        # product_id = 1
        # request = Request(product_id)
        # request.trend_data()
        # request.get_weather_data()
        
