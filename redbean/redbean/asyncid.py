import logging
logger = logging.getLogger(__name__)

import asyncio

import grpc
from aioetcd3.client import client as etcd_client
from aioetcd3.help import range_all, range_prefix
from aioetcd3 import transaction
from aioetcd3.kv import KV

from base64 import b16encode as _b16encode
from random import uniform as _rand_uniform

from .sleep import InterruptibleSleep


class AsyncID64:

    """ 分布式产生一个64位唯一ID。

    64bits ID: 32bits timestamp(in seconds), 12bits shards, 20bits sequence
    
    思路：每个进程可以创建一个或多个AsyncID实例，每个AsyncID实例动态租用一个“分片”，
    在其分片(shard)内，同时间戳(timestamp)下，序号(squence)保证唯一。
    
    :param prefix: 作为etcd目录的路径，例如 /asyncid/user_sn 

    """

    def __init__(self, prefix, endpoint, *, shard_ttl=14400, max_sequence=None):
        """
        """
        assert prefix.startswith('/')
        assert not prefix.endswith('/')
        assert len(prefix) > 1
        self._prefix = prefix

        self._client = etcd_client(endpoint)
        self._shard_ttl = shard_ttl

        if max_sequence is None:
            self._max_sequence = 2**20 - 1
        else:
            assert max_sequence <= 2**20 - 1
            self._max_sequence = max_sequence

        self._timestamp = None
        self._shard_id = None
        self._seqnum = None

        self._ready_event = None
        self._is_running = False
        self._is_stopping = False
        self._sleeping = None

        self._task = None

    async def new(self, encoding=None):

        if self._ready_event is None:
            self.start() # 自动启动服务

        seqnum = None
        while await self._ready_event.wait(): # 等待序号计数进入就绪状态
            if self._seqnum >= self._max_sequence:
                self._fire_renew_timestamp()
                continue

            with await self._lock:
                seqnum = self._seqnum
                self._seqnum += 1
            break

        shard_id = int_fromhexstr(self._shard_id)
        int_value = (self._timestamp << 32) | (shard_id << 20) | seqnum
        if encoding is None:
            return int_value

        buffer = int_value.to_bytes(8, byteorder='big')
        if encoding == 'base16':
            return _b16encode(buffer).decode('ascii')


    def start(self):
        self._ready_event = asyncio.Event() # 表示后台程序是否启动完毕
        
        self._lock = asyncio.Lock()

        loop = asyncio.get_event_loop()
        self._task = loop.create_task(self._run())

    def stop(self):
        """ """
        if self._task is None:
            return
                
        self._is_stopping = True
        logger.debug(f'stopping shard {self._shard_id}')
        
        if self._sleeping is not None:
            self._sleeping.cancel()
        
        self._is_running = False

    async def stopped(self):
        if self._task is None:
            return

        stopped = asyncio.Event()

        if not self._task.done():
            self._task.add_done_callback(lambda task: stopped.set())
            await stopped.wait()

        try:
            return self._task.result()
        except grpc.RpcError:
            logger.error(f"Caught an error in stopping ASyncID[{self._shard_id}]", 
                        exc_info=True) 

    def _fire_renew_timestamp(self):
        if self._sleeping is not None:
            self._sleeping.cancel()
        self._ready_event.clear()

    async def _run(self):
        """后台任务更新时间戳和重置序号"""

        tick_gen = _task_idle_ticks(0.5*self._shard_ttl)
        self._is_running = True
        self._ready_event.clear()
        
        while True:
            try:
                await self._lease_shard()
                break
            except grpc.RpcError as exc:
                nap = _rand_uniform(3, 15)
                logger.warn(f'failed in gRPC [{exc.code()}]: {exc.details()} '
                            f'. napping {nap:.0f} secs ...')

                if await self._continueAfterSleep(nap):
                    continue
                else:
                    return

        assert self._shard_id is not None           
               
        try:
            while self._is_running:

                self._ready_event.clear()
                try:
                    await self._renew_timestamp()
                    await self._keepalive_shard()
                except grpc.RpcError as exc: 
                    # exc.code()==grpc.StatusCode.UNAVAILABLE
                    nap = _rand_uniform(3, 15)
                    logger.warn(f'failed in grpc[{exc.code()}]: {exc.details()}'
                                f', napping {nap:.0f}secs ...')

                    if await self._continueAfterSleep(nap):
                        continue
                    else:
                        break

                self._ready_event.set()

                if await self._continueAfterSleep(next(tick_gen)):
                    continue
                else:
                    break

        except asyncio.CancelledError:
            pass

        except Exception:
            logger.error(f'Error in shard#{self._shard_id}:', exc_info=True)

        finally:
            self._ready_event.clear()
            await self._lease.revoke() # 取消租约
            logger.debug(f'shard#{self._shard_id}, the lease revoked')

    async def _continueAfterSleep(self, seconds):
        """ 返回True，可睡醒或被叫醒后继续的；否则，睡醒或被叫醒后，不能继续执行 """
        assert self._sleeping is None
        self._sleeping = InterruptibleSleep(seconds)
        try:
            await self._sleeping.wait()
            return True
        except asyncio.CancelledError:
            return not self._is_stopping
        finally:
            self._sleeping = None        

    async def _renew_timestamp(self) -> None:
        retries = 0
        # 重新设置序号计数的时间戳
        while True:
            local_timestamp = _make_timestamp()
            latency = await self._update_timestamp(local_timestamp)
            if latency == 0:
                # 成功更新时间戳，重新计数
                self._timestamp = local_timestamp
                self._seqnum = 0
                logger.debug(f"shard#{self._shard_id}, renew timestamp {self._timestamp}")

                return
            else:
                # 更新失败，或许其它分片刚同时更新成功，随机休息片刻再次重试
                if latency < 10: 
                    # 在30秒之内就等待一会儿再尝试，如果太长则可能存在系统时间设置问题
                    logger.debug(f'latency, sleep {latency} secs at shard {self._shard_id}')

                    try:
                        self._sleeping = InterruptibleSleep(latency)
                        await self._sleeping.wait()
                    except asyncio.CancelledError:
                        raise
                    finally:
                        self._sleeping = None
                                            
                    continue
                else:
                    raise ValueError(f'全局时间晚于当前时间太长({latency} secs)')

            retries += 1
        
    async def _update_timestamp(self, local_timestamp):

        timestamp_path = f'{self._prefix}/timestamp/{self._shard_id}'

        timestamp_bytes = local_timestamp.to_bytes(4, byteorder='big')

        is_success, responses = await self._client.txn(compare=[
                transaction.Value(timestamp_path) < timestamp_bytes,
            ], success=[
                KV.put.txn(timestamp_path, timestamp_bytes, prev_kv=True)
            ], fail=[
                KV.get.txn(timestamp_path)
            ])
        if is_success:
            return 0
        
        if responses[0][0] is None: # 
            is_success, _ = await self._client.txn(compare=[
                    transaction.Version(timestamp_path) == 0,
                ], success=[
                    KV.put.txn(timestamp_path, timestamp_bytes)
                ])
            
            if is_success:
                return 0
            
            raise ValueError()
        else:
            assert responses[0][0] is not None
            remote_timestamp = int.from_bytes(responses[0][0], byteorder='big')
            latency = remote_timestamp - local_timestamp
            assert latency >= 0, f'latency: {latency}'
            if latency == 0:
                latency = 1
            
            return latency


    async def _lease_shard(self):
        """ 申请一个新分片，从小到大[0,4095]寻找一个为占用的分片 """

        prefix = self._prefix + '/shards/'
        self._lease = await self._client.grant_lease(ttl=self._shard_ttl)

        timestamp_bytes = (0).to_bytes(4, byteorder='big')

        retries = 0
        while True:
            shard_subidx = len(prefix)
            shard_id = 0

            # 找到未使用的最小分片号
            records = await self._client.range_keys(range_prefix(prefix))
            nums = sorted(int_fromhexbytes(k[shard_subidx:]) for k, _ in records)
            for i, n in enumerate(nums):
                if n > i:
                    shard_id = i
                    break
            else:
                shard_id = len(nums)

            shard_id = int_tohex(shard_id, length=2)

            logger.debug(f'leasing shard#{shard_id}, retry={retries}')

            shard_path = f'{self._prefix}/shards/{shard_id}'
            is_success, _ = await self._client.txn(compare=[
                    transaction.Version(shard_path) == 0 
                ], success=[
                    KV.put.txn(shard_path, timestamp_bytes, lease=self._lease)
                ])

            if is_success:
                self._shard_id = shard_id
                self._timestamp = None
                self._seqnum = None
                break
            else:
                logger.debug(f'failed in leasing shard#{shard_id}: retry {retries}')
                await _random_nap(retries)
                retries += 1

                if retries > 10:
                    raise ValueError('out of retries')

    async def _keepalive_shard(self):
        lease = await self._client.refresh_lease(self._lease)
        self._lease = lease
        logger.debug(f'shard#{self._shard_id}, keep the lease alive, ttl={lease.ttl}')


def int_fromhexbytes(hex_bytes):
    return int.from_bytes(bytes.fromhex(hex_bytes.decode('ascii')), byteorder='big')

def int_fromhexstr(hex_str):
    return int.from_bytes(bytes.fromhex(hex_str), byteorder='big')

def int_tohex(int_value: int, length):
    return bytes.hex((int_value).to_bytes(length, byteorder='big'))

from datetime import datetime
from time import time as time_ticks

def b16encode_int64(int_value):
    return _b16encode(int_value.to_bytes(8, byteorder='big')).decode('utf-8')

async def _random_nap(retries=0):
    asyncio.sleep(_rand_uniform(0.1, 0.3))

def _make_timestamp():
    return int(datetime.utcnow().timestamp())

def _task_idle_ticks(seconds_per_cycle):
    """ 计算下次周期的沉睡时间 """ 
    t = time_ticks()
    while True:
        t += seconds_per_cycle
        yield max(t - time_ticks(), 0)


__all__ = ['AsyncID64']
