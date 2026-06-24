# api/views.py
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated 
from expenses.utils import predict_category_from_text
from .serializers import YourDataSerializer  


class PredictCategory(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        user_input = request.data.get('description', '')
        
        if not user_input:
            return Response({'predicted_category': 'Other'}, status=status.HTTP_200_OK)
        
        # Use the ML model from utils.py - NO training, NO dataset reload
        predicted_category = predict_category_from_text(user_input)

        return Response({'predicted_category': predicted_category}, status=status.HTTP_200_OK)


class UpdateDataset(APIView):
    # permission_classes = [IsAuthenticated]

    def post(self, request):
       new_data = request.data.get('new_data')

       if 'description' in new_data and 'category' in new_data:
            # Load your existing dataset
            data = pd.read_csv('dataset.csv')  # Load the existing dataset
            new_category = new_data['category']
            new_description = new_data['description']

            # Append the new data to the dataset
            new_row = {'description': new_description, 'category': new_category, 'clean_description': preprocess_text(new_description)}
            data = pd.concat([data, pd.DataFrame([new_row])], ignore_index=True)
            # Save the updated dataset
            data.to_csv('dataset.csv', index=False)
            
            # Note: Model retraining would require reloading the module or 
            # implementing a proper model management strategy
            return Response({'status': 'Dataset updated. Please restart server to retrain model.'}, status=status.HTTP_200_OK)

       return Response({'error': 'Invalid data'}, status=status.HTTP_400_BAD_REQUEST)


def preprocess_text(text):
    from nltk.tokenize import word_tokenize
    from nltk.corpus import stopwords
    import nltk
    
    nltk.download('punkt', quiet=True)
    nltk.download('stopwords', quiet=True)
    
    stop_words = set(stopwords.words('english'))
    tokens = word_tokenize(text.lower())
    tokens = [t for t in tokens if t.isalnum() and t not in stop_words]
    return ' '.join(tokens)
