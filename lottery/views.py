from django.shortcuts import render
import random


def lotto_form(request):
    return render(request, 'lottery/lotto_form.html')

def lotto_result(request):
    c = int(request.POST['total_numbers'])
    n = int(request.POST['games'])
    
    numbers = list(range(1, 46))
    numbers_picked = random.sample(numbers, c)
    numbers_picked.sort()

    results = []
    for i in range(n):
        winner_numbers = random.sample(numbers_picked, 6)
        winner_numbers.sort()
        results.append(f"{i+1}회: {winner_numbers}")

    return render(request, 'lottery/lotto_result.html', {'results': results})