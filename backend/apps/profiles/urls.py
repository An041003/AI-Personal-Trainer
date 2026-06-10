from django.urls import path

from .views import DashboardGreetingView, ProfileAdviceView, ProfileView, ProfileWeatherView


urlpatterns = [
    path("", ProfileView.as_view(), name="profile"),
    path("advice/", ProfileAdviceView.as_view(), name="profile-advice"),
    path("dashboard-greeting/", DashboardGreetingView.as_view(), name="profile-dashboard-greeting"),
    path("weather/", ProfileWeatherView.as_view(), name="profile-weather"),
]
