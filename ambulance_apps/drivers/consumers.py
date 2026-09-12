from channels.db import database_sync_to_async
from channels.generic.websocket import AsyncJsonWebsocketConsumer

from ambulance_apps.drivers.models import Driver


class DriverConsumer(AsyncJsonWebsocketConsumer):
    """Driver socket for dispatches and driver-specific status updates."""

    async def connect(self):
        self.driver_id = self.scope['url_route']['kwargs']['driver_id']
        self.driver_group = f'driver_{self.driver_id}'
        self.online_group = 'drivers_online'

        is_online = await self._is_online()
        await self.channel_layer.group_add(self.driver_group, self.channel_name)
        if is_online:
            await self.channel_layer.group_add(self.online_group, self.channel_name)
        await self.accept()

    async def disconnect(self, close_code):
        await self.channel_layer.group_discard(self.driver_group, self.channel_name)
        await self.channel_layer.group_discard(self.online_group, self.channel_name)

    async def send_update(self, event):
        await self.send_json(event['data'])

    @database_sync_to_async
    def _is_online(self):
        return Driver.objects.filter(pk=self.driver_id, is_online=True).exists()
