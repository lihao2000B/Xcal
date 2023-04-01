import sys
import tempfile
import msoffcrypto

workbook_file_path = "123.xlsx"    

with open(workbook_file_path, "rb") as fin,\
    tempfile.TemporaryFile() as tfp:
    encrypted = msoffcrypto.OfficeFile(fin)
    with open("data.in", "r") as f:
        passwords = f.read()
        password_list = passwords.split(" ")

    for password in password_list:
        try: 
            encrypted.load_key(password=password)
            encrypted.decrypt(tfp)
            print(password + "accept !!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!")
            sys.exit(0)
        except Exception:
            pass
    
    sys.exit(1)

