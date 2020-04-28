from asgiref.sync import async_to_sync
from channels.generic.websocket import JsonWebsocketConsumer

from .utils import *
from .models import Game


class GameConsumer(JsonWebsocketConsumer):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.game = None
        self.connected = False

    def connect(self):
        try:
            self.game = Game.objects.get(id=self.scope["url_route"]["kwargs"]["game_id"])
        except Game.DoesNotExist:
            return self.close()

        if not self.game.playing:
            return self.close()

        self.connected = True
        self.accept()

        async_to_sync(self.channel_layer.group_add)(
            self.game.channels_group_name, self.channel_name
        )

    def disconnect(self, code):
        self.connected = False
        super().disconnect(code=code)
        self.close()

    def game_update(self, event):
        self.update_game()

    def game_log(self, event):
        self.send_log()

    def game_error(self, event):
        self.send_error()

    def update_game(self):
        if self.connected:
            self.game.refresh_from_db()
            game = serialize_game_info(self.game)
            self.send_json(game)
            if game['game_over']:
                self.disconnect(code=0)

    def send_log(self):
        if self.connected:
            log = self.game.logs.latest()
            has_access = log.game.black.user == self.scope["user"] if log.player == "Black" else log.game.white.user == self.scope["user"]
            if has_access:
                self.send_json(serialize_game_log(log))

    def send_error(self):
        if self.connected:
            self.send_json(serialize_game_error(self.game.errors.latest()))