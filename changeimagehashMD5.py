import tkinter as tk
import hashlib, random
import tkinter.filedialog
root = tkinter.Tk()
def print_path():
    fimage = tkinter.filedialog.askopenfilename(
        parent=root, initialdir='C:/Tutorial',
        title='Choose file',
        filetypes=[('png images', '.png'),
                   ('gif images', '.gif')]
        )
    print(fimage)
    L = str(random.randint(8, 888))
    md5_hash = hashlib.md5()
    a_file = open(fimage, "ab")
    for item in L:
     s = str(item) + '\n'
     bt = s.encode()
     a_file.write(bt)
    a_file.close()
    a_file = open(fimage, "rb")
    content = a_file.read()
    md5_hash.update(content)
    digest = md5_hash.hexdigest()
    print(digest)
b1 = tkinter.Button(root, text='Choose file(and random md5 hash)', command=print_path)
b1.pack(fill='x')
root.mainloop()
