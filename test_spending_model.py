import joblib
import numpy as np

# Load trained model
model = joblib.load("spending_model.pkl")

# Example transaction
test_amount = np.array([[4500]])

prediction = model.predict(test_amount)

if prediction[0] == -1:
    print("Unusual spending detected")
else:
    print("Normal transaction")