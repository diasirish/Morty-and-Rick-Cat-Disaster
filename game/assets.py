"""Central asset registry with lazy loading and graceful fallbacks.

All file paths live here (they used to be string literals scattered across
characters.py and main.py). Generated assets (Rick, Larissa, the smoothed
background, the cleaned food sprite, Rick's bark) come from
tools/generate_assets.py; if a generated file is missing we fall back to the
nearest original so the game still runs.
"""

import os

import pygame

from .entities import FOOD_H, FOOD_W

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _path(*parts):
    return os.path.join(_ROOT, *parts)


# key -> list of candidate paths, first existing wins
IMAGE_FILES = {
    "background": [
        _path("visuals", "Background_v4_doom_640x480.png"),  # generated, doom palette
        _path("visuals", "Background_v3_640x480.png"),       # generated, smoothed original colors
        _path("visuals", "Background_v2_640x480.png"),       # original MS-Paint
    ],
    "start_screen": [_path("visuals", "Start_Screen.jpg")],
    "dog_morty": [_path("visuals", "Morty_64x60.png")],
    "dog_rick": [
        _path("visuals", "Rick_64x60.png"),              # generated
        _path("visuals", "Morty_64x60.png"),
    ],
    "cat": [_path("visuals", "Cat_ex1_64x57_right.png")],
    "food": [
        _path("visuals", "food_32.png"),                 # generated, transparent
        _path("visuals", "8853301006071_compressed copy.jpg"),
    ],
    "larissa_f1": [_path("visuals", "Larissa_120x180_f1.png")],
    "larissa_f2": [_path("visuals", "Larissa_120x180_f2.png")],
}

SOUND_FILES = {
    "bark_morty": [_path("sounds", "woof_morty_1.wav")],
    "bark_rick": [
        _path("sounds", "woof_rick_1.wav"),              # generated, pitched up
        _path("sounds", "woof_morty_1.wav"),
    ],
    "food": [_path("sounds", "smw_power-up_appears.wav")],
    "game_over": [_path("sounds", "puppy_crying.mp3")],
    "round_start": [_path("sounds", "dog-howl-352680.mp3")],
}

CHARACTERS = {
    "morty": {"sprite": "dog_morty", "bark": "bark_morty"},
    "rick": {"sprite": "dog_rick", "bark": "bark_rick"},
}


class Assets:
    def __init__(self):
        self._images: dict = {}
        self._sounds: dict = {}

    # ------------------------------------------------------------------

    def image(self, key, flipped=False, scale=None):
        """Load (and cache) an image; flipped/scaled variants are cached too,
        so per-frame draws never re-transform surfaces."""
        cache_key = (key, flipped, scale)
        if cache_key in self._images:
            return self._images[cache_key]

        if (key, False, None) not in self._images:
            surface = self._load_image(key)
            self._images[(key, False, None)] = surface
        surface = self._images[(key, False, None)]
        if surface is not None:
            if scale is not None:
                surface = pygame.transform.scale(surface, scale)
            if flipped:
                surface = pygame.transform.flip(surface, True, False)
        self._images[cache_key] = surface
        return surface

    def _load_image(self, key):
        for path in IMAGE_FILES[key]:
            if os.path.exists(path):
                surface = pygame.image.load(path)
                # convert_alpha needs a display; skip when running headless
                if pygame.display.get_surface() is not None:
                    surface = surface.convert_alpha()
                if key == "food" and surface.get_size() != (FOOD_W, FOOD_H):
                    surface = pygame.transform.smoothscale(surface, (FOOD_W, FOOD_H))
                return surface
        return None

    # ------------------------------------------------------------------

    def sound(self, key):
        """Load (and cache) a sound; returns None when the mixer is not
        initialized (headless RL runs never init the mixer)."""
        if key in self._sounds:
            return self._sounds[key]
        sound = None
        if pygame.mixer.get_init():
            for path in SOUND_FILES[key]:
                if os.path.exists(path):
                    sound = pygame.mixer.Sound(path)
                    break
        self._sounds[key] = sound
        return sound

    def character_sprite_key(self, character):
        return CHARACTERS[character.lower()]["sprite"]

    def character_bark_key(self, character):
        return CHARACTERS[character.lower()]["bark"]
