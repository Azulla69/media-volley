from django.shortcuts import render
from leagues.models import Championship


def home(request):
    championships = Championship.objects.filter(is_active=True)[:4]
    return render(request, 'core/home.html', {'championships': championships})