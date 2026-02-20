from django.contrib.auth.decorators import user_passes_test

def admin_required(view_func):

    decorated_view_func = user_passes_test(
        lambda user: user.is_authenticated and user.rol == 'ADMIN',
        login_url='login'  # URL a la que se redirige si no es admin
    )(view_func)
    return decorated_view_func
