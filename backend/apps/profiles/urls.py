from django.urls import path

from .views import ProfileAdviceView, ProfileView


urlpatterns = [
    path("", ProfileView.as_view(), name="profile"),
    path("advice/", ProfileAdviceView.as_view(), name="profile-advice"),
]

