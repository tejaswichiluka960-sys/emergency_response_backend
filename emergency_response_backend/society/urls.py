from django.urls import path
from .views import *

urlpatterns = [
    path('societies/', SocietyView.as_view()),
    path('societies/list/', SocietyListView.as_view()),
    path('societies/update/<int:pk>/', UpdateSocietyView.as_view()),
    path('societies/delete/<int:pk>/', DeleteSocietyView.as_view()),
    path('invite/', InviteUserView.as_view()),
    path('flats/', FlatView.as_view()),
    path('flats/list/', FlatListView.as_view()),
    path('flats/update/<int:pk>/', UpdateFlatView.as_view()),
    path('flats/delete/<int:pk>/', DeleteFlatView.as_view()),
    path('flats/<int:pk>/', GetFlatView.as_view()),
]


