import pygame
import math
from src.utils.settings import load_sprite


class Portal(pygame.sprite.Sprite):
    def __init__(self, pos):
        super().__init__()

        self.pos = pygame.math.Vector2(pos)
        self.base_size = 90
        self.timer = 0

        self.use_sprite = False
        try:
            import os
            if os.path.exists("assets/sprites/portal.png"):
                self.sprite_img = load_sprite("assets/sprites/portal.png", (self.base_size, self.base_size), (100, 0, 200))
                self.use_sprite = True
        except:
            pass

        self.image = pygame.Surface((self.base_size, self.base_size), pygame.SRCALPHA)
        self.rect  = self.image.get_rect(center=pos)

        self._base_portal_vol = 0.06
        try:
            self.portal_sound = pygame.mixer.Sound("assets/sounds/portal.mp3")
            self.portal_sound.set_volume(self._base_portal_vol)
            self.portal_sound.play(-1)
        except:
            self.portal_sound = None

    def apply_volume_scale(self, factor):
        if self.portal_sound:
            self.portal_sound.set_volume(self._base_portal_vol * factor)

    def update(self):
        self.timer += 1
        pulse = math.sin(self.timer * 0.08) * 8
        size  = int(self.base_size + pulse)

        self.image = pygame.Surface((size, size), pygame.SRCALPHA)

        if self.use_sprite:
            scaled = pygame.transform.scale(self.sprite_img, (size, size))
            self.image.blit(scaled, (0, 0))
        else:
            self.draw_procedural_portal(size)

        self.rect = self.image.get_rect(center=self.pos)

    def draw_procedural_portal(self, size):
        cx, cy = size // 2, size // 2
        r = size // 2

        pygame.draw.circle(self.image, (60, 0, 120, 200),  (cx, cy), r)
        pygame.draw.circle(self.image, (130, 0, 220, 220), (cx, cy), int(r * 0.78))

        inner_color_val = int(180 + math.sin(self.timer * 0.12) * 75)
        pygame.draw.circle(self.image, (inner_color_val, 0, 255, 240), (cx, cy), int(r * 0.52))
        pygame.draw.circle(self.image, (220, 180, 255, 255),           (cx, cy), int(r * 0.28))

        for i in range(8):
            angle  = math.radians((self.timer * 3 + i * 45) % 360)
            sx     = cx + int(math.cos(angle) * r * 0.68)
            sy     = cy + int(math.sin(angle) * r * 0.68)
            spark_size = int(3 + math.sin(self.timer * 0.1 + i) * 2)
            pygame.draw.circle(self.image, (255, 200, 255, 200), (sx, sy), spark_size)

    def kill(self):
        if self.portal_sound:
            self.portal_sound.stop()
        super().kill()