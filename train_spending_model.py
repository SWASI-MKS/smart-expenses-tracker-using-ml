import pandas as pd
from sklearn.ensemble import IsolationForest
import joblib

# Load dataset
df = pd.read_csv("expense_tracker_dataset.csv")

# Use amount as the main feature for spending behavior
X = df[["amount"]]

# Train anomaly detection model
model = IsolationForest(contamination=0.05, random_state=42)
model.fit(X)

# Save the model
joblib.dump(model, "spending_model.pkl")

print("Model trained successfully")
print("Model saved as spending_model.pkl")