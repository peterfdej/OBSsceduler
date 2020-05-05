#!/usr/bin/env python

import sys
import time
import xml.etree.ElementTree as ET
import socket
import websocket
import hashlib
import base64
import json
try:
    import thread
except ImportError:
    import _thread as thread

xmlfile = 'obssceduletimes.xml'
tree = ET.parse('obshost.xml')  
root = tree.getroot()
host = root[0].text
port = root[1].text
password = root[2].text

StudioMode = False
exporttime = '3500' # every hour at mmss
GetAuthRequired = {"request-type" : "GetAuthRequired" ,"message-id" : "1"};
GetStudioModeStatus = {"request-type" : "GetStudioModeStatus" , "message-id" : "GetStudioModeStatus"}
GetSceneList = {"request-type" : "GetSceneList" , "message-id" : "getSceneList"}
GetTransitionList = {"request-type": "GetTransitionList","message-id" : "GetTransitionList"}

while True:
	try:
		def on_message(ws, message):
			data = json.loads(message)
			#print (data["message-id"])
			#print (data)
			if "error" in data:
				if (data["error"] == "Authentication Failed."):
					print("Authentication Failed.")
					ws.keep_running = False
				else:
					print (data)
			elif "message-id" in data:
				if (data["message-id"] == "GetStudioModeStatus"):
					global StudioMode
					StudioMode = data["studio-mode"]
				elif (data["message-id"] == "getSceneList"):
					with open('scenelist.txt', 'w') as outfile:
						json.dump(data, outfile) 
				elif (data["message-id"] == "GetTransitionList"):
					with open('transitionlist.txt', 'w') as outfile:
						json.dump(data, outfile)
				elif (data["authRequired"]):
					print("Authentication required")
					secret = base64.b64encode(hashlib.sha256((password + data['salt']).encode('utf-8')).digest())
					auth = base64.b64encode(hashlib.sha256(secret + data['challenge'].encode('utf-8')).digest()).decode('utf-8')
					auth_payload = {"request-type": "Authenticate", "message-id": "2", "auth": auth}
					ws.send(json.dumps(auth_payload))
				else:
					print(data)
			elif "update-type" in message:
				if (data["update-type"] == "StudioModeSwitched"):
					StudioMode = data["new-state"]

		def on_error(ws, error):
			print(error)
			ws.close()

		def on_close(ws):
			print("Connection error.")
			ws.keep_running = False
			time.sleep(30)

		def on_open(ws):
			def run(*args):
				ws.send(json.dumps(GetAuthRequired))
				time.sleep(2)
				if ws.sock:
					ws.send(json.dumps(GetStudioModeStatus))
					while True:
						tree = ET.parse(xmlfile)  
						root = tree.getroot()
						currentdtime = time.strftime("%d%m%Y%H%M%S",time.localtime())
						print(time.strftime("%H:%M:%S",time.localtime()))
						for elem in root:
							if elem[2].text == '0': #task not processed.
								dtime = elem.attrib['dtime']
								if currentdtime == dtime:
									print(dtime)
									scene = elem[0].text
									trans_type = elem[1].text
									print(scene)
									print(trans_type)
									elem[2].text = '1'
									message={"request-type" : "SetCurrentTransition" , "message-id" : "SetCurrentTransition" ,"transition-name":trans_type};
									ws.send(json.dumps(message))
									message = {"request-type" : "SetCurrentScene" , "message-id" : "SetCurrentScene" , "scene-name" : scene};
									ws.send(json.dumps(message))
									tree.write(xmlfile)
									time.sleep(1) #prevent read error
						time.sleep(0.5) #no need 100's loops a second
						# export scene names and transition names.
						timenow = time.strftime("%M%S",time.localtime())
						if timenow == exporttime:
							ws.send(json.dumps(GetSceneList))
							ws.send(json.dumps(GetTransitionList))
							time.sleep(1) #prevent multiple exports
			thread.start_new_thread(run, ())

		if __name__ == "__main__":
			#websocket.enableTrace(True)
			ws = websocket.WebSocketApp("ws://{}:{}".format(host, port),on_message = on_message,on_error = on_error,on_close = on_close)
			ws.on_open = on_open
			ws.run_forever()

	except Exception:
		print("Connection error")
		time.sleep(10)





