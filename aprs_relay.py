# -*- coding: utf-8 -*-

import socket
import threading
import Queue
from time import sleep,ctime
import re

queue_size = 1000  # 缓存队列大小
data_queue = Queue.Queue(queue_size)

RECEIVE_SERVER = ('0.0.0.0', 14581)  # 接收服务器
APRSIS_SERVER1 = ('192.168.1.1', 14580)  # SERVER1，适用于server1_callsigns列表中的呼号
APRSIS_SERVER2 = ('127.0.0.1', 14580)  # SERVER2，适用于其它呼号
#CALLSIGN = 'NOCALL-0'  # 替换为你的呼号
#PASSCODE = '13023'  # 替换为你的 APRS-IS 密码
#FILTER = 'filter b/N0CALL'  # APRS-IS 过滤器
#login_str = 'user {} pass {} vers PythonAPRS 1.0 {}\n'.format(CALLSIGN, PASSCODE, FILTER)

# 定义需要转发到 SERVER1 的呼号列表
server1_callsigns = ['BB1BB-7', 'BB2BB-3']

def extract_callsign(aprs_data):
	# 正则表达式匹配呼号
	match = re.match(r'user (\S+) pass.*', aprs_data)
	if match:
		return match.group(1).upper()
	return None

def receive_data():
	# 连接到接收服务器
	sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
	sock.bind(RECEIVE_SERVER)
	while True:
		data, addr = sock.recvfrom(1024)
		if not data:
			continue
		print("%s Received: %s" % (ctime(), data.strip()))
		callsign = extract_callsign(data)		# 从数据中提取呼号，假设呼号在数据的前面部分
		if callsign :			#判断是否APRS包，不是的直接丢弃
			# 接收到数据后返回 'R'
			sock.sendto(b'R', addr)
			# 确保将数据放入队列，仅当队列未满时才放入
			if not data_queue.full():
				data_queue.put((data , callsign))
			#print("Current queue size: {}".format(data_queue.qsize()))  # 打印当前队列大小

def forward_data():
	# 准备sock连接
	sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
	sock.settimeout(10)  # 为 sock 设置超时10秒
	while True:
		data, callsign = data_queue.get()
		#print("Process data : %s" % data)
		# 确定转发目标服务器
		if callsign in server1_callsigns:
			while True:
				try:
					sock.sendto(data, APRSIS_SERVER1)
					print("%s Forwarded to %s" % (ctime(), APRSIS_SERVER1))
					response, addr = sock.recvfrom(1024)
					if b'R' in response:
						break
					else :
						print("%s Forwarded not correct responsed, retrying in 10 seconds..." % (ctime()))
						sleep(10)
				except socket.timeout:
					print("%s No response, retrying in 10 seconds..." % (ctime()))
					sleep(10)
				except Exception as e:
					print("%s, Forward failed with error: %s, retrying in 10 seconds..." % (ctime(),e))
					sleep(10)
		else:
			try:
				sock.sendto(data, APRSIS_SERVER2)
				print("%s Forwarded to %s" % (ctime(), APRSIS_SERVER2))
			except Exception as e:
				print("%s Forward failed with error: %s" % (ctime(), e))
		data_queue.task_done()
		#print("Current queue size: {}".format(data_queue.qsize()))  # 打印当前队列大小

## 线程状态管理
threads = {}
thread_targets = {
	'receive_data': receive_data,
	'forward_data': forward_data,
}

# 启动线程
def start_thread(name, target):
	thread = threading.Thread(target=target, name=name)
	thread.setDaemon(True)  # 将线程设置为守护线程
	thread.start()
	threads[name] = thread
	print("%s Starting %s thread" % (ctime(),name))

# 检查线程状态
def check_threads():
	while True:
		for name, thread in threads.items():
			if not thread.is_alive():
				#print("%s : %s is not alive. Restarting..." % (ctime(),name))
				start_thread(name, thread_targets[name])
		sleep(5)  

if __name__ == '__main__':
	# 使用循环启动所有线程
	for name, target in thread_targets.items():
		start_thread(name, target)
	
	# 启动线程检查
	check_thread = threading.Thread(target=check_threads)
	check_thread.setDaemon(True)  # 将线程设置为守护线程
	check_thread.start()
	
	# 主线程保持运行
	try:
		while True:
			sleep(10)
	except KeyboardInterrupt:
		print("Shutting down...")

