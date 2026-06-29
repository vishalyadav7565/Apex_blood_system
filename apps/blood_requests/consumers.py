from channels.generic.websocket import AsyncJsonWebsocketConsumer

class RequestConsumer(AsyncJsonWebsocketConsumer):

    async def connect(self):

        print("🔥 WS CONNECT REQUEST")

        self.hospital_id = self.scope["url_route"]["kwargs"].get(
            "hospital_id"
        )

        self.user_id = self.scope["url_route"]["kwargs"].get(
            "user_id"
        )

        if self.hospital_id:
            self.group_name = f"hospital_{self.hospital_id}"

        elif self.user_id:
            self.group_name = f"user_{self.user_id}"

        else:
            self.group_name = "requests"

        print("GROUP:", self.group_name)

        await self.channel_layer.group_add(
            self.group_name,
            self.channel_name
        )

        await self.accept()

        print("✅ CONNECTED:", self.group_name)

    async def disconnect(self, close_code):

        print("❌ DISCONNECTED:", close_code)

        await self.channel_layer.group_discard(
            self.group_name,
            self.channel_name
        )

    async def send_update(self, event):

        print("📨 EVENT RECEIVED:", event)

        await self.send_json(event["data"])