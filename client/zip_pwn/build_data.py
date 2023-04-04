import itertools
import sys

with open("data.in", 'w+') as file:
    sys.stdout = file
    l = 1
    r = 1000000
    while True:
        if r > 99999999:
            r = 99999999
            print(l,r,end="")
            break
        print(l,r,end=" ")
        l=r+1
        r=r+1000000
        