import hashlib, random
L = str(random.randint(8, 888))
md5_hash = hashlib.md5()
a_file = open("image.jpg", "ab")
for item in L:
    s = str(item) + '\n'
    bt = s.encode()
    a_file.write(bt)
a_file.close()
a_file = open("image.jpg", "rb")
content = a_file.read()
md5_hash.update(content)
digest = md5_hash.hexdigest()
print(digest)
