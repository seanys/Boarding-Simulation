# Video: https://www.youtube.com/watch?v=oAHbLRjF0vo&feature=youtu.be

import random
import simpy


RANDOM_SEED = 42 # 随机种子
NEW_CUSTOMERS = 5 # 客户数
INTERVAL_CUSTOMERS = 10.0 # 客户到达的间距时间
MIN_PATIENCE = 1 # 客户等待时间, 最小
MAX_PATIENCE = 3 # 客户等待时间, 最大


def source(env, number, interval, counter):
    """进程用于生成客户"""
    for i in range(number):
        c = customer(env, 'Customer%02d' % i, counter, time_in_bank=12.0)
        env.process(c)
        t = random.expovariate(1.0 / interval)
        yield env.timeout(t)

def customer(env, name, counter, time_in_bank):
    """一个客户表达为一个协程, 客户到达, 被服务, 然后离开"""

    arrive = env.now
    print('%7.4f %s: Here I am' % (arrive, name))

    with counter.request() as req:
        patience = random.uniform(MIN_PATIENCE, MAX_PATIENCE)
        results = yield req | env.timeout(patience)
        wait = env.now - arrive

    if req in results:
        print('%7.4f %s: Waited %6.3f' % (env.now, name, wait))
        tib = random.expovariate(1.0 / time_in_bank)
        yield env.timeout(tib)
        print('%7.4f %s: Finished' % (env.now, name))
    else:
        # 没有服务到位
        print('%7.4f %s: RENEGED after %6.3f' % (env.now, name, wait))


if __name__=='__main__':

    # 设置并开始
    print('Boarding')
    random.seed(RANDOM_SEED)
    env = simpy.Environment()

    # 开始进程
    counter = simpy.Resource(env, capacity=1)
    env.process(source(env, NEW_CUSTOMERS, INTERVAL_CUSTOMERS, counter))
    env.run()
