# -*- coding: utf-8 -*-

import socket
import threading
import Queue
from time import sleep,ctime
import re

queue_size = 100  # 缓存队列大小
data_queue = Queue.Queue(queue_size)

RECEIVE_SERVER = ('0.0.0.0', 14581)  # 接收服务器
APRSIS_SERVER1 = ('192.168.1.1', 14580)  # SERVER1，适用于server1_callsigns列表中的呼号
APRSIS_SERVER2 = ('127.0.0.1', 14580)  # SERVER2，适用于其它呼号
CALLSIGN = 'NOCALL-0'  # 替换为你的呼号
PASSCODE = '13023'  # 替换为你的 APRS-IS 密码
FILTER = 'filter b/N0CALL'  # APRS-IS 过滤器

# 定义需要转发到 SERVER1 的呼号列表
server1_callsigns = ['BB1BB-9', 'BB1BB-5']

def extract_callsign(aprs_data):
	# 正则表达式匹配呼号
	match = re.match(r'user (\S+)', aprs_data)
	if match:
		return match.group(1).upper()
	return None
	
def connect_to_receive_server(server):
	sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
	sock.bind(server)
	return sock
	
def connect_to_aprsis_server(server, callsign, passcode, filter_str):
	sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
	login_str = 'user {} pass {} vers PythonAPRS 1.0 {}\n'.format(callsign, passcode, filter_str)
	sock.sendto(login_str.encode('utf-8'), server)
	return sock

def receive_data(sock):
	while True:
		data, addr = sock.recvfrom(1024)
		if not data:
			break
		print("Received: {}".format(data.strip()))
		# 接收到数据后返回 'R'
		sock.sendto(b'R', addr)
		# 确保将数据放入队列，仅当队列未满时才放入
		if not data_queue.full():
			data_queue.put(data)
		#print("Current queue size: {}".format(data_queue.qsize()))  # 打印当前队列大小

def forward_data(sock1, sock2, server1, server2):
	sock1.settimeout(10)  # 仅为 sock1 设置超时
	while True:
		data = data_queue.get()
		#print("Process data : %s" % data)
		# 从数据中提取呼号，假设呼号在数据的前面部分
		callsign = extract_callsign(data)
		# 确定转发目标服务器
		if callsign in server1_callsigns:
			target_sock = sock1
			target_server = server1
			while True:
				try:
					target_sock.sendto(data, target_server)
					print("{} Forwarded to {}: {}".format(ctime(), target_server, data.strip()))
					response, addr = target_sock.recvfrom(1024)
					if b'R' in response:
						break
					else :
						print("%s Forwarded not correct responsed, retrying in 10 seconds..." % (ctime()))
						sleep(10)
				except socket.timeout:
					print("%s No response, retrying in 10 seconds..." % (ctime()))
					sleep(10)
				except Exception as e:
					print("%s, Forward failed with error: {}, retrying in 10 seconds...".format(ctime(),e))
					sleep(10)
		else:
			target_sock = sock2
			target_server = server2
			try:
				target_sock.sendto(data, target_server)
				print("%s Forwarded to {}: {}".format(ctime(), target_server, data.strip()))
			except Exception as e:
				print("%s Forward failed with error: {}".format(ctime(), e))
		data_queue.task_done()
		#print("Current queue size: {}".format(data_queue.qsize()))  # 打印当前队列大小

def main():
	# 连接到接收服务器
	receive_sock = connect_to_receive_server(RECEIVE_SERVER)
	
	# 连接到两个 APRS-IS 服务器
	sock1 = connect_to_aprsis_server(APRSIS_SERVER1, CALLSIGN, PASSCODE, FILTER)
	sock2 = connect_to_aprsis_server(APRSIS_SERVER2, CALLSIGN, PASSCODE, FILTER)
	
	# 启动接收线程
	threading.Thread(target=receive_data, args=(receive_sock,)).start()
	
	# 启动转发线程
	threading.Thread(target=forward_data, args=(sock1, sock2, APRSIS_SERVER1, APRSIS_SERVER2)).start()

	# 防止主线程退出
	data_queue.join()

if __name__ == "__main__":
	main()
