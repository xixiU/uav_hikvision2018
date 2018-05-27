# -*- coding:utf-8 -*-
import sys

from UAVService import start
if __name__ == "__main__":
    if len(sys.argv) == 4:
        print("Server Host: " + sys.argv[1])
        print("Server Port: " + sys.argv[2])
        print("Auth Token: " + sys.argv[3])
        start(sys.argv[1], sys.argv[2], sys.argv[3])
        #print(ai.sayHello(demoMap))
    else:
        print("need 3 arguments")