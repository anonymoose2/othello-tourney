from django.contrib.auth.views import LogoutView
from django.shortcuts import render
from django.urls import path

app_name = "auth"


def default(request):
    return render(request, f"auth/{request.resolver_match.url_name}.html")


urlpatterns = [
    path("error/", default, name="error"),
    path("", default, name="index"),
    path("login/", default, name="login"),
    path("logout/", LogoutView.as_view(), name="logout"),
]
