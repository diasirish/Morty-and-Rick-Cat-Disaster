"""Presentation themes. Neither simulation nor RL observations use preferences."""
from dataclasses import dataclass
import json
from pathlib import Path

import pygame

from .render import Renderer


@dataclass(frozen=True)
class Theme:
    name: str
    subtitle: str
    bg: tuple
    panel: tuple
    ink: tuple
    accent: tuple
    secondary: tuple
    muted: tuple
    screen: tuple


THEMES = {
    'original': Theme('Original', 'Your original yard, sprites and HUD.',
                      (8,16,22), (13,25,32), (222,238,237), (76,232,217),
                      (255,180,97), (108,138,146), (13,25,32)),
    'backyard': Theme('Backyard Deluxe', 'Warm sunset. Paper labels. Homemade fly machine.',
                      (47,30,26), (93,56,40), (253,226,175), (222,235,118),
                      (255,157,88), (194,158,118), (19,35,28)),
    'midnight': Theme('Midnight Mayhem', 'Moonlit yard. Purple shadows. Electric blue barks.',
                      (18,23,42), (35,44,69), (229,230,250), (152,211,246),
                      (237,162,211), (151,159,192), (15,26,42)),
}
SETTINGS = Path(__file__).resolve().parent.parent / 'runs' / 'design.json'


def load_design(path=SETTINGS):
    try:
        key = json.loads(Path(path).read_text()).get('design')
        return key if key in THEMES else 'backyard'
    except (OSError, ValueError, TypeError, AttributeError):
        return 'backyard'


def save_design(key, path=SETTINGS):
    if key not in THEMES:
        raise ValueError(f'Unknown design: {key}')
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    pending = path.with_suffix('.tmp')
    pending.write_text(json.dumps({'design': key}) + '\n')
    pending.replace(path)


def label(s, text, pos, size=20, color=(255,255,255), bold=False):
    font = pygame.font.SysFont('Avenir Next,DejaVu Sans', size, bold=bold)
    s.blit(font.render(text, True, color), pos)


def plaque(s, rect, theme, fill=None):
    rect = pygame.Rect(rect)
    pygame.draw.rect(s, (8,10,13), rect.move(3,4), border_radius=6)
    pygame.draw.rect(s, fill or theme.panel, rect, border_radius=6)
    pygame.draw.rect(s, theme.muted, rect, 2, border_radius=6)
    for x in (rect.left + 7, rect.right - 8):
        for y in (rect.top + 7, rect.bottom - 8):
            pygame.draw.circle(s, theme.bg, (x,y), 2)


class DesignRenderer(Renderer):
    def __init__(self, assets, config, design='original'):
        super().__init__(assets, config)
        self.design = design
        self.theme = THEMES[design]
        self._backdrop = None
        self._font = pygame.font.SysFont('Avenir Next,DejaVu Sans', 17, bold=True)
        self._small = pygame.font.SysFont('Avenir Next,DejaVu Sans', 11, bold=True)

    def backdrop(self):
        if self._backdrop is None:
            s = pygame.Surface(self.surface.get_size())
            image = self.assets.image('background')
            if image is not None:
                s.blit(image, (0,0))
            else:
                s.fill(self.theme.bg)
            if self.design == 'midnight':
                s.fill((125,147,208), special_flags=pygame.BLEND_RGB_MULT)
                wash = pygame.Surface(s.get_size(), pygame.SRCALPHA)
                wash.fill((14,22, 60, 44))
                s.blit(wash, (0,0))
                pygame.draw.circle(s, (211,216,233), (437,40), 18)
                pygame.draw.circle(s, (37,43,66), (443,35), 17)
            else:
                wash = pygame.Surface(s.get_size(), pygame.SRCALPHA)
                for y in range(s.get_height()):
                    pygame.draw.line(wash, (242,162,79,max(0,20-y//16)), (0,y),(s.get_width(),y))
                s.blit(wash,(0,0))
            self._backdrop = s
        return self._backdrop

    def draw(self, engine, highscore=None):
        if self.design == 'original':
            return super().draw(engine, highscore)
        s = self.surface
        s.blit(self.backdrop(), (0,0))
        shadow = pygame.Surface(s.get_size(), pygame.SRCALPHA)
        for actor in [engine.dog] + list(engine.cats):
            pygame.draw.ellipse(shadow, (7,10,17,100),
                                (int(actor.x)+6, int(actor.y+actor.height)-6, max(8,actor.width-12), 9))
        s.blit(shadow,(0,0))
        if engine.food.present:
            self._draw_food(s,engine.food)
        if engine.larissa is not None and engine.larissa.active:
            self._draw_larissa(s,engine.larissa)
        for cat in engine.cats:
            self._draw_cat(s,cat)
        self._draw_dog(s,engine)
        if self.config.barks_visible:
            for bark in engine.barks:
                for px,py in bark.projectiles:
                    pygame.draw.circle(s, self.theme.secondary, (int(px),int(py)), 7, 1)
                    pygame.draw.circle(s, self.theme.accent, (int(px),int(py)), 4)
                    pygame.draw.circle(s, self.theme.ink, (int(px)-1,int(py)-1), 1)
        self._draw_hud(s,engine,highscore)
        return s

    def _draw_hud(self,s,engine,highscore):
        if self.design == 'original':
            return super()._draw_hud(s,engine,highscore)
        t=self.theme
        plaque(s,(12,10,179, 40),t)
        s.blit(self._small.render('CAT DISASTER',True,t.muted),(26,15))
        s.blit(self._font.render(f'CATS  {engine.score:02d}',True,t.ink),(26,28))
        plaque(s,(453,10,174,40),t)
        text = f'BEST  {highscore:02d}' if highscore is not None else 'MORTY / FLY PILOT'
        s.blit(self._small.render(text,True,t.ink),(467,16))
        pygame.draw.rect(s,t.bg,(467,35,144,4),border_radius=2)
        progress=min(1,engine.score/max(1,self.config.cats_before_boss))
        pygame.draw.rect(s,t.accent,(467,35,int(progress*144),4),border_radius=2)
        if engine.done:
            veil=pygame.Surface(s.get_size(),pygame.SRCALPHA)
            veil.fill((8,10,17,110))
            s.blit(veil,(0,0))
            plaque(s,(155,179,330,110),t)
            text='YARD SAVED!' if engine.won else 'CAT-ASTROPHE!'
            label(s,text,(182,192),30,t.accent,True)
            label(s,f'{engine.score} cats stopped. Another round?',(182,240),15,t.ink)


def draw_menu(screen, assets, heading, options, selected, design):
    t=THEMES[design]
    bg=assets.image('background')
    if bg is not None:
        screen.blit(pygame.transform.scale(bg,screen.get_size()),(0,0))
    else:
        screen.fill(t.bg)
    shade=pygame.Surface(screen.get_size(),pygame.SRCALPHA)
    shade.fill((*t.bg,180))
    screen.blit(shade,(0,0))
    cx=screen.get_width()//2
    plaque(screen,(cx-237,57,474,345),t)
    label(screen,'MORTY & RICK',(cx-200,77),17,t.secondary,True)
    label(screen,heading,(cx-200,108),32,t.ink,True)
    for i,option in enumerate(options):
        rect=pygame.Rect(cx-200,172+i*46,400,38)
        if i==selected:
            pygame.draw.rect(screen,t.accent,rect,border_radius=4)
        label(screen,('>  ' if i==selected else '   ')+option,(rect.x+10,rect.y+7),18,
              t.bg if i==selected else t.ink,True)
    label(screen,'ARROWS / ENTER    |    ESC BACK',(cx-174,423),13,t.muted)


def design_loop(screen, assets, current, path=SETTINGS):
    """Live game preview; only Enter/Apply saves. Escape cancels."""
    from .engine import GameEngine
    from .config import GameConfig
    from .entities import CatState
    keys=list(THEMES)
    selected=keys.index(current)
    clock=pygame.time.Clock()
    cfg=GameConfig(intro_enabled=False)
    engine=GameEngine(cfg)
    engine.reset(seed=17)
    engine.cats=[CatState(x=170,y=140),CatState(x=370,y=225,color_id=1)]
    renderers={key:DesignRenderer(assets,cfg,key) for key in keys}
    width=screen.get_width()
    left=(width-600)//2
    cards=[pygame.Rect(left+i*202, 70,194,57) for i in range(3)]
    apply=pygame.Rect(left+385,424,215,38)
    error = None
    while True:
        for event in pygame.event.get():
            if event.type==pygame.QUIT:
                return 'quit'
            if event.type==pygame.KEYDOWN:
                if event.key==pygame.K_ESCAPE:
                    return current
                if event.key in (pygame.K_LEFT,pygame.K_a):
                    selected=(selected-1)%3
                if event.key in (pygame.K_RIGHT,pygame.K_d):
                    selected=(selected+1)%3
                if event.key==pygame.K_RETURN:
                    try:
                        save_design(keys[selected],path)
                    except OSError:
                        error='Cannot save design. Check folder permissions.'
                    else:
                        return keys[selected]
            if event.type==pygame.MOUSEBUTTONDOWN and event.button==1:
                for i,rect in enumerate(cards):
                    if rect.collidepoint(event.pos): selected=i
                if apply.collidepoint(event.pos):
                    try:
                        save_design(keys[selected],path)
                    except OSError:
                        error='Cannot save design. Check folder permissions.'
                    else:
                        return keys[selected]
        key=keys[selected]
        t=THEMES[key]
        screen.fill(t.bg)
        label(screen,'PICK YOUR DISASTER',(left,22),28,t.ink,True)
        for i,rect in enumerate(cards):
            pygame.draw.rect(screen,t.accent if i==selected else t.panel,rect,border_radius=5)
            label(screen,THEMES[keys[i]].name,(rect.x+10,rect.y+17),16,t.bg if i==selected else t.ink,True)
        preview=pygame.transform.smoothscale(renderers[key].draw(engine),(352,264))
        screen.blit(preview,(left,143))
        plaque(screen,(left+366,143,234,264),t)
        label(screen,'DESIGN NOTES',(left+384,162),15,t.secondary,True)
        notes={'original':['Original artwork','Classic score label','Original neural panel'],
               'backyard':['Warm backyard light','Soft sprite shadows','Paper + wood fly panel'],
               'midnight':['Moonlit colour grade','Electric bark effects','Night-shift fly panel']}[key]
        for i,line in enumerate(notes):
            label(screen,line,(left+384,207+i*34),13,t.ink)
        label(screen,'Gameplay stays the same.',(left+384,351),12,t.muted)
        label(screen,'F1 opens this in fly demo.',(left+384,373),12,t.muted)
        pygame.draw.rect(screen,t.accent,apply,border_radius=4)
        label(screen,'APPLY DESIGN  >',(apply.x+18,apply.y+9),15,t.bg,True)
        label(screen,'LEFT / RIGHT   ESC: CANCEL',(left,436),12,t.muted)
        if error: label(screen,error,(left,466),11,t.secondary)
        pygame.display.flip()
        clock.tick(30)
