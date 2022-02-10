import csv, time
from ftplib import FTP, FTP_TLS
from datetime import datetime
while True:
 oldfileclear = open("myfilenameoutput.csv", 'w') 
 oldfileclear.close
 i=0
 with open("inputfilename.csv", newline='', encoding='utf-8') as csvfile:
    readerfile = csv.reader(csvfile, delimiter=';')
    for row in readerfile:
        if i == 0 or row[3] == 'Name Exchange' or row[3] == 'Name Exchange' or row[3] == 'Name Exchange' or row[3] == 'Name Exchange':
            fildnames = row
            with open("myfilenameoutput.csv", 'a', newline='', encoding='utf-8') as csvfiledealer:
                writefile = csv.writer(csvfiledealer, delimiter=';')
                writefile.writerow(fildnames)
        else:
            if row[4] == 'NULL' or 2 > int(float(row[4])):
                row.pop(4)
                row.insert(4, 'None')
            elif 5 >= int(float(row[4])) >= 2:
                row.pop(4)
                row.insert(4, '2-5 inch')
            elif 10 >= int(float(row[4])) >= 6:
                row.pop(4)
                row.insert(4, '6-10 inch')
            elif int(float(row[4])) >= 10:
                row.pop(4)
                row.insert(4, '> 10 inch')
            newrow = row
            with open("myfilenameoutput.csv", 'a', newline='', encoding='utf-8') as csvfiledealer:
                writefile = csv.writer(csvfiledealer, delimiter=';')
                writefile.writerow(newrow)
        i += 1
        csvfiledealer.close
 current_datetime = datetime.now()
 print(current_datetime, " Well Done! CSV Complete!")
 ftps = FTP_TLS(input("Server FTP TLS: "))
 ftps.login(input("Login FTP Server: "), input("Password FTP Server: "))
 otherfile1 = "otherfile1.csv"
 otherfile2 = "otherfile2.csv"
 otherfile3 = "otherfile3.csv"
 myfilenameoutput = "myfilenameoutput.csv"
 with open(otherfile1, "rb") as file:
  ftps.storbinary(f"STOR {otherfile1}", file)
 with open(otherfile2, "rb") as file:
  ftps.storbinary(f"STOR {otherfile2}", file)
 with open(otherfile3, "rb") as file:
  ftps.storbinary(f"STOR {otherfile3}", file)
 with open(myfilenameoutput, "rb") as file:
  ftps.storbinary(f"STOR {myfilenameoutput}", file)
 ftps.quit()
 print(current_datetime, " Files uploaded! Wait 600 seconds ...")
 time.sleep(600)
