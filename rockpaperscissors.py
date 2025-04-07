import random

options = ["rock", "paper", "scissors"]

rock = '''
    _______
---'   ____)
      (_____)
      (_____)
      (____)
---.__(___)
'''

paper = '''
    _______
---'   ____)____
          ______)
          _______)
         _______)
---.__________)
'''

scissors = '''
    _______
---'   ____)____
          ______)
       __________)
      (____)
---.__(___)
'''

computer_select = random.randint(0,2)

human = int(input("What do you choose? 0 for rock, 1 for paper, 2 for scissors: "))

print (f"Computer selected {options[computer_select]}\n")
if computer_select == 0 and human == 1:
    print ("Human Wins")
elif computer_select == 1 and human == 0:
    print("Computer Wins")
elif computer_select == 0 and human == 2:
    print ("Computer Wins")
elif computer_select == 2 and human == 0:
    print ("Human Wins")
elif computer_select == 1 and human == 2:
    print ("Human Wins")
elif computer_select == 2 and human == 1:
    print ("Computer Wins")
else:
    print ("empate")
