from django.shortcuts import render, HttpResponse

# Create your views here.


def homepage(request):
    return render(request, template_name='data_assist/index.html')


def query(request):
    return render(request, template_name='data_assist/query.html')


def diagnose(request):
    return render(request, template_name='data_assist/diagnose.html')