from channels.generic.websocket import AsyncJsonWebsocketConsumer

class VerificationConsumer(AsyncJsonWebsocketConsumer):
    async def connect(self):
        self.session_code = self.scope["url_route"]["kwargs"].get("session_code")
        self.group_name = f"verif_{self.session_code}"

        print(f"🔥 WS CONNECT VERIFICATION SESSION: {self.session_code}")

        await self.channel_layer.group_add(
            self.group_name,
            self.channel_name
        )
        await self.accept()

        # Emit PHONE_CONNECTED event upon connection
        await self.channel_layer.group_send(
            self.group_name,
            {
                "type": "verification_status",
                "status": "PHONE_CONNECTED",
                "session_code": self.session_code
            }
        )

    async def disconnect(self, close_code):
        print(f"❌ WS DISCONNECTED VERIFICATION SESSION: {self.session_code}")
        # Broadcast PHONE_DISCONNECTED to inform Desktop (Requirement 41)
        await self.channel_layer.group_send(
            self.group_name,
            {
                "type": "verification_status",
                "status": "PHONE_DISCONNECTED",
                "session_code": self.session_code
            }
        )
        await self.channel_layer.group_discard(
            self.group_name,
            self.channel_name
        )

    async def receive_json(self, content):
        """
        Broadcasting real-time verification status updates across desktop & phone
        Supported Events: PHONE_CONNECTED, FRONT_CAPTURED, BACK_CAPTURED, AADHAAR_COMPLETED, SELFIE_CAPTURED, REGISTRATION_COMPLETED, ERROR, SESSION_EXPIRED
        """
        status_val = content.get("status") or content.get("type", "session_update")
        await self.channel_layer.group_send(
            self.group_name,
            {
                "type": "verification_status",
                "status": status_val,
                "session_code": self.session_code,
                "data": content
            }
        )

    async def verification_status(self, event):
        """
        Event handler for verification_status messages sent to group
        """
        payload = event.get("data", {})
        if "type" not in payload:
            payload["type"] = "verification_status"
        if "status" not in payload:
            payload["status"] = event.get("status", "UPDATED")
        payload["session_code"] = self.session_code

        await self.send_json(payload)

    async def session_update(self, event):
        await self.send_json(event["data"])
