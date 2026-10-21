# ─────────────────────────────────────────────────
# SmartBuy Planner — Model Training Script
# Run this once to train all 3 price prediction models
# ─────────────────────────────────────────────────

from prophet import Prophet
import pandas as pd
import pickle

products = {
    'boat':   'boat_price_history.csv',
    'nike':   'nike_price_history.csv',
    'iphone': 'iphone_price_history.csv'
}

for name, file in products.items():
    print(f"\n⏳ Training {name} model...")
    try:
        df = pd.read_csv(file)
        df.columns = ['ds', 'y']
        df['ds'] = pd.to_datetime(df['ds'])

        model = Prophet(
            daily_seasonality=False,
            weekly_seasonality=True,
            yearly_seasonality=True,
            changepoint_prior_scale=0.05
        )
        model.fit(df)

        with open(f'{name}_model.pkl', 'wb') as f:
            pickle.dump(model, f)

        print(f"✅ {name} model trained and saved as {name}_model.pkl")

    except FileNotFoundError:
        print(f"❌ {file} not found. Make sure CSV files are in the same folder.")

print("\n🎉 All models ready! Now run: python app.py")
