import os
import threading


protocols = [1034, 2535]
depth = [0, 3]


def gen(p,d):
    os.system(f"python main.py {p} --depth={d}")

if __name__ == '__main__':
    threads = []
    for p in protocols:
        for d  in depth:
            th = threading.Thread(target=gen,args=(p,d))
            th.start()
            threads.append(th)
    
    for th in threads:
        th.join()