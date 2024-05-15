from random import *
from datetime import date, datetime
import tkinter
import random
import time

random.seed(time.time())

def lotto_num():
    today = date.today()
    lotto_num_box.delete(0, tkinter.END)

    total = []
    lotto_number = list(range(1, 46))

    # 1.
    first_numbers = sorted(sample(lotto_number, 6))
    total.append(first_numbers)
    lotto_num_box.insert("end", "")
    lotto_num_box.insert("end", "*" * 50)
    lotto_num_box.insert("end", f"First numbers: {', '.join(map(str, first_numbers))}")

    # Update lotto_number by removing first_numbers
    first_numbers_set = set(first_numbers)
    lotto_number = [num for num in lotto_number if num not in first_numbers_set]

    # 2.
    second_numbers = sorted(sample(lotto_number, 6))
    total.append(second_numbers)
    lotto_num_box.insert("end", f"Second numbers: {', '.join(map(str, second_numbers))}")

    # Update lotto_number by removing second_numbers
    second_numbers_set = set(second_numbers)
    lotto_number = [num for num in lotto_number if num not in second_numbers_set]

    # 3.
    third_numbers = sorted(sample(lotto_number, 6))
    total.append(third_numbers)
    lotto_num_box.insert("end", f"Third numbers: {', '.join(map(str, third_numbers))}")

    # Update lotto_number by removing third_numbers
    third_numbers_set = set(third_numbers)
    lotto_number = [num for num in lotto_number if num not in third_numbers_set]

    # 4.
    fourth_numbers = sorted(sample(lotto_number, 6))
    total.append(fourth_numbers)
    lotto_num_box.insert("end", f"Fourth numbers: {', '.join(map(str, fourth_numbers))}")
    lotto_num_box.insert("end", "")

    # 24 numbers
    total_numbers = sorted([single_nums for each_row in total for single_nums in each_row])
    total_str = ', '.join(map(str, total_numbers))
    total_length = len(total_str)

    if total_length <= 50:
        lotto_num_box.insert("end", f"Total: {total_str}")
    else:
        first_line = total_str[:50]
        second_line = total_str[50:]

    lotto_num_box.insert("end", f"Total 24 numbers: ")
    lotto_num_box.insert("end", f"{first_line}")
    lotto_num_box.insert("end", f"{second_line}")
    lotto_num_box.insert("end", "*" * 50)
    lotto_num_box.insert("end", "")
    lotto_num_box.insert("end", f"{today}")

    # Generating winners
    for i in range(6):
        lotto_number = list(range(1, 46))
        winner_numbers = sample(lotto_number, 6)
        winner_numbers = sorted(winner_numbers)
        winner_numbers = map(str, winner_numbers)
        winner_numbers = ", ".join(winner_numbers)
        lotto_num_box.insert(i, f"{[i+1]}회:  {winner_numbers}")

    lotto_num_box.insert("end", "")

window = tkinter.Tk()
window.geometry("500x600")
window.resizable(False, False)
window.title("Saturday Lotto Generator")

label = tkinter.Label(window, text="Saturday Lotto Generator", font=("Bold", 12), height=2)
label.pack()

lotto_num_box = tkinter.Listbox(window, selectmode="extended", activestyle="none", font=("Bold", 12), width=48, height=24)
lotto_num_box.insert(0, "아래 버튼을 클릭하세요")
lotto_num_box.pack()

button = tkinter.Button(window, text="Click for Numbers", font=("Bold", 10), command=lotto_num)
button.pack(pady=20)

window.mainloop()
