from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from .models import SupportTicket


def support_home(request):
    return render(request, 'support/home.html')


@login_required
def ticket_list(request):
    tickets = SupportTicket.objects.filter(user=request.user).order_by('-created_at')
    return render(request, 'support/tickets.html', {'tickets': tickets})


@login_required
def create_ticket(request):
    return render(request, 'support/create_ticket.html')


@login_required
def submit_feedback(request):
    return render(request, 'support/feedback.html')
