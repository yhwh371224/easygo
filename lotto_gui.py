import tkinter
from random import *


def lotto_num():

    lotto_num_box.delete(0, tkinter.END)

    for i in range(3):
        lotto_number = list(range(1, 46))
        winner_numbers = sample(lotto_number, 6)
        winner_numbers = sorted(winner_numbers)
        winner_numbers = map(str, winner_numbers)
        winner_numbers = ", ".join(winner_numbers)
        lotto_num_box.insert(i, f"{[i+1]}회:  {winner_numbers}")

window = tkinter.Tk()
window.geometry("500x500")
window.resizable(False, False)

window.title("Saturday Lotto Generator")

label = tkinter.Label(window, text="Saturday Lotto Generator", font=("Bold", 12), height=2)
label.pack()

lotto_num_box = tkinter.Listbox(window, selectmode="extended", activestyle="none", font=("Bold", 12), width=48, height=20)
lotto_num_box.insert(0, "아래 버튼을 클릭하세요")
lotto_num_box.pack()

button = tkinter.Button(window, text="Click for Numbers", font=("Bold", 10), command=lotto_num)
button.pack(pady=20)

window.mainloop()