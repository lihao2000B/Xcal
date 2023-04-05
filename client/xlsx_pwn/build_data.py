import itertools
import sys

with open("data.in", 'w+') as file:
    # sys.stdout = file
    for i in range(0,10000000):
        file.write(str(i))
        data = str(i).zfill(6)
        file.write(str(i)+" ")
        # print(i,end=" ")
        