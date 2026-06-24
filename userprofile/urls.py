from django.urls import path
from . import views

urlpatterns = [
    path('', views.userprofile, name="account"),
    path('addSource/', views.addSource, name="addSource"),
    path('deleteSource/<int:id>', views.deleteSource, name="deleteSource"),
]

# Note: To fix NoReverseMatch for 'userprofile', templates should use {% url 'account' %}
# If there are templates using {% url 'userprofile' %}, they need to be updated to use {% url 'account' %}

