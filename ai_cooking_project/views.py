from django.db import connection
from django.http import JsonResponse
from django.shortcuts import render


def home(request):
    return render(request, "home.html")


def healthz(request):
    connection.ensure_connection()
    return JsonResponse({"status": "ok"})
