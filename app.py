import asyncio
import time

import websockets
import threading
import json

import config
import nls
import re
import ssl

from config import TEST_ACCESS_APPKEY
from util import genToken

class AliConnection:
    def __init__(self, websocket):
        self.user_websocket = websocket
        self.sr = None
        self.last_timestamp = None
        self.init_sr()
        asyncio.create_task(self.protect_thread())

    def init_sr(self):
        self.sr = nls.NlsSpeechTranscriber(
            token=genToken(),
            appkey=TEST_ACCESS_APPKEY,
            on_sentence_end=self.on_sentence_end,
            on_result_changed=self.on_result_chg,
        )
        self.sr.start(enable_intermediate_result=True,
                      enable_punctuation_prediction=True,
                      enable_inverse_text_normalization=True)
        print("sr_init")
    async def protect_thread(self):
        while True:
            await asyncio.sleep(1)
            if self.last_timestamp is not None and self.sr is not None:
                delta = time.time() - self.last_timestamp
                if delta > 1:
                    self.sr.stop()
                    self.sr = None
                    print("sr_stop")
    # 转发消息
    def forward(self, message):
        self.last_timestamp = time.time()
        if self.sr is None:
            self.init_sr()
        self.sr.send_audio(message)

    def close(self):
        self.sr.stop()

    def on_sentence_end(self, message, *args):
        data = json.loads(message)
        print("sentence end: " + data["payload"]["result"])
        asyncio.run(self.user_websocket.send(data["payload"]["result"]))
        time.sleep(0.01)
        asyncio.run(self.user_websocket.send('\n'))
    def on_result_chg(self, message, *args):
        data = json.loads(message)
        msg = data["payload"]["result"]
        print("sentence chg: " + msg)
        asyncio.run(self.user_websocket.send(msg))


class ConnectionManager:
    def __init__(self):
        self.connections = {}  # key: user websocket, value: AliConnection

    def __contains__(self, item):
        return item in self.connections.keys()

    def __getitem__(self, item):
        if self.__contains__(item):
            return self.connections[item]
        else:
            return None

    def create_connection(self, websocket):
        print("Connection created")
        ali_connection = AliConnection(websocket)
        self.connections[websocket] = ali_connection
        return ali_connection

    def close_connection(self, websocket):
        if self.connections[websocket] is None:
            return

        self.connections[websocket].close()
        self.connections.pop(websocket)
        print("Connection Closed")


manager = ConnectionManager()


async def forward_server(websocket, *args):
    conn = manager[websocket]
    if conn is None:
        # 如果新建对话
        conn = manager.create_connection(websocket)
    try:
        async for message in websocket:
            conn.forward(message)
    except Exception:
        pass
    finally:
        manager.close_connection(websocket)

ssl_context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
ssl_context.load_cert_chain(certfile=config.SSL_CERT, keyfile=config.SSL_KEY)
start_server = websockets.serve(forward_server, "0.0.0.0", 8765, ssl=ssl_context)

print("Server started")
asyncio.get_event_loop().run_until_complete(start_server)
asyncio.get_event_loop().run_forever()
