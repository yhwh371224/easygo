import time
import random

random.seed(time.time())

print("How many total numbers you like to choose?")
c = input()
print('')

# 24 numbers
numbers = list(range(1, 48))
numbers_picked = random.sample(numbers, int(c))
numbers_picked.sort()
print(numbers_picked)
print('')

numbers_shuffled = random.shuffle(numbers_picked)

print('How many games would you like to play?')
n = input()
print('')

print('Please find your numbers below, Good luck!')
print('')

for i in range(int(n)):
    winner_numbers = random.sample(numbers_shuffled, 7)
    winner_numbers.sort()
    print(f"{i+1}회: {winner_numbers}")
    print('')
