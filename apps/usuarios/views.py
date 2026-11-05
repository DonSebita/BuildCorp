from django.contrib.auth import views as auth_views


class LoginView(auth_views.LoginView):
    template_name = "registration/login.html"
    redirect_authenticated_user = True
