import time
import random

random.seed(time.time())

total = []

lotto_number = list(range(1, 46))

# 1. 
first_numbers = random.sample(lotto_number, 6)
total.append(first_numbers)
print(first_numbers)
print('*'*25)
first_remaining_numbers = [num for num in lotto_number if num not in first_numbers]

# 2. 
second_numbers = random.sample(first_remaining_numbers, 6)
total.append(second_numbers)
print(second_numbers)
print('*'*25)
second_remaining_numbers = [num for num in first_remaining_numbers if num not in second_numbers]

# 3
third_numbers = random.sample(second_remaining_numbers, 6)
total.append(third_numbers)
print(third_numbers)
print('*'*25)
third_remaining_numbers = [num for num in second_remaining_numbers if num not in third_numbers]

# 4
fourth_numbers = random.sample(third_remaining_numbers, 6)
total.append(fourth_numbers)
print(fourth_numbers)
print('*'*25)
print('*'*25)
# 24개의 번호들을 확인하기
total_numbers = [single_nums for each_row in total for single_nums in each_row]
total_numbers.sort()
print(total_numbers)
print('*'*25)

print('How many games would you like to pick?')

n = input()

print('Please find your random numbers in',
      n, 'games as you picked. Good luck!')

for i in range(int(n)):
    winner_numbers = random.sample(total_numbers, 6)
    winner_numbers.sort()
    print('Saturday Lotto numbers')
    print(winner_numbers)
    print('*'*25)




