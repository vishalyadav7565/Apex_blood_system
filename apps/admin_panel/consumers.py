from channels.generic.websocket import AsyncJsonWebsocketConsumer

class RequestConsumer(AsyncJsonWebsocketConsumer):

    async def connect(self):
        print("🔥 REQUEST WS CONNECTED")

        await self.channel_layer.group_add(
            "requests",
            self.channel_name
        )

        await self.accept()

    async def disconnect(self, close_code):
        print("❌ REQUEST WS DISCONNECTED")

        await self.channel_layer.group_discard(
            "requests",
            self.channel_name
        )

    async def send_update(self, event):
        print("📨 WS EVENT:", event)

        await self.send_json(event["data"])