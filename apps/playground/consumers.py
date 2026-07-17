import json
from channels.generic.websocket import AsyncWebsocketConsumer


class PlaygroundConsumer(AsyncWebsocketConsumer):
    """WebSocket consumer for the agent playground canvas."""

    async def connect(self):
        self.session_id = self.scope['url_route']['kwargs']['session_id']
        self.group_name = f'playground_{self.session_id}'
        await self.channel_layer.group_add(self.group_name, self.channel_name)
        await self.accept()
        await self.send(text_data=json.dumps({
            'type': 'connection_established',
            'session_id': self.session_id,
            'message': 'Connected to playground session'
        }))

    async def disconnect(self, close_code):
        await self.channel_layer.group_discard(self.group_name, self.channel_name)

    async def receive(self, text_data):
        data = json.loads(text_data)
        msg_type = data.get('type', 'unknown')

        if msg_type == 'run_graph':
            # Placeholder: echo back with streaming simulation
            await self.send(text_data=json.dumps({
                'type': 'output',
                'content': f'Compiling graph with {len(data.get("nodes", []))} nodes...',
                'stream': True
            }))
            await self.send(text_data=json.dumps({
                'type': 'output',
                'content': 'Execution complete.',
                'stream': False
            }))
        else:
            await self.send(text_data=json.dumps({
                'type': 'echo',
                'received': data
            }))
