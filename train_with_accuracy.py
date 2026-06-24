import pandas as pd
from sklearn.ensemble import IsolationForest
from sklearn.metrics import accuracy_score
import joblib

# Load dataset
df = pd.read_csv("expense_tracker_dataset.csv")

# Feature
X = df[["amount"]]

# Create labels (for evaluation)
df["label"] = df["amount"].apply(lambda x: -1 if x > 2000 else 1)

y_true = df["label"]

# Train model
model = IsolationForest(contamination=0.1, random_state=42)
model.fit(X)

# Predict
y_pred = model.predict(X)

# Calculate accuracy
accuracy = accuracy_score(y_true, y_pred)

print("Model Accuracy:", round(accuracy*100,2), "%")

# Save model
joblib.dump(model,"spending_model.pkl")




