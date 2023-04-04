from queue import Queue
import zipfile

filename = "test8.zip"

def uncompress(file_name, pass_word):
    try:
        with zipfile.ZipFile(file_name) as z_file:
            z_file.extractall("./", pwd=pass_word.encode("utf-8"))
        return True
    except:
        return False
 
with open("data.in", "r") as f:
    data = f.read()
    range_list = data.split(" ")
    q = Queue()
    for i in range_list:
        q.put(i)
    while(not q.empty()):
        l = int(str(q.get()))
        r = int(str(q.get()))
        for fill in range(1,9):
            for num in range(l,r+1):
                str_num = str(num)
                if len(str_num)>fill:
                    break
                password = str_num.zfill(fill)
                
                result = uncompress(filename, password)
                if not result:
                    pass
                    # print('false ', password)
                else:
                    print('pass ' + password, end="")
                    break
                
