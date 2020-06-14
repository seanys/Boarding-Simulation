'''
我们仅进行比较简单的模拟，每次生成3*6=18名客户，座位号定义为“行-左/右-第一
个座位”，比如1-A-1即第一行左侧第一个位置（靠走廊），一共生成如下图所示
4+18=22个Counter

    ｜3  ｜  ｜
    ｜2  ｜  ｜
    ｜1  ｜  ｜
——  ——  ——  ——  A
    ｜1  ｜  ｜
    ｜2  ｜  ｜
    ｜3  ｜  ｜

乘客行为方面
1. 乘客按照均匀时间生成，模拟飞机登机时逐个登机
2. 每个乘客都有随机的速度期望值，具体表现为在每个Encounter中的服务时间，具
体多久从正态分布中随机抽取
3. 判断所处位置并进行服务，同时设置Next Grid。如果目标位置就在该行，那么
Next Grid在旁边的短链，服务时间根据是否携带行李生成；否则，Next Grid设置
为该链上的下一个Grid
4. 服务完成后，前面的座位仍然有人，判断是在短链还是长链。如果在短链，比如1号
已经入座，3号需要入座，则速度会变慢而不需要等待；如果在长链，则等待前面服务完
成
'''

import random
import simpy
import copy
import numpy as np

RANDOM_SEED = 42 # 随机种子
NEW_PASSENGERS = 18 # 客户数
INTERVAL_PASSENGERS = 1.0 # 客户到达的间隔时间/秒

SEATS_STATUS = [0]*18

GRID_LONG_LIST = [] # 长链部分
GRID_LEFT_LIST = [] # 走廊左侧短链
GRID_RIGHT_LIST = [] # 走廊右侧短链

class Airplane(object):
    """飞机登机的环境"""
    def __init__(self, env):
        self.env = env
        self.genCounters()

    def genCounters(self):
        '''生成链式的服务中心'''
        # 生成长链的Grid，仅可服务一个客户
        for i in range(4):
            grid = simpy.Resource(self.env, capacity=1)
            GRID_LONG_LIST.append(grid)
        # 生成短链的Grid，同样仅可服务一个客户
        for i in range(3):
            grids = []
            for j in range(3):
                grid = simpy.Resource(self.env, capacity=1)
                grids.append(grid)
            GRID_LEFT_LIST.append(grids)
        # 生成短链的Grid，同样仅可服务一个客户
        for i in range(3):
            grids = []
            for j in range(3):
                grid = simpy.Resource(self.env, capacity=1)
                grids.append(grid)
            GRID_RIGHT_LIST.append(grids)

def setup(env):
    '''建立登机和乘客'''
    airplane = Airplane(env)

    # 生成随机的登机
    sequence = [i for i in range(0,NEW_PASSENGERS)]
    random.shuffle(sequence)

    # 按照登机序列登机
    for i in sequence:
        env.process(passenger(env, 'Passenger%02d' % i, i, airplane))
        wait_time = random.normalvariate(INTERVAL_PASSENGERS, 1)
        if wait_time < 0:
            wait_time = 1
        yield env.timeout(wait_time)

def getServiceList(seat_id):
    """根据座位号生成服务的列表"""
    grids_long_list, luagge_grid, seat_grids = [], [], []
    row = seat_id // 6
    column = seat_id % 6
    
    # 首先添加长链部分
    for i in range(row+1):
        grids_long_list.append(GRID_LONG_LIST[i])
    
    # 放置行李的格子
    luagge_grid = GRID_LONG_LIST[row+1]

    # 短链部分
    if column < 3:
        for i in range(0,3-column):
            seat_grids.append(GRID_RIGHT_LIST[row][i])
    else:
        for i in range(0,column-2):
            seat_grids.append(GRID_LEFT_LIST[row][i])
    return grids_long_list, luagge_grid, seat_grids

def passenger(env, name, seat_num, airplane):
    """乘客的定义交互"""
    # 乘客是否携带行李
    carry = False
    if random.random() < 0.8:
        carry = True
    # 放置行李的时间 - 提前生成 - 30s - 60s
    luagge_time = random.random() * 30 + 30
    # 不带行李的时候的时间 - 4 ~ 8s 
    without_luagge_time = random.random() * 4 + 4
    # 平均过道时间和过座位时间 3～5s
    exp_aisle_time = random.random() * 2 + 3
    exp_seat_time = random.random() * 2 + 3
    # 乘客的到达时间
    arrive = env.now
    # 生成服务的链队
    grids_long_list, luagge_grid, seat_grids = getServiceList(seat_num)
    # 首先请求长链
    for i,grid in enumerate(grids_long_list):
        with grid.request() as request:
            yield request
            print('%s enter the long grid0%s at %.2f.' % (name, i, env.now))
            yield env.process(service(env,exp_aisle_time,2))
            print('%s leaves the long grid0%s at %.2f.' % (name, i, env.now))

    # 请求放行李的部分
    with luagge_grid.request() as request:
        yield request
        print('%s enter the service grid at %.2f.' % (name, env.now))
        if carry == True:
            print("Settle luagge")
            yield env.process(service(env,luagge_time,20))
        else:
            yield env.process(service(env,without_luagge_time,2))
        print('%s leaves the service grid at %.2f.' % (name, env.now))

    # 请求最终的位置长链
    for i,grid in enumerate(seat_grids):
        with grid.request() as request:
            yield request
            print('%s enter the short grid0%s at %.2f.' % (name, i, env.now))
            yield env.process(service(env,exp_seat_time,2))
            print('%s leaves the short grid0%s at %.2f.' % (name, i, env.now))

def service(env, mu, sigma):
    """每个服务的时间"""
    service_time = random.normalvariate(mu, sigma)
    if service_time < 0:
        service_time = 1
    yield env.timeout(service_time)

if __name__ == '__main__':
    # 仿真环境配置
    random.seed(RANDOM_SEED)
    env = simpy.Environment()
    # 运行仿真过程
    env.process(setup(env))
    env.run()
    print("\nNumber of passengers:", NEW_PASSENGERS)
    print("Boarding strategy: RANDOM")
    print("Total time:", env.now/60, "min")