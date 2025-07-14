from django.shortcuts import render, get_object_or_404
from django.contrib.auth.decorators import login_required
from .models import Message


@login_required
def message_list(request):
    messages = Message.objects.filter(recipient=request.user).order_by('-created_at')
    return render(request, 'messaging/list.html', {'messages': messages})


@login_required
def compose_message(request):
    return render(request, 'messaging/compose.html')


@login_required
def message_detail(request, pk):
    message = get_object_or_404(Message, pk=pk, recipient=request.user)
    return render(request, 'messaging/detail.html', {'message': message})
