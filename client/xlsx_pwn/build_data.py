import itertools
import sys

with open("data.in", 'w+') as file:
    sys.stdout = file
    for i in range(0,10000000):
        data = str(i).zfill(6)
        print(data,end=" ")
        