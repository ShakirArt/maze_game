import random
import sys
from collections import deque

import pygame

WALL, PATH = 1, 0


# Maze generation + solving

def generate_maze(rooms_rows, rooms_cols):

    rows, cols = 2 * rooms_rows + 1, 2 * rooms_cols + 1
    grid = [[WALL] * cols for _ in range(rows)]

    grid[1][1] = PATH
    stack = [(1, 1)]  

    while stack:
        r, c = stack[-1]
        options = []
        for dr, dc in ((-2, 0), (2, 0), (0, -2), (0, 2)):
            nr, nc = r + dr, c + dc
            if 0 < nr < rows - 1 and 0 < nc < cols - 1 and grid[nr][nc] == WALL:
                options.append((dr, dc))

        if options:
            dr, dc = random.choice(options)
            grid[r + dr // 2][c + dc // 2] = PATH 
            grid[r + dr][c + dc] = PATH            
            stack.append((r + dr, c + dc))
        else:
            stack.pop()

    return grid


def solve(grid, start, goal):
    prev = {start: None}
    queue = deque([start])
    while queue:
        cur = queue.popleft()
        if cur == goal:
            break
        r, c = cur
        for dr, dc in ((-1, 0), (1, 0), (0, -1), (0, 1)):
            nxt = (r + dr, c + dc)
            if grid[nxt[0]][nxt[1]] == PATH and nxt not in prev:
                prev[nxt] = cur
                queue.append(nxt)

    path, node = [], goal if goal in prev else None
    while node is not None:
        path.append(node)
        node = prev[node]
    return path[::-1]



# Player

def hits_wall(grid, rect, tile):
    first_row, last_row = rect.top // tile, (rect.bottom - 1) // tile
    first_col, last_col = rect.left // tile, (rect.right - 1) // tile
    for r in range(first_row, last_row + 1):
        for c in range(first_col, last_col + 1):
            if grid[r][c] == WALL:
                return True
    return False


class Player:
    def __init__(self, row, col, tile):
        self.tile = tile
        self.size = int(tile * 0.6)
        self.speed = tile * 9 
        offset = (tile - self.size) // 2
        self.rect = pygame.Rect(col * tile + offset, row * tile + offset, self.size, self.size)
        self.x, self.y = float(self.rect.x), float(self.rect.y)

    @property
    def cell(self):
        return self.rect.centery // self.tile, self.rect.centerx // self.tile

    def move(self, dx, dy, grid):
        t = self.tile

        self.x += dx
        self.rect.x = round(self.x)
        if hits_wall(grid, self.rect, t):
            if dx > 0:
                self.rect.right = ((self.rect.right - 1) // t) * t
            elif dx < 0:
                self.rect.left = (self.rect.left // t + 1) * t
            self.x = float(self.rect.x)

        self.y += dy
        self.rect.y = round(self.y)
        if hits_wall(grid, self.rect, t):
            if dy > 0:
                self.rect.bottom = ((self.rect.bottom - 1) // t) * t
            elif dy < 0:
                self.rect.top = (self.rect.top // t + 1) * t
            self.y = float(self.rect.y)


# Game

TILE = 16
ROOMS = 20      
SIDEBAR = 200

COLORS = {
    "path":    (11, 16, 32),
    "wall":    (38, 49, 84),
    "sidebar": (17, 24, 39),
    "panel":   (30, 41, 59),
    "player":  (34, 211, 238),
    "goal":    (244, 114, 182),
    "hint":    (251, 191, 36),
    "text":    (229, 231, 235),
    "muted":   (148, 163, 184),
    "win":     (52, 211, 153),
}


class Game:
    def __init__(self):
        pygame.init()
        self.grid_px = (2 * ROOMS + 1) * TILE
        self.screen = pygame.display.set_mode((self.grid_px + SIDEBAR, self.grid_px))
        pygame.display.set_caption("Maze")
        self.clock = pygame.time.Clock()
        fonts = "segoeui,helveticaneue,helvetica,arial"
        self.big = pygame.font.SysFont(fonts, 40, bold=True)
        self.med = pygame.font.SysFont(fonts, 24, bold=True)
        self.small = pygame.font.SysFont(fonts, 16)
        self.new_game()

    def new_game(self):
        self.grid = generate_maze(ROOMS, ROOMS)
        self.rows, self.cols = len(self.grid), len(self.grid[0])
        self.goal = (self.rows - 2, self.cols - 2)
        self.player = Player(1, 1, TILE)
        self.maze_surface = self.render_maze()
        self.start_ms = pygame.time.get_ticks()
        self.finish_ms = None
        self.show_hint = False
        self.hint_path = []
        self.hint_from = None

    def center(self, cell):
        r, c = cell
        return c * TILE + TILE // 2, r * TILE + TILE // 2

    def render_maze(self):
        surf = pygame.Surface((self.grid_px, self.grid_px))
        surf.fill(COLORS["path"])
        for r, row in enumerate(self.grid):
            for c, tile in enumerate(row):
                if tile == WALL:
                    pygame.draw.rect(surf, COLORS["wall"], (c * TILE, r * TILE, TILE, TILE))
        cx, cy = self.center(self.goal)
        glow = pygame.Surface((TILE * 3, TILE * 3), pygame.SRCALPHA)
        pygame.draw.circle(glow, (*COLORS["goal"], 70), (TILE * 3 // 2, TILE * 3 // 2), TILE)
        surf.blit(glow, (cx - TILE * 3 // 2, cy - TILE * 3 // 2))
        pygame.draw.circle(surf, COLORS["goal"], (cx, cy), int(TILE * 0.32))
        return surf

    @property
    def won(self):
        return self.finish_ms is not None

    def refresh_hint(self):
        if self.show_hint and self.player.cell != self.hint_from:
            self.hint_from = self.player.cell
            self.hint_path = solve(self.grid, self.hint_from, self.goal)

    def handle_input(self, dt):
        keys = pygame.key.get_pressed()
        dx = (keys[pygame.K_RIGHT] or keys[pygame.K_d]) - (keys[pygame.K_LEFT] or keys[pygame.K_a])
        dy = (keys[pygame.K_DOWN] or keys[pygame.K_s]) - (keys[pygame.K_UP] or keys[pygame.K_w])
        step = self.player.speed * dt
        self.player.move(dx * step, dy * step, self.grid)

    def update(self, dt):
        if not self.won:
            self.handle_input(dt)
            if self.player.cell == self.goal:
                self.finish_ms = pygame.time.get_ticks()
        self.refresh_hint()

    def text(self, font, string, color, x, y):
        self.screen.blit(font.render(string, True, COLORS[color]), (x, y))

    def draw(self):
        self.screen.fill(COLORS["sidebar"])
        self.screen.blit(self.maze_surface, (0, 0))

        if self.show_hint and not self.won and len(self.hint_path) > 1:
            points = [self.center(cell) for cell in self.hint_path]
            pygame.draw.lines(self.screen, COLORS["hint"], False, points, 3)

        pygame.draw.rect(self.screen, COLORS["player"], self.player.rect, border_radius=3)

        x = self.grid_px + 24
        elapsed = (self.finish_ms or pygame.time.get_ticks()) - self.start_ms
        secs = elapsed // 1000
        self.text(self.small, "TIME", "muted", x, 28)
        self.text(self.big, f"{secs // 60:02}:{secs % 60:02}", "text", x, 46)

        if self.won:
            self.text(self.med, "You win!", "win", x, 110)
        elif self.show_hint:
            self.text(self.small, "STEPS TO GOAL", "muted", x, 110)
            self.text(self.med, str(max(len(self.hint_path) - 1, 0) // 2), "hint", x, 130)

        for i, (key, label) in enumerate((("WASD / ←↑↓→", "move"), ("H", "toggle hint"), ("R", "new maze"), ("ESC", "quit"))):
            y = self.grid_px - 170 + i * 38
            self.text(self.small, key, "text", x, y)
            self.text(self.small, label, "muted", x, y + 16)

        pygame.display.flip()

    def run(self):
        while True:
            dt = min(self.clock.tick(60) / 1000, 0.05) 
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    pygame.quit()
                    sys.exit()
                if event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_ESCAPE:
                        pygame.quit()
                        sys.exit()
                    elif event.key == pygame.K_r:
                        self.new_game()
                    elif event.key == pygame.K_h:
                        self.show_hint = not self.show_hint
                        self.hint_from = None 
            self.update(dt)
            self.draw()


if __name__ == "__main__":
    Game().run()