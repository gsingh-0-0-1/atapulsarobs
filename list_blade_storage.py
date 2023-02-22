import os

DATA_DIRECTORY = "/mnt/datac-netStorage-40G/blade/"

SUBDIRS = os.listdir(DATA_DIRECTORY)

SUBDIRS = [el for el in SUBDIRS if "J" in el]

missing = 0
present = 0

for subdir in SUBDIRS:
    listing = os.listdir(os.path.join(DATA_DIRECTORY, subdir))
    found = False
    for el in listing:
        if "spliced" in el and "fil" in el:
            print(subdir + ":\tFound spliced fil files(s)")
            found = True
    
    if found:
        present += 1
        continue
    else:
        missing += 1
        print(subdir + ":\tNO SPLICED FIL FILES FOUND")



print(str(missing) + " directories missing spliced filterbank files.")
print(str(present) + " directories containing spliced filterbank files.")

