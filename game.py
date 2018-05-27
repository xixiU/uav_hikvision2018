# -*- coding: utf-8 -*-
import numpy as np
import queue
INF=-1
import pickle
d=[]

# maze = pickle.load(open('maze.pl','rb'))
class Maze(object):
    def __init__(self,maze_array,start_x,start_y,end_x,end_y,block=1):
        """
        :param maze_array: 传进来的array是np.array数据类型
        :param start_x:迷宫起点x
        :param start_y:迷宫起点y
        :param end_x:迷宫终点x
        :param end_y:迷宫终点y
        :param block:墙的表示 默认-1
        """
        self.maze = maze_array
        self.sx =start_x
        self.sy = start_y
        self.gx = end_x
        self.gy = end_y#终点
        self.d = maze_array.copy()#d矩阵和迷宫同大小表示步数
        self.N, self.M = self.maze.shape#初始矩阵的长宽
        self.block = block
        self.realpath=[]

    def bfs(self):
        global d
        path = []
        dx = [1,1,1,-1,-1,-1,0,0]  # 八个方向移动向量
        dy = [1,0,-1,1,0,-1,1,-1]  # 八个方向移动向量
        que = queue.Queue()  # 建队列变量
        for i in range(self.N):
            for j in range(self.M):
                self.d[i][j] = INF  # 初始化为INF
        p_list = [self.sx, self.sy, -1]  # 形成一个坐标，一起压入队列
        self.d[self.sx][self.sy] = 0  # 将d的起始点坐标设置为0
        que.put(p_list)  # 将坐标压入队列
        while (que.qsize()):
            que_get = que.get()  # 读取队列
            path.append(que_get)
            # print(que_get)
            if (que_get[0] == self.gx and que_get[1] == self.gy):  # 如果到终点，结束搜索
                self.realpath =print_r(path)
                break
            # 八个移动方向
            for i in range(8):
                # 移动之后的位置记为nx，ny
                nx = que_get[0] + dx[i]
                ny = que_get[1] + dy[i]
                # 判断是否可以移动，并且是否已经访问过（访问过d[nx][ny]!=INF）
                if (0 <= nx and nx < self.N and 0 <= ny and ny < self.M
                        and self.maze[nx][ny] != self.block and self.d[nx][ny] == INF):
                    p_list = [nx, ny, len(path) - 1]  # 如果可以移动，将该点加入队列；并且距离加一
                    que.put(p_list)
                    self.d[nx][ny] = self.d[que_get[0]][que_get[1]] + 1

        return self.d[self.gx][self.gy]

def print_r(path,echo_print=False):
    curNode = path[-1]
    realpath = []
    while curNode[2] != -1:
        realpath.append(curNode[0:2])
        curNode = path[curNode[2]]
    # realpath.append(curNode[0:2]) # 把起点放进去
    realpath.reverse()
    if echo_print:
        print(len(realpath))
        for i in realpath:
            print(i)
    return realpath

def start(maze_zone ,start_x=0,start_y=1,end_x =9,end_y = 8,block=1):
    mymaze = Maze(maze_array=maze_zone,start_x=start_x,start_y=start_y,end_x=end_x,end_y=end_y,block=block)
    res = mymaze.bfs()
    print('最少次数为%d' % res)

def fetch_good(sx,sy,end_x,end_y,high_low,good_left_time,maze_array,sz=0):
    """
    :param sx:飞机初始位置x
    :param sy:
    :param sz:
    :param end_x:
    :param end_y:
    :param high_low:最低飞行高度
    :return:返回运输过程中的路径
    """
    fly_path = []
    #fly_path.append((sx,sy,0))#把最开始的位置添加进去
    # 取货过程
    fly_time = high_low*2
    if sz<high_low:
        for i in range(sz+1,high_low+1):
            fly_path.append((sx,sy,i))#初始飞到取货点上空
    mymaze = Maze(maze_array=maze_array, start_x=sx, start_y=sy, end_x=end_x, end_y=end_y, block=-1)
    fly_time += mymaze.bfs()
    if fly_time>good_left_time or fly_time<0:#时间不够，飞不到
        return False
    realpath = mymaze.realpath

    for fly_action in realpath:
        fly_action.append(high_low)
        fly_path.append(tuple(fly_action))
    for i in range(high_low-1,-1,-1):
        fly_path.append((end_x,end_y,i))#初始飞到取货点上空
    return fly_path


if __name__=="__main__":
    import datetime
    start_time =datetime.datetime.now()
    # fly_path = fetch_good(sx=0, sy=1, end_x=9, end_y=8, high_low=7, good_left_time=80, maze_array=maze)
    # # start()
    # print(fly_path,len(fly_path))
    # print("time use:",(datetime.datetime.now()-start_time).microseconds)
