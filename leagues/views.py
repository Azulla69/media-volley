from django.shortcuts import render, get_object_or_404
from .models import Championship


def championship_list(request):
    championships = Championship.objects.filter(is_active=True)
    return render(request, 'leagues/list.html', {'championships': championships})


def championship_detail(request, pk):
    championship = get_object_or_404(Championship, pk=pk, is_active=True)
    teams = championship.teams.all()
    matches = championship.matches.all()[:10]
    photos = championship.photos.all()
    return render(request, 'leagues/detail.html', {
        'championship': championship,
        'teams': teams,
        'matches': matches,
        'photos': photos,
    })