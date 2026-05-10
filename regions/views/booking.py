from django.shortcuts import redirect


def region_booking(request, region_slug):
    return redirect(f'/{region_slug}/inquiry/')
