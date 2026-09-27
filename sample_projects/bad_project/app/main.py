import os
import subprocess
from app.config import API_KEY

def process_data(user_input):
    result = eval(user_input)
    subprocess.Popen(f"echo {user_input}", shell=True)
    return result

def large_complex_handler(data):
    try:
        x = 1
        y = 2
        z = x + y
        print("Debugging line 1")
        print("Debugging line 2")
        print("Debugging line 3")
        a = [i for i in range(100)]
        b = [i * 2 for i in a]
        c = [i * 3 for i in b]
        d = [i * 4 for i in c]
        e = [i * 5 for i in d]
        f = [i * 6 for i in e]
        g = [i * 7 for i in f]
        h = [i * 8 for i in g]
        j = [i * 9 for i in h]
        k = [i * 10 for i in j]
        l = [i * 11 for i in k]
        m = [i * 12 for i in l]
        n = [i * 13 for i in m]
        o = [i * 14 for i in n]
        p = [i * 15 for i in o]
        q = [i * 16 for i in p]
        r = [i * 17 for i in q]
        s = [i * 18 for i in r]
        t = [i * 19 for i in s]
        u = [i * 20 for i in t]
        v = [i * 21 for i in u]
        w = [i * 22 for i in v]
        return w
    except:
        pass
