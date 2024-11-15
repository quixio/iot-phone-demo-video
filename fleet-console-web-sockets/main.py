import asyncio
import websockets
import os
from quixstreams import Application
from dotenv import load_dotenv
import json
import time

load_dotenv()

class webSocketSource:

    def __init__(self) -> None:
        app = Application(consumer_group="heatmap-web-sockets-v5", auto_offset_reset="latest")
        self._topic = app.topic(name=os.environ["input"])
        self._events_topic = app.topic(name=os.environ["events_topic"])
        
        self._consumer = app.get_consumer()
        self._consumer.subscribe([self._topic.name, self._events_topic.name])
        
        # Holds all client connections partitioned by page.
        self.websocket_connections = {}
        
    async def consume_messages(self):
        commit_time = time.time()

        while True:
            message = self._consumer.poll(1)
            print(message)
            if message is not None:
                value = json.loads(bytes.decode(message.value()))
                key = bytes.decode(message.key())
                for key, client in list(self.websocket_connections.items()):
                    try:
                        value["streamId"] = key
                        await client.send(json.dumps(value))
                    except:
                        print("Connection already closed.")
                        del self.websocket_connections[key]
                    print(f"Send {str(len(self.websocket_connections))} times.")
                
                if time.time() - commit_time > 5:
                    self._consumer.commit(message)

                await asyncio.sleep(0)
            else:
                await asyncio.sleep(1)
                
    async def handle_websocket(self, websocket, path):
        print(path + " user connected.")
        self.websocket_connections[path] = websocket

        try:
            print("Keep the connection open and wait for messages if needed")
            await websocket.wait_closed()
        except Exception as e:
            print(f"Client disconnected with error: {e}")
        finally:
            print("Removing client from connection list")
            if path in self.websocket_connections:
                del self.websocket_connections[path]

    async def start_websocket_server(self):
        print("Listening for websocket connections..")
        server = await websockets.serve(self.handle_websocket, '0.0.0.0', 80)
        await server.wait_closed()

async def main():
    client = webSocketSource()
    asyncio.create_task(client.consume_messages())
    await client.start_websocket_server()

try:
    asyncio.run(main())
except Exception as e:
    print(f"An error occurred: {e}")
