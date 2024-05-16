from random import *

print('How many games would you like to pick?')

n = input()

print('')

lotto_number = list(range(1, 48))
shuffle(lotto_number)

print('Oz Lotto numbers')
print('')
for i in range(int(n)):
    shuffle(lotto_number)
    winner_numbers = sample(lotto_number, 7)
    winner_numbers.sort()    
    print(f"{i+1}회: {winner_numbers}")
    print('')


