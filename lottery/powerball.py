import random
import time

print('How many games would you like to pick?')

n = input()

print('Please find your random numbers in',
      n, 'games as you picked. Good luck!')

print('')

random.seed(time.time())

lotto_number = list(range(1, 36))
random.shuffle(lotto_number)
lotto_numbers = random.sample(lotto_number, 28)

print('winner numbers')
for i in range(int(n)):
    random.shuffle(lotto_numbers)
    winner_numbers = random.sample(lotto_numbers, 7)
    winner_numbers.sort()    
    print(f"{i+1}회: {winner_numbers}")
    print('')

print('')

print('Powerball number')
powerball_number = list(range(1, 21))
random.shuffle(powerball_number)
powerball_numbers = random.sample(powerball_number, 11)

for i in range(int(n)):
    random.shuffle(powerball_number)
    winner_number = random.sample(powerball_number, 1)    
    print(f"{i+1}회: {winner_number}")
    print('')



