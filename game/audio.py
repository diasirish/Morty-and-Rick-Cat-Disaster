"""AudioPlayer: engine events -> sounds.

The engine never plays audio itself (it must run headless at maximum speed
during training); it emits Events instead, and this thin layer turns them
into mixer calls. Only the windowed modes (human play, --render training,
inference) ever construct an AudioPlayer.
"""

from .engine import EventType


class AudioPlayer:
    def __init__(self, assets, character="morty"):
        self.assets = assets
        self.bark_key = assets.character_bark_key(character)

    def handle(self, events):
        for event in events:
            key = self._sound_key(event.type)
            if key is None:
                continue
            sound = self.assets.sound(key)
            if sound is not None:
                sound.play()

    def _sound_key(self, event_type):
        if event_type == EventType.BARK_FIRED:
            return self.bark_key
        return {
            EventType.ROUND_STARTED: "round_start",
            EventType.FOOD_PLACED: "food",
            EventType.CAT_ATE_FOOD: "food",
            EventType.DOG_DIED: "game_over",
        }.get(event_type)
