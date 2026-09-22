"""Read-only display of real flybrain spikes; the layout is schematic."""
from pathlib import Path
import time

import numpy as np
import pygame

from rl.env import CatDisasterEnv
from game.design import THEMES, DesignRenderer, plaque

WIDTH = 420
BG = (8, 16, 22)
CARD = (13, 25, 32)
LINE = (32, 57, 65)
WHITE = (222, 238, 237)
MUTED = (108, 138, 146)
CYAN = (76, 232, 217)
AMBER = (255, 180, 97)
PINK = (255, 102, 131)


class BrainPanel:
    def __init__(self, controller, design="original"):
        self.controller = controller
        self.design = design
        self.font = pygame.font.SysFont('Menlo,DejaVu Sans Mono', 11)
        self.small = pygame.font.SysFont('Menlo,DejaVu Sans Mono', 9)
        self.big = pygame.font.SysFont('Menlo,DejaVu Sans Mono', 22, bold=True)
        self.avatar = pygame.transform.smoothscale(pygame.image.load(
            Path(__file__).parent / 'visuals' / 'fruitfly-avatar.png'), (112, 112))
        self.surface = pygame.Surface((WIDTH, 480))
        self.glow = pygame.Surface((WIDTH, 480), pygame.SRCALPHA)
        self.last_tick = -1
        self.ids = np.array([], dtype=int)
        self.points, self.edges, self.colors = [], [], []
        self.names = []
        if controller is not None:
            self._sample(controller.brain)
        self.lit_at = np.full(len(self.ids), -1000.0)

    def _sample(self, brain):
        # A separate RNG keeps visualization entirely out of the policy's RNG.
        rng = np.random.default_rng(47)
        seeds = rng.choice(brain.n, min(80, brain.n), replace=False)
        selected = set(map(int, seeds))
        for source in seeds:
            targets = brain.indices[brain.indptr[source]:brain.indptr[source + 1]]
            if len(targets):
                selected.update(map(int, rng.choice(targets, min(2, len(targets)), replace=False)))
        sensory = set()
        motor = set()
        for row in self.controller.inputs:
            for group in row:
                ids = group[np.linspace(0, len(group) - 1, min(10, len(group)), dtype=int)]
                sensory.update(map(int, ids))
        for row in self.controller.outputs:
            for group in row:
                motor.update(map(int, group))
        selected.update(sensory | motor)
        self.ids = np.array(sorted(selected), dtype=int)
        lookup = {int(neuron): i for i, neuron in enumerate(self.ids)}
        for neuron in self.ids:
            self.names.append(f"{brain.cell_type[neuron]} / {brain.side[neuron]} / #{neuron}")
            side = str(brain.side[neuron])
            right = side == 'R' if side in ('L', 'R') else bool(rng.integers(2))
            angle, radius = rng.uniform(0, 2 * np.pi), np.sqrt(rng.uniform(0, 1))
            self.points.append((int((282 if right else 138) + 64 * radius * np.cos(angle)),
                                int(249 + 45 * radius * np.sin(angle))))
            self.colors.append(PINK if neuron in motor else AMBER if neuron in sensory else CYAN)
        # Only real synaptic edges between the displayed neurons are drawn.
        for source in self.ids:
            targets = brain.indices[brain.indptr[source]:brain.indptr[source + 1]]
            self.edges.extend((lookup[int(source)], lookup[int(target)])
                              for target in targets if int(target) in lookup)

    def text(self, text, x, y, color=MUTED, font=None):
        self.surface.blit((font or self.font).render(str(text), True, color), (x, y))

    def bar(self, label, values, x, y, color, scale=1):
        self.text(label, x, y, MUTED, self.small)
        for side, value in enumerate(values):
            bx = x + side * 84
            pygame.draw.rect(self.surface, LINE, (bx, y + 16, 72, 4), border_radius=2)
            fill = round(72 * min(max(float(value) / scale, 0), 1))
            if fill:
                pygame.draw.rect(self.surface, color, (bx, y + 16, fill, 4), border_radius=2)
            self.text(f"{'L' if side == 0 else 'R'} {value:.1f}", bx, y + 23, color, self.small)

    def _draw_original(self):
        s = self.surface
        s.fill(BG)
        ctrl = self.controller
        pygame.draw.line(s, LINE, (0, 0), (0, 480))
        pygame.draw.circle(s, CYAN if ctrl else MUTED, (25, 25), 3)
        self.text('FRUIT FLY / NEURAL LIVE', 37, 18, WHITE)
        self.text('01', 378, 18, CYAN)
        s.blit(self.avatar, (20, 50))
        pygame.draw.rect(s, LINE, (20, 50, 112, 112), 1, border_radius=6)
        self.text('DROSOPHILA', 151, 53, CYAN, self.small)
        self.text(f'{ctrl.brain.n:,}' if ctrl else 'OFFLINE', 150, 67, WHITE, self.big)
        self.text('NEURONS / FROZEN CONNECTOME', 151, 94, MUTED, self.small)
        count = ctrl.spike_count if ctrl else 0
        self.text(f'{count:,}', 150, 111, AMBER, self.big)
        window_ms = round(ctrl.sample_seconds * 1000) if ctrl else 0
        self.text(f'SPIKES / LAST {window_ms} ms', 151, 141, MUTED, self.small)

        self._draw_network()
        drive = ctrl.last_drive if ctrl else np.zeros((2, 2))
        rates = ctrl.rates if ctrl else np.zeros((2, 2))
        self.bar('SENSE / TARGET', drive[:, 0], 20, 340, AMBER)
        self.bar('SENSE / THREAT', drive[:, 1], 224, 340, AMBER)
        self.bar('DNa02 / STEER Hz', rates[:, 0], 20, 385, CYAN, 25)
        self.bar('DNp01 / BARK Hz', rates[:, 1], 224, 385, PINK, 25)
        pygame.draw.rect(s, (20, 48, 49), (20, 439, 380, 28), border_radius=5)
        action = ctrl.last_action.name.replace('_', ' + ') if ctrl else 'RANDOM'
        self.text(f'MORTY > {action}', 31, 447, WHITE)
        return s

    def _draw_network(self):
        """Draw directly into the final panel in every theme, on every frame."""
        s = self.surface
        now = time.monotonic()
        ctrl = self.controller
        if ctrl is not None and ctrl.telemetry_tick != self.last_tick:
            if ctrl.telemetry_tick < self.last_tick:
                self.lit_at.fill(-1000)
            self.last_tick = ctrl.telemetry_tick
            if ctrl.telemetry_tick:
                self.lit_at[np.isin(self.ids, ctrl.last_spikes)] = now
        pulse = np.exp(-np.maximum(0, now - self.lit_at) / 0.13)
        pygame.draw.rect(s, CARD, (20, 176, 380, 151), border_radius=8)
        self.text('L', 33, 211, MUTED, self.small)
        self.text('R', 379, 211, MUTED, self.small)
        self.text(f'LIVE SPIKES / {len(self.ids)} SAMPLED CELLS', 31, 184, MUTED, self.small)
        self.glow.fill((0, 0, 0, 0))
        for a, b in self.edges:
            level = float(min(pulse[a], pulse[b]))
            col = (28, int(47 + 48 * level), int(54 + 42 * level))
            pygame.draw.aaline(s, col, self.points[a], self.points[b])
        for i, point in enumerate(self.points):
            strength = float(pulse[i])
            color = self.colors[i]
            if strength > 0.04:
                pygame.draw.circle(self.glow, (*color, int(45 * strength)), point, 8)
                pygame.draw.circle(self.glow, (*color, int(95 * strength)), point, 4)
            col = tuple(int(35 + (c - 35) * max(0.12, strength)) for c in color)
            pygame.draw.circle(s, col, point, 2 if strength > 0.1 else 1)
        s.blit(self.glow, (0, 0))
        caption = 'SCHEMATIC LAYOUT / REAL SYNAPSES'
        mx, my = pygame.mouse.get_pos()
        mx -= pygame.display.get_surface().get_width() - WIDTH
        for i, (px, py) in enumerate(self.points):
            if (mx - px) ** 2 + (my - py) ** 2 < 49:
                caption = self.names[i][:48]
                pygame.draw.circle(s, WHITE, (px, py), 6, 1)
                break
        self.text(caption, 31, 311, MUTED, self.small)

    def draw(self):
        if self.design == 'original':
            return self._draw_original()
        t = THEMES[self.design]
        s = self.surface
        s.fill(t.bg)
        for y in range(0,480,21):
            pygame.draw.line(s,t.panel,(5,y),(415,y+4),2)
        plaque(s,(7,7,406,466),t)
        pygame.draw.rect(s,t.accent,(20,17,380,25),border_radius=3)
        self.text("LARISSA'S FLY-O-MATIC",31,23,t.bg)
        self.text('MK.01',355,23,t.bg,self.small)
        paper=pygame.Surface((122,126))
        paper.fill(t.ink)
        paper.blit(self.avatar,(5,5))
        portrait=pygame.transform.rotate(paper,-3)
        s.blit(portrait,(22,48))
        self.text('SPECIMEN / DO NOT FEED',165,57,t.secondary,self.small)
        ctrl=self.controller
        self.text(f'{ctrl.brain.n:,}' if ctrl else 'OFFLINE',165, 73,t.ink,self.big)
        self.text('CELLS IN THIS LITTLE MENACE',165,101,t.muted,self.small)
        self.text(f'{ctrl.spike_count:,}' if ctrl else '0',165,116,t.accent,self.big)
        ms=round(ctrl.sample_seconds*1000) if ctrl else 0
        self.text(f'SPIKES / {ms} ms',165,143,t.muted,self.small)
        plaque(s,(14,171,392,160),t,fill=t.screen)
        self._draw_network()
        # Chunky instrument scales replace the generic dashboard bars.
        drive=ctrl.last_drive if ctrl else np.zeros((2,2))
        rates=ctrl.rates if ctrl else np.zeros((2,2))
        rows=[('TARGET SIGHTED',drive[:,0],20,341,t.secondary,1),
              ('DANGER NEARBY',drive[:,1],224,341,t.secondary,1),
              ('TURN / DNa02 Hz',rates[:,0],20,386,t.accent,25),
              ('BARK / DNp01 Hz',rates[:,1],224,386,t.accent,25)]
        for name,values,x,y,color,scale in rows:
            self.text(name,x,y,t.ink,self.small)
            for side,value in enumerate(values):
                bx=x+84*side
                for tick in range(10):
                    lit=value/scale >= (tick+1)/10
                    pygame.draw.rect(s,color if lit else t.bg,(bx+tick*7,y+14,5,6))
                self.text(f"{'L' if side==0 else 'R'} {value:.1f}",bx,y+24,t.muted,self.small)
        pygame.draw.rect(s,t.accent,(20,429,380,24),border_radius=3)
        action=ctrl.last_action.name.replace('_',' + ') if ctrl else 'RANDOM'
        self.text('MORTY > '+action,31,435,t.bg)
        self.text('F1: DESIGNS   /   HOVER A CELL   /   ESC: EXIT',52,455,t.muted,self.small)
        return s


class FlyPanelEnv(CatDisasterEnv):
    """Wider spectator window; environment observations remain the game only."""
    def __init__(self, controller, design="original", **kwargs):
        super().__init__(render_mode='human', **kwargs)
        self.panel = BrainPanel(controller, design)
        self.set_design(design)

    def set_design(self, design):
        self.design = design
        self.panel.design = design
        self.view_renderer = DesignRenderer(self.assets, self.config, design)

    def _open_window(self):
        self._window = pygame.display.set_mode((self.config.screen_width + WIDTH,
                                               self.config.screen_height))
        pygame.display.set_caption('Morty & Rick / Fruit Fly Neural Live')

    def _render_human(self):
        if self._window is None:
            self._open_window()
        self._window.blit(self.view_renderer.draw(self.engine), (0, 0))
        self._window.blit(self.panel.draw(), (self.config.screen_width, 0))
        pygame.event.pump()
        pygame.display.flip()
