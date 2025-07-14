from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from .models import Wallet, Transaction


@login_required
def wallet_list(request):
    wallets = Wallet.objects.filter(user=request.user)
    return render(request, 'wallets/list.html', {'wallets': wallets})


@login_required
def deposit(request):
    return render(request, 'wallets/deposit.html')


@login_required
def withdraw(request):
    return render(request, 'wallets/withdraw.html')


@login_required
def transaction_list(request):
    transactions = Transaction.objects.filter(wallet__user=request.user).order_by('-created_at')
    return render(request, 'wallets/transactions.html', {'transactions': transactions})
