import os, sys, random, pygame

# --------------- Config chung -----------------
pygame.init()
pygame.mixer.quit()

SCREEN_W, SCREEN_H = 1280, 720
SCREEN = pygame.display.set_mode((SCREEN_W, SCREEN_H))
CLOCK = pygame.time.Clock()
FPS = 60

WHITE = (255, 255, 255)
HUD_BG = (0, 0, 0, 140)

FONT = pygame.font.SysFont("arial", 36)
SMALL_FONT = pygame.font.SysFont("arial", 28)

ASSET_DIR = "assets"
GRAPHIC_DIR = os.path.join(ASSET_DIR, "graphic")
CARD_DIR = os.path.join(ASSET_DIR, "card")

def load_image(path, scale=None):
    img = pygame.image.load(path).convert_alpha()
    if scale:
        img = pygame.transform.smoothscale(img, scale)
    return img

def try_load(path, fallback_size=None, text=""):
    try:
        return load_image(path, fallback_size)
    except Exception:
        surf = pygame.Surface(fallback_size or (200, 80), pygame.SRCALPHA)
        surf.fill((60, 60, 60, 220))
        if text:
            t = SMALL_FONT.render(text, True, WHITE)
            rect = t.get_rect(center=(surf.get_width()/2, surf.get_height()/2))
            surf.blit(t, rect)
        return surf

class ImageButton:
    def __init__(self, image, pos, center=True):
        self.image = image
        self.rect = self.image.get_rect()
        if center: self.rect.center = pos
        else: self.rect.topleft = pos
    def draw(self, screen): screen.blit(self.image, self.rect)
    def is_hover(self): return self.rect.collidepoint(pygame.mouse.get_pos())
    def handle_event(self, event):
        return event.type == pygame.MOUSEBUTTONDOWN and event.button == 1 and self.is_hover()

class Card:
    def __init__(self, image, rect, id_):
        self.image, self.rect, self.id = image, rect, id_
        self.flipped, self.matched = False, False
    def draw(self, screen, back_color=(200,200,220)):
        if self.matched or self.flipped: screen.blit(self.image, self.rect)
        else:
            pygame.draw.rect(screen, back_color, self.rect, border_radius=12)
            pygame.draw.rect(screen, (80,80,100), self.rect, 3, border_radius=12)
    def click(self,pos): return self.rect.collidepoint(pos) and not self.matched

# --------------- Định nghĩa level -----------------
LEVELS = {
    1: {"grid": (2,2), "time":30, "moves":6},
    2: {"grid": (4,4), "time":75, "moves":26},
    3: {"grid": (6,6), "time":150, "moves":54},
    4: {"grid": (8,8), "time":240, "moves":90},
    5: {"grid": (10,10), "time":360, "moves":120},
    6: {"grid": (12,12), "time":480, "moves":180},
}

# --------------- Load asset UI -----------------
BG = try_load(os.path.join(GRAPHIC_DIR,"background.png"),(SCREEN_W,SCREEN_H))
LOGO = try_load(os.path.join(GRAPHIC_DIR,"logo.png"),(int(SCREEN_W*0.7),int(SCREEN_H*0.25)))
MENU_IMG = try_load(os.path.join(GRAPHIC_DIR,"menu.png"),(int(SCREEN_W*0.8),int(SCREEN_H*0.35)))

PLAY_BTN_IMG = try_load(os.path.join(GRAPHIC_DIR,"play.png"),(int(SCREEN_W*0.75),int(SCREEN_H*0.28)))
QUIT_BTN_MENU_IMG = try_load(os.path.join(GRAPHIC_DIR,"quit.png"),(int(SCREEN_W*0.75),int(SCREEN_H*0.28)))
QUIT_BTN_LEVEL_IMG = try_load(os.path.join(GRAPHIC_DIR,"quit.png"),(int(SCREEN_W*0.32),int(SCREEN_H*0.18)))
QUIT_BTN_INGAME_IMG = try_load(os.path.join(GRAPHIC_DIR,"quit.png"),(int(SCREEN_W*0.19),int(SCREEN_H*0.13)))

CHOOSE_LEVEL_LOGO = try_load(os.path.join(GRAPHIC_DIR,"chooselevel.png"),(int(SCREEN_W*0.65),int(SCREEN_H*0.35)))
LEVEL_IMGS = {i: try_load(os.path.join(GRAPHIC_DIR,f"level{i}.png"),(int(SCREEN_W*0.7),int(SCREEN_H*0.4))) for i in range(1,7)}

PAUSE_IMG = try_load(os.path.join(GRAPHIC_DIR,"pause.png"),(int(SCREEN_W*0.35),int(SCREEN_H*0.15)))
CONTINUE_IMG = try_load(os.path.join(GRAPHIC_DIR,"continue.png"),(int(SCREEN_W*0.35),int(SCREEN_H*0.15)))

WIN_BG = try_load(os.path.join(GRAPHIC_DIR,"winbg.png"),(SCREEN_W,SCREEN_H))
NEXTLEVEL_IMG = try_load(os.path.join(GRAPHIC_DIR,"nextlevel.png"),(int(SCREEN_W*0.16),int(SCREEN_H*0.1)))
LOSE_BG = try_load(os.path.join(GRAPHIC_DIR,"losebg.png"),(SCREEN_W,SCREEN_H))
TRYAGAIN_IMG = try_load(os.path.join(GRAPHIC_DIR,"tryagain.png"),(int(SCREEN_W*0.16),int(SCREEN_H*0.1)))

CARD_FILES = ["apple.png","banana.png","cat.png","dog.png","lion.png","tiger.png","wolf.png","zebra.png",
              "cherry.png","grape.png","orange1.png","orange2.png","peach.png","pear.png","watermelon.png","strawberry.png"]

STATE_MENU, STATE_LEVEL_SELECT, STATE_PLAYING, STATE_WIN, STATE_LOSE = "menu","level_select","playing","win","lose"

def load_card_image(name, size):
    path = os.path.join(CARD_DIR, name)
    return try_load(path, size)

def centered_positions(cols, rows, card_w, card_h, padding=16, top_offset=120):
    total_w = cols*card_w+(cols-1)*padding
    total_h = rows*card_h+(rows-1)*padding
    start_x=(SCREEN_W-total_w)//2
    start_y=(SCREEN_H-total_h)//2+top_offset//2
    return [pygame.Rect(start_x+c*(card_w+padding), start_y+r*(card_h+padding), card_w, card_h)
            for r in range(rows) for c in range(cols)]

class MatchGame:
    def __init__(self):
        self.state=STATE_MENU; self.level=1; self.cards=[]; self.first_pick=None
        self.moves_left=0; self.time_left=0; self.start_ticks=0; self.pause_overlay=False

        self.play_btn=ImageButton(PLAY_BTN_IMG,(SCREEN_W//2,int(SCREEN_H*0.6)))
        self.quit_btn_menu=ImageButton(QUIT_BTN_MENU_IMG,(SCREEN_W//2,int(SCREEN_H*0.8)))

        # Level select buttons
        positions=[(int(SCREEN_W*0.3),int(SCREEN_H*0.52)),(int(SCREEN_W*0.5),int(SCREEN_H*0.52)),
                   (int(SCREEN_W*0.7),int(SCREEN_H*0.52)),(int(SCREEN_W*0.3),int(SCREEN_H*0.70)),
                   (int(SCREEN_W*0.49),int(SCREEN_H*0.69)),(int(SCREEN_W*0.69),int(SCREEN_H*0.70))]
        self.level_btns=[(i+1,ImageButton(LEVEL_IMGS[i+1],positions[i])) for i in range(6)]
        self.quit_btn_level=ImageButton(QUIT_BTN_LEVEL_IMG,(SCREEN_W-QUIT_BTN_LEVEL_IMG.get_width()-10,
                                                           SCREEN_H-QUIT_BTN_LEVEL_IMG.get_height()-10),center=False)

        self.pause_btn=ImageButton(PAUSE_IMG,(int(SCREEN_W*0.09),int(SCREEN_H*0.07)))
        self.continue_btn=ImageButton(CONTINUE_IMG,(SCREEN_W//2,SCREEN_H//2))
        self.quit_btn_ingame = ImageButton(
            QUIT_BTN_INGAME_IMG,
            (SCREEN_W - QUIT_BTN_INGAME_IMG.get_width() - 10, int(SCREEN_H*0.01)),
            center=False
        )

        self.nextlevel_btn = ImageButton(NEXTLEVEL_IMG,(SCREEN_W//2,int(SCREEN_H*0.66)))
        self.quit_btn_win = ImageButton(QUIT_BTN_MENU_IMG,(SCREEN_W//2,int(SCREEN_H*0.78)))
        self.tryagain_btn = ImageButton(TRYAGAIN_IMG,(SCREEN_W//2,int(SCREEN_H*0.66)))
        self.quit_btn_lose = ImageButton(QUIT_BTN_MENU_IMG,(SCREEN_W//2,int(SCREEN_H*0.78)))

    # ---------- Setup level ----------
    def setup_level(self, level):
        config = LEVELS[level]
        cols, rows = config["grid"]
        self.moves_left = config["moves"]
        self.time_left = config["time"]
        self.start_ticks = pygame.time.get_ticks()
        self.pause_overlay = False
        self.first_pick = None

        hud_h = int(SCREEN_H*0.12)
        avail_w = int(SCREEN_W*0.86)
        avail_h = SCREEN_H - hud_h - int(SCREEN_H*0.08)
        padding = 18
        card_w = (avail_w - padding*(cols-1)) // cols
        card_h = (avail_h - padding*(rows-1)) // rows
        size = min(card_w, card_h)
        card_w = card_h = size

        rects = centered_positions(cols, rows, card_w, card_h, padding, top_offset=hud_h)

        pair_count = (cols*rows)//2
        if pair_count > len(CARD_FILES):
            choices = random.choices(CARD_FILES, k=pair_count)
        else:
            choices = random.sample(CARD_FILES, pair_count)

        images=[]
        for name in choices:
            img = load_card_image(name,(card_w,card_h))
            images.extend([(name,img),(name,img)])
        random.shuffle(images)

        self.cards=[Card(img,rect,id_=name) for rect,(name,img) in zip(rects,images)]

    def update_timer(self):
        now = pygame.time.get_ticks()
        elapsed = (now - self.start_ticks)//1000
        return max(0,self.time_left - elapsed)

    def all_matched(self): return all(c.matched for c in self.cards)

    def handle_card_flip(self,pos):
        if self.pause_overlay: return
        for card in self.cards:
            if card.click(pos) and not card.flipped:
                card.flipped=True
                if self.first_pick is None:
                    self.first_pick=card
                else:
                    self.moves_left=max(0,self.moves_left-1)
                    second=card
                    if second.id==self.first_pick.id:
                        second.matched=True; self.first_pick.matched=True
                        self.first_pick=None
                    else:
                        pygame.time.set_timer(pygame.USEREVENT+1,600,loops=1)
                        self.pending_hide=(self.first_pick,second)
                        self.first_pick=None
                break
    # ---------- Event handling ----------
    def handle_events(self, events):
        for event in events:
            if event.type == pygame.QUIT:
                pygame.quit(); sys.exit()

            if self.state == STATE_MENU:
                if self.play_btn.handle_event(event):
                    self.state = STATE_LEVEL_SELECT
                elif self.quit_btn_menu.handle_event(event):
                    pygame.quit(); sys.exit()

            elif self.state == STATE_LEVEL_SELECT:
                if self.quit_btn_level.handle_event(event):
                    self.state = STATE_MENU
                for idx, btn in self.level_btns:
                    if btn.handle_event(event):
                        self.level = idx
                        self.setup_level(idx)
                        self.state = STATE_PLAYING

            elif self.state == STATE_PLAYING:
                if self.pause_btn.handle_event(event):
                    self.pause_overlay = True
                elif self.quit_btn_ingame.handle_event(event):
                    self.state = STATE_LEVEL_SELECT
                if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                    self.handle_card_flip(event.pos)
                if event.type == pygame.USEREVENT+1 and hasattr(self,"pending_hide"):
                    a,b=self.pending_hide
                    if a and b:
                        a.flipped=False; b.flipped=False
                    del self.pending_hide

            elif self.state == STATE_WIN:
                if self.nextlevel_btn.handle_event(event):
                    next_lv=min(max(LEVELS.keys()),self.level+1)
                    self.level=next_lv; self.setup_level(next_lv)
                    self.state=STATE_PLAYING
                elif self.quit_btn_win.handle_event(event):
                    self.state=STATE_MENU

            elif self.state == STATE_LOSE:
                if self.tryagain_btn.handle_event(event):
                    self.setup_level(self.level); self.state=STATE_PLAYING
                elif self.quit_btn_lose.handle_event(event):
                    self.state=STATE_MENU

            if self.state==STATE_PLAYING and self.pause_overlay:
                if self.continue_btn.handle_event(event):
                    self.start_ticks=pygame.time.get_ticks()-(self.time_left-self.update_timer())*1000
                    self.pause_overlay=False

        if self.state==STATE_PLAYING and not self.pause_overlay:
            t_remain=self.update_timer()
            if t_remain<=0 or self.moves_left<=0:
                self.state=STATE_WIN if self.all_matched() else STATE_LOSE
            elif self.all_matched():
                self.state=STATE_WIN

    # ---------- Drawing ----------
    def draw_hud(self,screen,level):
        bar=pygame.Surface((SCREEN_W,int(SCREEN_H*0.12)),pygame.SRCALPHA)
        bar.fill(HUD_BG); screen.blit(bar,(0,0))
        t_remain=self.update_timer()
        level_text=SMALL_FONT.render(f"Level {level}",True,WHITE)
        time_text=SMALL_FONT.render(f"Time: {t_remain}s",True,WHITE)
        moves_text=SMALL_FONT.render(f"Moves: {self.moves_left}",True,WHITE)
        screen.blit(level_text,(int(SCREEN_W*0.16),int(SCREEN_H*0.04)))
        screen.blit(time_text,(int(SCREEN_W*0.32),int(SCREEN_H*0.04)))
        screen.blit(moves_text,(int(SCREEN_W*0.50),int(SCREEN_H*0.04)))
        self.pause_btn.draw(screen); self.quit_btn_ingame.draw(screen)

    def draw_menu(self):
        SCREEN.blit(BG,(0,0))
        SCREEN.blit(MENU_IMG,MENU_IMG.get_rect(center=(SCREEN_W//2+20,SCREEN_H//2-60)))
        SCREEN.blit(LOGO,LOGO.get_rect(center=(SCREEN_W//2,int(SCREEN_H*0.20))))
        self.play_btn.draw(SCREEN); self.quit_btn_menu.draw(SCREEN)

    def draw_level_select(self):
        SCREEN.blit(BG,(0,0))
        SCREEN.blit(CHOOSE_LEVEL_LOGO,CHOOSE_LEVEL_LOGO.get_rect(center=(SCREEN_W//2,int(SCREEN_H*0.18))))
        for _,btn in self.level_btns: btn.draw(SCREEN)
        self.quit_btn_level.draw(SCREEN)

    def draw_playing(self):
        SCREEN.blit(BG,(0,0)); self.draw_hud(SCREEN,self.level)
        for card in self.cards: card.draw(SCREEN)
        if self.pause_overlay:
            overlay=pygame.Surface((SCREEN_W,SCREEN_H),pygame.SRCALPHA)
            overlay.fill((0,0,0,160)); SCREEN.blit(overlay,(0,0))
            self.continue_btn.draw(SCREEN)

    def draw_win(self):
        SCREEN.blit(WIN_BG,(0,0))
        msg=FONT.render("You Win!",True,WHITE)
        SCREEN.blit(msg,msg.get_rect(center=(SCREEN_W//2,int(SCREEN_H*0.44))))
        self.nextlevel_btn.draw(SCREEN); self.quit_btn_win.draw(SCREEN)

    def draw_lose(self):
        SCREEN.blit(LOSE_BG,(0,0))
        msg=FONT.render("You Lose!",True,WHITE)
        SCREEN.blit(msg,msg.get_rect(center=(SCREEN_W//2,int(SCREEN_H*0.44))))
        self.tryagain_btn.draw(SCREEN); self.quit_btn_lose.draw(SCREEN)

    # ---------- Main loop ----------
    def run(self):
        while True:
            events=pygame.event.get(); self.handle_events(events)
            if self.state==STATE_MENU: self.draw_menu()
            elif self.state==STATE_LEVEL_SELECT: self.draw_level_select()
            elif self.state==STATE_PLAYING: self.draw_playing()
            elif self.state==STATE_WIN: self.draw_win()
            elif self.state==STATE_LOSE: self.draw_lose()
            pygame.display.flip(); CLOCK.tick(FPS)

# --------------- Main -----------------
if __name__=="__main__":
    pygame.mouse.set_visible(True)
    game=MatchGame(); game.run()
