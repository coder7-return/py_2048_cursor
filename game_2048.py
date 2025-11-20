import json
import os
import random
import sys
from dataclasses import dataclass
from typing import Dict, List, Optional, Set, Tuple

import pygame


GRID_SIZE = 4
TILE_COLORS = {
    0: (204, 192, 179),
    2: (238, 228, 218),
    4: (237, 224, 200),
    8: (242, 177, 121),
    16: (245, 149, 99),
    32: (246, 124, 95),
    64: (246, 94, 59),
    128: (237, 207, 114),
    256: (237, 204, 97),
    512: (237, 200, 80),
    1024: (237, 197, 63),
    2048: (237, 194, 46),
}
BACKGROUND_COLOR = (250, 248, 239)
BOARD_COLOR = (187, 173, 160)
TEXT_COLOR = (119, 110, 101)
LIGHT_TEXT_COLOR = (249, 246, 242)

WINDOW_WIDTH = 600
WINDOW_HEIGHT = 780
BOARD_MARGIN = 32
BOARD_TOP = 210
TILE_GAP = 12
BOARD_SIZE = WINDOW_WIDTH - 2 * BOARD_MARGIN
TILE_SIZE = (BOARD_SIZE - (GRID_SIZE + 1) * TILE_GAP) // GRID_SIZE
ANIMATION_DURATION_MS = 140
SPAWN_ANIMATION_DURATION_MS = 120
BUTTON_WIDTH = 170
BUTTON_HEIGHT = 58
BUTTON_GAP = 24
CONTROL_BUTTON_HEIGHT = 48
CONTROL_BUTTON_PADDING_X = 28
CONTROL_BUTTON_PADDING_Y = 12
CONTROL_BUTTON_GAP = 18
CONTROL_BUTTON_ROW_GAP = 10
HEADER_CONTROL_BUTTONS = [
    ("Restart", "RESTART"),
    ("Quit", "QUIT"),
]
SCORE_STATE_FILE = os.path.join(os.path.dirname(__file__), "score_state.json")


def load_score_state() -> Dict[str, int]:
    if not os.path.exists(SCORE_STATE_FILE):
        return {"best_score": 0, "total_score": 0}
    try:
        with open(SCORE_STATE_FILE, "r", encoding="utf-8") as handler:
            data = json.load(handler)
            return {
                "best_score": int(data.get("best_score", 0)),
                "total_score": int(data.get("total_score", 0)),
            }
    except (OSError, json.JSONDecodeError, ValueError):
        return {"best_score": 0, "total_score": 0}


def save_score_state(best_score: int, total_score: int) -> None:
    try:
        with open(SCORE_STATE_FILE, "w", encoding="utf-8") as handler:
            json.dump({"best_score": best_score, "total_score": total_score}, handler)
    except OSError:
        pass


def reverse(row: List[int]) -> List[int]:
    return list(reversed(row))


def transpose(board: List[List[int]]) -> List[List[int]]:
    return [list(row) for row in zip(*board)]


@dataclass
class TileMove:
    start: Tuple[int, int]
    end: Tuple[int, int]
    value: int
    merged: bool = False


@dataclass
class MoveResult:
    board: List[List[int]]
    score_gain: int
    moved: bool
    moves: List[TileMove]
    spawn: Optional[Tuple[int, int, int]] = None


class Game2048:
    def __init__(self) -> None:
        state = load_score_state()
        self.best_score = state.get("best_score", 0)
        self.total_score = state.get("total_score", 0)
        self.score = 0
        self.board: List[List[int]] = []
        self.game_over = False
        self.won = False
        self.last_spawn: Optional[Tuple[int, int, int]] = None
        self.reset()

    def reset(self) -> None:
        self.board = [[0 for _ in range(GRID_SIZE)] for _ in range(GRID_SIZE)]
        self.score = 0
        self.game_over = False
        self.won = False
        self.last_spawn = None
        self._spawn_tile()
        self._spawn_tile()

    def _spawn_tile(self) -> Optional[Tuple[int, int, int]]:
        empty_cells = [(r, c) for r in range(GRID_SIZE) for c in range(GRID_SIZE) if self.board[r][c] == 0]
        if not empty_cells:
            return None
        r, c = random.choice(empty_cells)
        value = 4 if random.random() < 0.1 else 2
        self.board[r][c] = value
        self.last_spawn = (r, c, value)
        return self.last_spawn

    def _move_left(self, board: List[List[int]]) -> MoveResult:
        new_board: List[List[int]] = []
        total_gain = 0
        moved = False
        moves: List[TileMove] = []

        for r, row in enumerate(board):
            non_zero = [(value, r, c) for c, value in enumerate(row) if value != 0]
            new_row = [0 for _ in range(GRID_SIZE)]
            target = 0
            idx = 0

            while idx < len(non_zero):
                value, sr, sc = non_zero[idx]
                dest_col = target
                if idx + 1 < len(non_zero) and non_zero[idx + 1][0] == value:
                    next_value, nr, nc = non_zero[idx + 1]
                    merged_value = value * 2
                    new_row[dest_col] = merged_value
                    total_gain += merged_value
                    moves.append(TileMove(start=(sr, sc), end=(r, dest_col), value=value, merged=True))
                    moves.append(TileMove(start=(nr, nc), end=(r, dest_col), value=next_value, merged=True))
                    idx += 2
                else:
                    new_row[dest_col] = value
                    moves.append(TileMove(start=(sr, sc), end=(r, dest_col), value=value, merged=False))
                    idx += 1
                target += 1

            if new_row != row:
                moved = True
            new_board.append(new_row)

        return MoveResult(board=new_board, score_gain=total_gain, moved=moved, moves=moves)

    def move(self, direction: str) -> Optional[MoveResult]:
        if direction not in {"LEFT", "RIGHT", "UP", "DOWN"}:
            return None

        if direction == "LEFT":
            result = self._move_left(self.board)
        elif direction == "RIGHT":
            flipped = [reverse(row) for row in self.board]
            result = self._move_left(flipped)
            result.board = [reverse(row) for row in result.board]
            result.moves = [self._mirror_horizontal(move) for move in result.moves]
        elif direction == "UP":
            transposed = transpose(self.board)
            result = self._move_left(transposed)
            result.board = transpose(result.board)
            result.moves = [self._transpose_move(move) for move in result.moves]
        else:  # DOWN
            transposed = transpose(self.board)
            flipped = [reverse(row) for row in transposed]
            result = self._move_left(flipped)
            unflipped = [reverse(row) for row in result.board]
            result.board = transpose(unflipped)
            mirrored = [self._mirror_horizontal(move) for move in result.moves]
            result.moves = [self._transpose_move(move) for move in mirrored]

        if not result.moved:
            return None

        self.board = result.board
        self.score += result.score_gain
        self._apply_score_gain(result.score_gain)

        if any(cell >= 2048 for row in self.board for cell in row):
            self.won = True

        result.spawn = self._spawn_tile()
        self.game_over = not self._can_move()

        return result

    @staticmethod
    def _mirror_horizontal(move: TileMove) -> TileMove:
        return TileMove(
            start=(move.start[0], GRID_SIZE - 1 - move.start[1]),
            end=(move.end[0], GRID_SIZE - 1 - move.end[1]),
            value=move.value,
            merged=move.merged,
        )

    @staticmethod
    def _transpose_move(move: TileMove) -> TileMove:
        return TileMove(
            start=(move.start[1], move.start[0]),
            end=(move.end[1], move.end[0]),
            value=move.value,
            merged=move.merged,
        )

    def _apply_score_gain(self, gain: int) -> None:
        if gain <= 0:
            return
        self.total_score += gain
        if self.score > self.best_score:
            self.best_score = self.score
        save_score_state(self.best_score, self.total_score)

    def current_total(self) -> int:
        return self.total_score

    def _can_move(self) -> bool:
        if any(0 in row for row in self.board):
            return True

        for r in range(GRID_SIZE):
            for c in range(GRID_SIZE - 1):
                if self.board[r][c] == self.board[r][c + 1]:
                    return True

        for c in range(GRID_SIZE):
            for r in range(GRID_SIZE - 1):
                if self.board[r][c] == self.board[r + 1][c]:
                    return True

        return False


class GameApp:
    def __init__(self) -> None:
        pygame.init()
        pygame.display.set_caption("2048 in Python")
        self.screen = pygame.display.set_mode((WINDOW_WIDTH, WINDOW_HEIGHT))
        self.clock = pygame.time.Clock()
        self.font_large = pygame.font.SysFont("arial", 48, bold=True)
        self.font_medium = pygame.font.SysFont("arial", 28, bold=True)
        self.font_small = pygame.font.SysFont("arial", 20)
        self.font_tile_big = pygame.font.SysFont("arial", 36, bold=True)
        self.font_tile_medium = pygame.font.SysFont("arial", 30, bold=True)
        self.font_tile_small = pygame.font.SysFont("arial", 24, bold=True)
        self.font_tile_tiny = pygame.font.SysFont("arial", 20, bold=True)
        self.game = Game2048()
        self.move_animation: Optional[dict] = None
        self.spawn_animation: Optional[dict] = None
        self.pending_spawn: Optional[Tuple[int, int, int]] = None
        self.overlay_buttons: Dict[str, pygame.Rect] = {}
        self.header_buttons: Dict[str, pygame.Rect] = {}
        self.last_gain = 0
        self.last_gain_time = 0
        self.current_time = 0

    def run(self) -> None:
        while True:
            self.clock.tick(60)
            self.current_time = pygame.time.get_ticks()
            self._handle_events()
            self._update_animations()
            self._draw()
            pygame.display.flip()

    def _handle_events(self) -> None:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit()
            if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                if self.game.game_over or self.game.won:
                    self._handle_overlay_click(event.pos)
                    continue
                if self._handle_header_click(event.pos):
                    continue
            if event.type == pygame.KEYDOWN:
                if event.key in (pygame.K_ESCAPE, pygame.K_q):
                    pygame.quit()
                    sys.exit()
                if event.key == pygame.K_r:
                    self._restart_game()
                    return
                if self.game.game_over:
                    continue
                direction = {
                    pygame.K_LEFT: "LEFT",
                    pygame.K_RIGHT: "RIGHT",
                    pygame.K_UP: "UP",
                    pygame.K_DOWN: "DOWN",
                }.get(event.key)
                if direction:
                    self._trigger_action(direction)

    def _record_gain(self, gain: int) -> None:
        if gain <= 0:
            return
        self.last_gain = gain
        self.last_gain_time = self.current_time

    def _restart_game(self) -> None:
        self.game.reset()
        self.move_animation = None
        self.spawn_animation = None
        self.pending_spawn = None
        self.overlay_buttons = {}

    def _handle_overlay_click(self, pos: Tuple[int, int]) -> None:
        replay_rect = self.overlay_buttons.get("replay")
        exit_rect = self.overlay_buttons.get("exit")
        if replay_rect and replay_rect.collidepoint(pos):
            self._restart_game()
        elif exit_rect and exit_rect.collidepoint(pos):
            pygame.quit()
            sys.exit()

    def _handle_header_click(self, pos: Tuple[int, int]) -> bool:
        for action, rect in self.header_buttons.items():
            if rect.collidepoint(pos):
                self._trigger_action(action)
                return True
        return False

    def _trigger_action(self, action: str) -> None:
        if action in {"UP", "DOWN", "LEFT", "RIGHT"}:
            result = self.game.move(action)
            if result:
                self._record_gain(result.score_gain)
                self._start_move_animation(result)
        elif action == "RESTART":
            self._restart_game()
        elif action == "QUIT":
            pygame.quit()
            sys.exit()

    def _draw(self) -> None:
        self.screen.fill(BACKGROUND_COLOR)
        self._draw_header()
        self._draw_board()
        if self.game.game_over or self.game.won:
            self._draw_overlay()
        else:
            self.overlay_buttons = {}

    def _draw_header(self) -> None:
        title_surface = self.font_large.render("2048", True, TEXT_COLOR)
        title_rect = title_surface.get_rect()
        title_rect.topleft = (BOARD_MARGIN, 36)
        self.screen.blit(title_surface, title_rect)

        box_width = 152
        box_height = 68
        box_spacing = 12
        best_rect = pygame.Rect(WINDOW_WIDTH - BOARD_MARGIN - box_width, 36, box_width, box_height)
        total_rect = pygame.Rect(best_rect.x - box_spacing - box_width, 36, box_width, box_height)
        self._draw_score_box(total_rect, "TOTAL", self.game.current_total(), highlight=self._gain_active())
        self._draw_score_box(best_rect, "BEST", self.game.best_score)
        self._draw_gain_indicator(total_rect)

        self._draw_header_buttons(best_rect.bottom + 20)

    def _draw_board(self) -> None:
        pygame.draw.rect(
            self.screen,
            BOARD_COLOR,
            (BOARD_MARGIN, BOARD_TOP, BOARD_SIZE, BOARD_SIZE),
            border_radius=8,
        )
        self._draw_static_tiles()
        if self.move_animation:
            self._draw_move_animation()

    def _draw_static_tiles(self) -> None:
        animated_targets = self._animated_targets()
        for r in range(GRID_SIZE):
            for c in range(GRID_SIZE):
                x, y = self._cell_position(r, c)
                self._draw_tile(0, x, y, TILE_SIZE)

        for r in range(GRID_SIZE):
            for c in range(GRID_SIZE):
                value = self.game.board[r][c]
                if value == 0:
                    continue
                cell = (r, c)
                if cell in animated_targets:
                    continue
                if self.spawn_animation and self.spawn_animation["cell"] == cell:
                    self._draw_spawn_tile(cell, value)
                else:
                    x, y = self._cell_position(r, c)
                    self._draw_tile(value, x, y, TILE_SIZE)

    def _draw_move_animation(self) -> None:
        if not self.move_animation:
            return
        elapsed = self.current_time - self.move_animation["start_time"]
        progress = min(1.0, elapsed / ANIMATION_DURATION_MS)
        for move in self.move_animation["moves"]:
            start_x, start_y = self._cell_position(*move.start)
            end_x, end_y = self._cell_position(*move.end)
            x = start_x + (end_x - start_x) * progress
            y = start_y + (end_y - start_y) * progress
            self._draw_tile(move.value, x, y, TILE_SIZE)

    def _draw_spawn_tile(self, cell: Tuple[int, int], value: int) -> None:
        if not self.spawn_animation:
            return
        elapsed = self.current_time - self.spawn_animation["start_time"]
        progress = min(1.0, elapsed / SPAWN_ANIMATION_DURATION_MS)
        scale = 0.5 + 0.5 * progress
        size = TILE_SIZE * scale
        row, col = cell
        base_x, base_y = self._cell_position(row, col)
        x = base_x + (TILE_SIZE - size) / 2
        y = base_y + (TILE_SIZE - size) / 2
        self._draw_tile(value, x, y, size)
        if progress >= 1.0:
            self.spawn_animation = None

    def _draw_tile(self, value: int, x: float, y: float, size: float) -> None:
        color = TILE_COLORS.get(value, (60, 58, 50))
        rect = pygame.Rect(x, y, size, size)
        pygame.draw.rect(self.screen, color, rect, border_radius=6)
        if value:
            text_color = LIGHT_TEXT_COLOR if value >= 8 else TEXT_COLOR
            font = self._tile_font(value)
            text = font.render(str(value), True, text_color)
            text_rect = text.get_rect(center=rect.center)
            self.screen.blit(text, text_rect)

    def _tile_font(self, value: int) -> pygame.font.Font:
        if value < 100:
            return self.font_tile_big
        if value < 1000:
            return self.font_tile_medium
        if value < 10000:
            return self.font_tile_small
        return self.font_tile_tiny

    def _draw_overlay(self) -> None:
        overlay = pygame.Surface((WINDOW_WIDTH, WINDOW_HEIGHT), pygame.SRCALPHA)
        overlay.fill((255, 255, 255, 200))
        self.screen.blit(overlay, (0, 0))

        if self.game.won and not self.game.game_over:
            message = "You made 2048!"
        elif self.game.won and self.game.game_over:
            message = "Victory & no moves!"
        else:
            message = "Game Over"

        message_surface = self.font_large.render(message, True, TEXT_COLOR)
        message_rect = message_surface.get_rect(center=(WINDOW_WIDTH / 2, WINDOW_HEIGHT / 2 - 80))
        self.screen.blit(message_surface, message_rect)

        detail_surface = self.font_medium.render("Choose an option below", True, TEXT_COLOR)
        detail_rect = detail_surface.get_rect(center=(WINDOW_WIDTH / 2, message_rect.bottom + 30))
        self.screen.blit(detail_surface, detail_rect)

        self._draw_overlay_buttons(detail_rect.bottom + 30)

    def _cell_position(self, row: int, col: int) -> Tuple[float, float]:
        x = BOARD_MARGIN + TILE_GAP + col * (TILE_SIZE + TILE_GAP)
        y = BOARD_TOP + TILE_GAP + row * (TILE_SIZE + TILE_GAP)
        return float(x), float(y)

    def _start_move_animation(self, result: MoveResult) -> None:
        animated_moves = [
            move for move in result.moves if move.start != move.end or move.merged
        ]
        if animated_moves:
            self.move_animation = {
                "moves": animated_moves,
                "start_time": self.current_time,
            }
        else:
            self.move_animation = None

        if result.spawn:
            if self.move_animation:
                self.pending_spawn = result.spawn
            else:
                self.spawn_animation = {
                    "cell": result.spawn[:2],
                    "value": result.spawn[2],
                    "start_time": self.current_time,
                }
                self.pending_spawn = None

    def _animated_targets(self) -> Set[Tuple[int, int]]:
        if not self.move_animation:
            return set()
        return {(move.end[0], move.end[1]) for move in self.move_animation["moves"]}

    def _update_animations(self) -> None:
        if self.move_animation:
            elapsed = self.current_time - self.move_animation["start_time"]
            if elapsed >= ANIMATION_DURATION_MS:
                self.move_animation = None
                if self.pending_spawn:
                    self.spawn_animation = {
                        "cell": self.pending_spawn[:2],
                        "value": self.pending_spawn[2],
                        "start_time": self.current_time,
                    }
                    self.pending_spawn = None
        elif self.pending_spawn:
            self.spawn_animation = {
                "cell": self.pending_spawn[:2],
                "value": self.pending_spawn[2],
                "start_time": self.current_time,
            }
            self.pending_spawn = None

        if self.spawn_animation:
            elapsed = self.current_time - self.spawn_animation["start_time"]
            if elapsed >= SPAWN_ANIMATION_DURATION_MS:
                self.spawn_animation = None

    def _draw_score_box(self, rect: pygame.Rect, label: str, value: int, *, highlight: bool = False) -> None:
        box_color = (205, 190, 170) if highlight else BOARD_COLOR
        pygame.draw.rect(self.screen, box_color, rect, border_radius=8)
        label_surface = self.font_small.render(label, True, LIGHT_TEXT_COLOR)
        label_rect = label_surface.get_rect(center=(rect.centerx, rect.top + label_surface.get_height() / 2 + 6))
        value_surface = self.font_medium.render(str(value), True, LIGHT_TEXT_COLOR)
        value_rect = value_surface.get_rect(center=(rect.centerx, rect.bottom - value_surface.get_height() / 2 - 6))
        self.screen.blit(label_surface, label_rect)
        self.screen.blit(value_surface, value_rect)

    def _gain_active(self) -> bool:
        if self.last_gain <= 0:
            return False
        if self.current_time - self.last_gain_time > 1200:
            self.last_gain = 0
            return False
        return True

    def _draw_gain_indicator(self, anchor: pygame.Rect) -> None:
        if not self._gain_active():
            return
        gain_surface = self.font_small.render(f"+{self.last_gain}", True, (197, 120, 30))
        gain_rect = gain_surface.get_rect(midtop=(anchor.centerx, anchor.bottom + 6))
        self.screen.blit(gain_surface, gain_rect)

    def _draw_header_buttons(self, top_y: float) -> None:
        self.header_buttons = {}
        x = BOARD_MARGIN
        y = top_y
        row_height = 0
        max_width = WINDOW_WIDTH - BOARD_MARGIN
        for label, action in HEADER_CONTROL_BUTTONS:
            text_surface = self.font_medium.render(label, True, TEXT_COLOR)
            width = text_surface.get_width() + CONTROL_BUTTON_PADDING_X * 2
            height = max(CONTROL_BUTTON_HEIGHT, text_surface.get_height() + CONTROL_BUTTON_PADDING_Y * 2)
            if x + width > max_width:
                x = BOARD_MARGIN
                y += row_height + CONTROL_BUTTON_ROW_GAP
                row_height = 0
            rect = pygame.Rect(x, y, width, height)
            row_height = max(row_height, height)
            base_color = (226, 214, 198) if action in {"UP", "DOWN", "LEFT", "RIGHT"} else (196, 180, 160)
            pygame.draw.rect(self.screen, base_color, rect, border_radius=10)
            text_rect = text_surface.get_rect(center=rect.center)
            self.screen.blit(text_surface, text_rect)
            self.header_buttons[action] = rect
            x += width + CONTROL_BUTTON_GAP

    def _draw_overlay_buttons(self, top_y: float) -> None:
        self.overlay_buttons = {}
        total_width = BUTTON_WIDTH * 2 + BUTTON_GAP
        start_x = WINDOW_WIDTH / 2 - total_width / 2
        labels = [("Replay", "replay"), ("Exit", "exit")]
        for idx, (text, key) in enumerate(labels):
            rect = pygame.Rect(start_x + idx * (BUTTON_WIDTH + BUTTON_GAP), top_y, BUTTON_WIDTH, BUTTON_HEIGHT)
            color = BOARD_COLOR if key == "exit" else (146, 123, 99)
            text_color = LIGHT_TEXT_COLOR if key == "replay" else TEXT_COLOR
            pygame.draw.rect(self.screen, color, rect, border_radius=10)
            button_text = self.font_medium.render(text, True, text_color)
            self.screen.blit(button_text, button_text.get_rect(center=rect.center))
            self.overlay_buttons[key] = rect


def main() -> None:
    app = GameApp()
    app.run()


if __name__ == "__main__":
    main()

