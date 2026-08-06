from django.contrib.auth import login, logout
from django.contrib.auth.decorators import login_not_required
from django.contrib.auth.forms import AuthenticationForm
from django.http import HttpResponse
from django.shortcuts import render, redirect
from django.urls import reverse
from django.views.decorators.http import require_POST


@login_not_required
def landing(request):
    return render(request, 'landing.html')


@login_not_required
def login_modal(request):
    form = AuthenticationForm(request)
    return render(request, 'users/partials/login_modal.html', {'form': form})


@login_not_required
@require_POST
def login_submit(request):
    form = AuthenticationForm(request, data=request.POST)
    if form.is_valid():
        login(request, form.get_user())
        response = HttpResponse()
        response['HX-Redirect'] = reverse('vehicules:garages')
        return response
    return render(request, 'users/partials/login_modal.html', {'form': form})


@login_not_required
def modal_close(request):
    return HttpResponse('')


@require_POST
def logout_view(request):
    logout(request)
    return redirect('users:landing')
