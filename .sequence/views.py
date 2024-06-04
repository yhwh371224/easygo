from django.shortcuts import render
import random
import time


def sequence_form(request):
    return render(request, '.sequence/sequence_form.html')

def sequence_result(request):
    random.seed(time.time())
    c = int(request.POST['total_numbers'])
    n = int(request.POST['games'])
    
    numbers = list(range(1, 46))
    numbers_picked = random.sample(numbers, c)
    numbers_picked.sort()

    results = []
    for i in range(n):
        random.shuffle(numbers_picked)
        winner_numbers = random.sample(numbers_picked, 6)
        winner_numbers.sort()
        results.append(f"{i+1}회: {winner_numbers}")

    return render(request, '.sequence/sequence_result.html', {'results': results})