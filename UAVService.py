# -*- coding:utf-8 -*-
import json
import numpy as np
import time
import socket
from game import fetch_good

plane_goods = []  # 飞机-货物list组合，里面是字典{[飞机-货物-取货路径-送货路径]}

flag_rematch = True  # 是否更新fly_goods的标识符
h_high = 0  # 飞行的最高高度
h_low = 0  # 飞行的最低高度
maze_array = []  # 三维迷宫
renew_Myplane = False
goodsInTranfer =[]
parking=()

def toJson(recevie_data):
    data_length = int(recevie_data[0:8])
    data_json = json.loads(recevie_data[8:])
    return data_length, data_json

# sendjson or senddict
def to_send(sendjson):
    str_json = json.dumps(sendjson)
    len_json = str(len(str_json)).zfill(8)
    # send_string = "%08d%s" % (ord(str(len(sendjson) * 2)), str(sendjson))
    send_string = len_json + str_json
    send_string = send_string.replace('\'', '"')
    return send_string.encode()

def sendjson(s, sendjson):
    send_info = to_send(sendjson)
    s.send(send_info)

# 对核心对战地图进行处理
def generate_zone(map_info):
    """
    生成飞行区域空间
    0表示可以经过；-1表示建筑物和最高飞行高度以上，1表示安全区域
    :param map_info:
    :return:
    """
    global h_high, h_low, maze_array,parking
    map = map_info["map"]
    map_array = np.zeros((map['map']['x'], map['map']['y'], map['map']['z']), dtype=np.int8)
    # parking = map['parking']#停机坪位置
    parking = (map['parking']['x'],map['parking']['y'],0)
    map_array = map_array[:, :, 0:map["h_high"] + 1]  # 大于最大飞行高度的直接截断
    map_array[:, :, map["h_low"]:] = 1  # 安全飞行区域
    building = map["building"]
    h_high = map["h_high"]
    h_low = map["h_low"]
    for one_build in building:
        # x->x+l-1,
        # max_high = map["h_high"]+1 if map["h_high"]+1>=one_build["h"] else one_build["h"]
        map_array[one_build["x"]:one_build["x"] + one_build["l"], one_build["y"]:one_build["y"] + one_build["w"],
        0:one_build["h"]] = -1  # 建筑物区域设置为-1
    maze_array = map_array
    print("地图信息如下：最高飞行%d，最低飞行%d" % (h_high, h_low))

def genarate_planes_goods_set(myplanes, goods):
    """
    :param myplanes:
    :param goods:
    :return:
    """
    global plane_goods

    planes_key = [x[0] for x in plane_goods]   #已经匹配到的飞机信息
    good_value = [x[1] for x in plane_goods]   #已经匹配到的货物信息

    for one_good_index in range(len(goods)):
        # one_good格式{ "no": 0, "start_x": 3, "start_y": 3, "end_x": 98, "end_y": 3, "weight": 55, "value": 100, "start_time":15,"remain_time": 90, "left_time": 75,"status": 1},
        # status为0表示空闲，为1表示已经被运输
        one_goods = goods[one_good_index]
        goodHasMatched = False
        if one_goods["no"] in good_value:
            goodHasMatched =True
            continue  # 已经匹配了货物
        if goodHasMatched:
            break
        for one_plane_index in range(len(myplanes)):
            # oneplane格式{"no":3,"x":0,"y":16,"z":0,"load_weight":30,"type":"F4","status":0,"goods_no":-1}
            if goodHasMatched:
                break
            plane = myplanes[one_plane_index]
            if plane["no"] in planes_key:
                continue  # 已经匹配了飞机
            if one_goods['status'] == 0 and one_goods['weight'] <= plane['load_weight']:
                fly_path_fetch = fetch_good(sx=plane['x'], sy=plane['y'],sz=plane['z'], end_x=one_goods['start_x'],
                                            end_y=one_goods['start_y'],
                                            high_low=h_low, good_left_time=one_goods['left_time'],
                                            maze_array=maze_array[:, :, h_low])
                if not fly_path_fetch:  # 当前点不通
                    continue
                # fly_path_fetch.insert(0,(plane['x'],plane['y'],0))#将飞机初始位置添加，方便第一次返回
                fly_path_send = fetch_good(sx=one_goods['start_x'], sy=one_goods['start_y'], end_x=one_goods['end_x'],
                                           end_y=one_goods['end_y'], high_low=h_low,
                                           good_left_time=one_goods['left_time'] - len(fly_path_fetch),
                                           maze_array=maze_array[:, :, h_low])
                if not fly_path_send:  # 当前点不通
                    continue

                plane_goods.append((plane["no"],one_goods["no"],fly_path_fetch,fly_path_send))  # 将其添加到plane_goods字典中

                # 更新
                planes_key = [x[0] for x in plane_goods]#这里可以直接append下同
                good_value = [x[1] for x in plane_goods]
                goodHasMatched=True#匹配完成后，内层循环就结束了
    print("飞机货物信息匹配后为:", plane_goods)


def get_goodlist(battle_dict):
    """
    good格式{'no': 6, 'start_x': 4, 'start_y': 8, 'end_x': 3, 'end_y': 18, 'weight': 32, 'value': 36, 'start_time': 19, 'remain_time': 64, 'status': 1, 'left_time': 19}
    从battle_dict中获取可以取得货物的list
    :param battle_dict:
    :return:
    """
    global goodsInTranfer
    goods = []
    for good in battle_dict['goods']:
        if good['status'] == 0 or good['no'] in goodsInTranfer:
            goods.append(good)
    goods = sorted(goods, key=lambda k: k['value'], reverse=True)  # 货物value降序排列
    return goods


def fly(initaldata, FlyPlane, battle_dict):
    """
    :param initaldata:初始接收到的对战通知信息，含有地图和我方飞机等所有信息
    :param FlyPlane:我方飞机信息，核心就是更新FlyPlane["UAV_info"] 字段
    :param battle_dict:对战信息，
    :return:
    """
    global plane_goods, h_low, h_high, flag_rematch, renew_Myplane, goodsInTranfer, parking
    # 去掉之前完成的部分
    plane_goods = [x for x in plane_goods if x !=()]
    if renew_Myplane:
        FlyPlane["UAV_info"] = battle_dict["UAV_we"]
        FlyPlane["UAV_info"] = sorted(FlyPlane["UAV_info"], key=lambda k: k['load_weight'],
                                      reverse=True)  # 按照无人机的载重降序排列

    my_plane = FlyPlane['UAV_info']  # 我方飞机已经按照最大载重降序排列

    # 准备飞行
    allgoods = get_goodlist(battle_dict)  # list类型的字典信息#这里没有考虑货物被对手运输的情况
    goods_list = [x['no'] for x in allgoods]  # 对战信息中的货物的编号组合

    # 首先删掉已经消失的货物组合和已经输送完成的
    for index,onePlaneGoodsSet in enumerate(plane_goods):
        if onePlaneGoodsSet[1] not in goods_list:
            del plane_goods[index]

    # 检查是否有新增的货物
    good_value = [x[1] for x in plane_goods]  # 已经匹配到的货物信息
    for goodsNumber in goods_list:
        if goodsNumber not in good_value:
            flag_rematch = True
            break
    # 判断当前飞行路径上的飞机能否在货物消失前取到
    #飞行组合的货物编号应当全部在对战货物编号列表中
    for goodIndex,good_no in enumerate(goods_list):
        if good_no in good_value:#对战信息中的货物编号存在于已经确定飞行组合的set中，执行检察
            if allgoods[goodIndex]['left_time']<len(plane_goods[good_value.index(good_no)][2])+len(plane_goods[good_value.index(good_no)][3]):
                print("运输路径过长，放弃取货")
                plane_goods[good_value.index(good_no)] =()
                flag_rematch = True
    plane_goods = [x for x in plane_goods if x != ()]#上面判别运输路径会产生()字段
    # 货物不匹配或者有飞机飞到了
    if flag_rematch:
        print("获取到的货物飞机组合有变动，重新匹配")
        genarate_planes_goods_set(myplanes=my_plane, goods=allgoods)
        flag_rematch = False
        # 然后需要重新匹配plane_goods

    good_value = [x[1] for x in plane_goods]  # 已经匹配到的货物信息
    planes_value = [x[0] for x in plane_goods]  # 已经匹配到的飞机信息
    for x in plane_goods:
        print("第%d飞机 与%d号货物组合"%(x[0],x[1]))
    # 计算当前占据的点
    occupied_points = []
    # for x in allgoods:
    #     occupied_points.append((x['start_x'],x['start_y'],0))
    for x in my_plane:
        current_point = (x['x'], x['y'], x['z'])
        if current_point!=parking:
            occupied_points.append(current_point)
    print("当前occupied_points为%s" % occupied_points)
    force_move = True
    # for plane in my_plane[0:len(plane_goods)]:  # 只需要对匹配到的进行更新
    for plane_index ,plane in enumerate(my_plane):  # 只需要对匹配到的进行更新+ 其他
        # plane{'no': 0, 'x': 0, 'y': 16, 'z': 0, 'load_weight': 100, 'type': 'F1', 'status': 0, 'goods_no': -1},
        if plane["no"] in planes_value:
            index = planes_value.index(plane["no"])
            print("第%d飞机在第%s" % (plane["no"], plane_goods[index]))
            fly_path = plane_goods[index][2] if len(plane_goods[index][2])>0 else plane_goods[index][3] #初始时赋值为取货路径
            fly_point = fly_path[0]
            if fly_point not in occupied_points or (plane["goods_no"] in goodsInTranfer and force_move):  # 飞机即将飞的点没有其他飞机存在/载货的强制飞行
                force_move = False
                good_exceptfortransfer = []  # 除了待运输的货物的位置集合
                for x in allgoods:
                    if x["no"] != good_value[index]:
                        good_exceptfortransfer.append((x['start_x'], x['start_y'], 0))
                if fly_point in good_exceptfortransfer:  # 运输路径中有其他货物阻挡，直接返回，等待
                    continue
                # plane['x'], plane['y'], plane['z'] = fly_path.pop(0)
            else:
                if plane['z']>=h_low:
                    fly_path.insert(0, (plane['x'], plane['y'], plane['z']+1))
                    fly_path.insert(1, (plane['x'], plane['y'], plane['z']+1))
                    fly_path.insert(2,(plane['x'], plane['y'],plane['z']))
            plane['x'], plane['y'], plane['z'] = fly_path.pop(0)
            if len(occupied_points)>plane_index:
                occupied_points[plane_index] = (plane['x'], plane['y'], plane['z'])#原来是fly_point
            else:
                occupied_points.append((plane['x'], plane['y'], plane['z']))
            if len(fly_path) == 0:
                if len(plane_goods[index][3]) == 0:
                    # 这是已经送货完成了
                    # del plane_goods[index]  # 删除飞机货物组合标志位更新组合这样删除后面会报错
                    plane_goods[index]=()#当前飞行组合设置为空
                    occupied_points[index] = ()
                    flag_rematch = True
                    renew_Myplane = True
                    del goodsInTranfer[goodsInTranfer.index(good_value[index])]

                    print("\n飞机%d完成运输%d号物品\n" % (plane["no"], good_value[index]))
                else:
                    # 这是完成了取货
                    plane['goods_no'] = good_value[index]
                    goodsInTranfer.append(good_value[index])
                    print("飞机%d到达%d号物品位置\n\n" % (plane["no"], good_value[index]))
        else:#其他没有匹配到的飞机
            if plane["z"]<h_low:
                fly_point = (plane['x'],plane['y'],plane['z']+1)
                if fly_point not in occupied_points:
                    plane["z"]+=1
                    occupied_points.append(fly_point)
    return FlyPlane


def start(ip, port, token):
    # f_write = open('fight2.txt','w')
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.connect((ip, int(port)))
    data = s.recv(1024)  # 2.1链接裁判服务器#b'00000052{"notice":"token","msg":"hello, what\'s your token?"}'
    data_length, data_json = toJson(data)
    print('最开始', data_json)

    # 2.2 选手向裁判服务器表明身份(Player -> Judger)
    my_token = {"token": token, "action": "sendtoken"}
    send_ = to_send(my_token)
    print("发送数据为", send_)
    s.send(send_)

    # 2.3 身份验证结果(Judger -> Player)
    data = s.recv(1024)
    data_length, data_json = toJson(data)
    print('身份验证', data_json)
    if data_json['result'] == -1:
        return

    # 2.3.1选手向裁判服务器表明自己已准备就绪(Player -> Judger)
    send_ = to_send({"token": token, "action": "ready"})
    s.send(send_)

    # 2.4 对战开始通知(Judger -> Player)　
    data = s.recv(2048)  # 第一次该部分会受到地图和货物信息
    _length, initaldata = toJson(data)
    generate_zone(initaldata)  # 初始化h_low,h_high,parking,maze_array
    print('核心地图信息', initaldata)
    # f_write.write('核心地图信息'+str(alldata_json) + '\n')
    FlyPlane = {"UAV_info": initaldata['map']['init_UAV'], "token": initaldata['token'], "action": "flyPlane"}
    # for element in m_dict["UAV_info"]:
    #     del element["load_weight"]
    #     del element["type"]
    #     del element["status"]
    # 不删该部分的话，后面也会带上这几个字段

    FlyPlane["UAV_info"] = sorted(FlyPlane["UAV_info"], key=lambda k: k['load_weight'], reverse=True)  # 按照无人机的载重降序排列

    i = 0
    battle_dict = {}

    send_info = to_send(FlyPlane)  #
    s.send(send_info)  # 这是刚开始的时候
    while 1:
        # 2.5选手返回下一步无人机坐标(Player -> Judger)

        # print('%d时刻发送信息'%i, send_info)
        # 2.6 比赛下一步骤指令(Judger -> Player)
        data = s.recv(1024 * 1024 * 4)  # 第一次运行改指令的时候，会收到货物信息

        _length, battle_dict = toJson(data)
        print('%d时刻接收消息' % i, battle_dict)
        # f_write.write(str(alldata)+'\n')
        i += 1
        if battle_dict['match_status'] == 1:
            break
        tofly = fly(initaldata, FlyPlane, battle_dict)
        send_info = to_send(tofly)  #
        s.send(send_info)
        print("%d时刻发送消息为%s" % (i,tofly))
    print('对战结束')



if __name__ == "__main__":
    map_info = {}

