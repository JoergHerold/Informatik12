# starter activity sheet 5

from turtle import *

    
def small_square():
    for counter in range(4):
        forward(50)
        right(90)

def large_square():
    for counter in range(4):
        forward(150)
        right(90)

def any_square(length):
    for counter in range(4):
        forward(length)
        right(90)
    
def main():
    small_square()
    large_square()
    length = int(input("Enter length of the square   "))
    any_square(length)

    
main()
