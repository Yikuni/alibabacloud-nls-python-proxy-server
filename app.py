import asyncio
import websockets
import threading
import json
import nls

from config import TEST_ACCESS_APPKEY
from util import genToken

class AliConnection:
    def __init__(self, websocket):
        self.user_websocket = websocket
        self.sr = nls.NlsSpeechTranscriber(
            token=genToken(),
            appkey=TEST_ACCESS_APPKEY,
            on_sentence_end=self.on_sentence_end,
        )
        self.sr.start(enable_intermediate_result=True,
                      enable_punctuation_prediction=True,
                      enable_inverse_text_normalization=True)

    # 转发消息
    def forward(self, message):
        self.sr.send_audio(message)

    def close(self):
        self.sr.stop()

    def on_sentence_end(self, message, *args):
        data = json.loads(message)
        print(data["payload"]["result"])
        asyncio.run(self.user_websocket.send(data["payload"]["result"]))


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
        ali_connection = AliConnection(websocket)
        self.connections[websocket] = ali_connection
        print("Connection created")
        return ali_connection

    def close_connection(self, websocket):
        if self.connections[websocket] is None:
            return

        self.connections[websocket].close()
        self.connections.pop(websocket)
        print("Connection Closed")


manager = ConnectionManager()


async def forward_server(websocket):
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


start_server = websockets.serve(forward_server, "localhost", 8765)

asyncio.get_event_loop().run_until_complete(start_server)
asyncio.get_event_loop().run_forever()
