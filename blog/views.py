from django.shortcuts import render


# error handler 400 403 404 500 502 503 
def custom_bad_request(request, exception):
    return render(request, '400.html', status=400)


def custom_forbidden(request, exception):
    return render(request, '403.html', status=403)


def custom_page_not_found(request, exception):
    return render(request, '404.html', status=404)


def custom_server_error(request):
    return render(request, '500.html', status=500)


def custom_bad_gateway(request):
    return render(request, '502.html', status=502)


def custom_under_maintenance(request):
    return render(request, '503.html', status=503)
