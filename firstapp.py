"""
Tic Tac Toe game using Pygame and OpenGL with enhanced animations.
"""
from __future__ import annotations
from typing import List, Tuple, Optional, Any, Dict, Union, cast
import sys
import math
import random
import time
import numpy as np
import pygame
import pygame.event
from pygame.locals import (
    DOUBLEBUF, OPENGL, HWSURFACE, 
    GL_MULTISAMPLEBUFFERS, GL_MULTISAMPLESAMPLES,
    FULLSCREEN, RESIZABLE
)
import OpenGL.GL as GL
import OpenGL.GLU as GLU
from OpenGL.GL import *
from OpenGL.GLU import *
import moderngl
import moderngl_window
from PIL import Image, ImageDraw, ImageFilter

ButtonDict = Dict[str, Union[Tuple[float, float, float, float], str, bool, float, Tuple[float, float, float]]]

class Particle:
    def __init__(self, pos, color, size, velocity):
        self.pos = list(pos)
        self.color = color
        self.size = size
        self.velocity = list(velocity)
        self.age = 0
        self.lifetime = random.uniform(0.5, 1.5)

class ParticleSystem:
    def __init__(self):
        self.particles = []
        
    def emit(self, pos, color, count=1, speed=0.1):
        for _ in range(count):
            angle = random.uniform(0, 2 * math.pi)
            velocity = [math.cos(angle) * speed, math.sin(angle) * speed]
            size = random.uniform(0.01, 0.03)
            self.particles.append(Particle(pos, color, size, velocity))
            
    def update(self, dt):
        # Update particle positions and remove dead particles
        self.particles = [p for p in self.particles if p.age < p.lifetime]
        for p in self.particles:
            p.pos[0] += p.velocity[0] * dt
            p.pos[1] += p.velocity[1] * dt
            p.age += dt
            
    def draw(self):
        # Draw all particles
        glEnable(GL_POINT_SMOOTH)
        glPointSize(5.0)
        glBegin(GL_POINTS)
        for p in self.particles:
            alpha = 1.0 - (p.age / p.lifetime)
            glColor4f(p.color[0], p.color[1], p.color[2], alpha)
            glVertex2f(p.pos[0], p.pos[1])
        glEnd()
        glDisable(GL_POINT_SMOOTH)

class TicTacToe:
    """Enhanced Tic Tac Toe game with animations."""

    def __init__(self) -> None:
        """Initialize the game with enhanced UI elements."""
        pygame.init()
        
        # Initialize display with proper flags
        display_flags = DOUBLEBUF | OPENGL | HWSURFACE
        self.display_size = (800, 600)
        self.screen = pygame.display.set_mode(self.display_size, display_flags)
        pygame.display.set_caption("Tic Tac Toe")
        
        # Initialize OpenGL
        GL.glViewport(0, 0, self.display_size[0], self.display_size[1])
        GL.glMatrixMode(GL.GL_PROJECTION)
        GL.glLoadIdentity()
        GL.glOrtho(-1, 1, -1, 1, -1, 1)
        GL.glMatrixMode(GL.GL_MODELVIEW)
        GL.glLoadIdentity()
        GL.glEnable(GL.GL_BLEND)
        GL.glBlendFunc(GL.GL_SRC_ALPHA, GL.GL_ONE_MINUS_SRC_ALPHA)
        
        # Cursor trail system
        self.cursor_trail = []
        self.max_trail_length = 12
        self.trail_fade_speed = 0.1
        self.cursor_smoothing = 0.3
        self.cursor_pos = [0.0, 0.0]
        self.cursor_target = [0.0, 0.0]
        self.cursor_glow_intensity = 0.0
        self.cursor_scale = 1.0
        
        # Game state
        self.board = [[None for _ in range(3)] for _ in range(3)]
        self.current_player = True  # True for player, False for computer
        self.game_over = False
        self.winner = None
        self.in_menu = True
        self.show_winner_screen = False
        self.fade_alpha = 0.0
        self.player_symbol = None
        self.computer_symbol = None
        self.player_color = (0.2, 0.8, 0.2)  # Default green
        self.computer_color = (0.8, 0.2, 0.2)  # Default red
        
        # Animation and timing
        self.animation_progress = 0.0
        self.animation_speed = 0.1
        self.last_move_time = 0.0
        self.move_delay = 0.3
        self.hover_speed = 0.1
        self.grid_animation_speed = 0.1
        self.grid_pulse_intensity = 0.0
        
        # Performance monitoring
        self.fps = 0
        self.frame_count = 0
        self.last_frame_time = time.time()
        
        # Error handling
        self.error_state = False
        self.error_message = ""
        self.recovery_attempts = 0
        self.max_recovery_attempts = 3
        
        # Score tracking
        self.score = {'player': 0, 'computer': 0, 'draws': 0}
        self.move_history = []
        self.last_computer_move = (-1, -1)
        
        # Mouse and hover state
        self.hover_cell = (-1, -1)
        
        # Initialize buttons with proper attributes
        button_width = 0.4
        button_height = 0.18
        button_spacing = 0.06
        menu_y = 0.6
        
        # Initialize game buttons with all required attributes
        self.buttons = {
            'restart': {
                'rect': [0.05, 0.05, button_width, button_height],
                'text': 'RESTART',
                'subtext': 'Press R',
                'color': (0.2, 0.8, 0.2),  # Green
                'hover': False,
                'scale': 1.0,
                'glow': 0.0
            },
            'menu': {
                'rect': [0.3 + button_spacing, 0.05, button_width, button_height],
                'text': 'MENU',
                'subtext': 'Press ESC',
                'color': (0.2, 0.2, 0.8),  # Blue
                'hover': False,
                'scale': 1.0,
                'glow': 0.0
            },
            'undo': {
                'rect': [0.55 + 2 * button_spacing, 0.05, button_width, button_height],
                'text': 'UNDO',
                'subtext': 'Ctrl+Z',
                'color': (0.8, 0.2, 0.2),  # Red
                'hover': False,
                'scale': 1.0,
                'glow': 0.0
            }
        }
        
        # Initialize menu buttons with all required attributes
        self.menu_buttons = {
            'play_x': {
                'rect': [0.3, menu_y, button_width, button_height],
                'text': 'Play as X',
                'subtext': 'First Move',
                'color': (0.8, 0.2, 0.2),  # Red
                'hover': False,
                'scale': 1.0,
                'glow': 0.0
            },
            'play_o': {
                'rect': [0.3, menu_y - button_height - button_spacing, button_width, button_height],
                'text': 'Play as O',
                'subtext': 'Second Move',
                'color': (0.2, 0.2, 0.8),  # Blue
                'hover': False,
                'scale': 1.0,
                'glow': 0.0
            },
            'color_red': {
                'rect': [0.3, menu_y - 2 * (button_height + button_spacing), button_width, button_height],
                'text': 'Red',
                'subtext': 'Classic',
                'color': (0.8, 0.2, 0.2),
                'hover': False,
                'scale': 1.0,
                'glow': 0.0
            },
            'color_blue': {
                'rect': [0.3, menu_y - 3 * (button_height + button_spacing), button_width, button_height],
                'text': 'Blue',
                'subtext': 'Ocean',
                'color': (0.2, 0.2, 0.8),
                'hover': False,
                'scale': 1.0,
                'glow': 0.0
            },
            'color_green': {
                'rect': [0.3, menu_y - 4 * (button_height + button_spacing), button_width, button_height],
                'text': 'Green',
                'subtext': 'Forest',
                'color': (0.2, 0.8, 0.2),
                'hover': False,
                'scale': 1.0,
                'glow': 0.0
            },
            'color_purple': {
                'rect': [0.3, menu_y - 5 * (button_height + button_spacing), button_width, button_height],
                'text': 'Purple',
                'subtext': 'Royal',
                'color': (0.6, 0.2, 0.8),
                'hover': False,
                'scale': 1.0,
                'glow': 0.0
            }
        }

        # Visual effects
        self.particles = ParticleSystem()
        self.last_particle_emit = 0
        self.particle_emit_delay = 0.1
        self.glow_intensity = 0.0
        self.pulse_phase = 0.0

    def resize_viewport(self, width: int, height: int) -> None:
        """Handle window resize events properly."""
        if height == 0:
            height = 1
        
        # Update display size
        self.display_size = (width, height)
        
        # Reset viewport
        GL.glViewport(0, 0, width, height)
        GL.glMatrixMode(GL.GL_PROJECTION)
        GL.glLoadIdentity()
        
        # Maintain aspect ratio
        aspect = width / height
        if width >= height:
            GLU.gluOrtho2D(-1 * aspect, 1 * aspect, -1, 1)
        else:
            GLU.gluOrtho2D(-1, 1, -1 / aspect, 1 / aspect)
        
        GL.glMatrixMode(GL.GL_MODELVIEW)
        GL.glLoadIdentity()

    def handle_error(self, error: Exception) -> bool:
        """Handle errors gracefully with recovery attempts."""
        self.error_state = True
        self.error_message = str(error)
        self.recovery_attempts += 1
        
        if self.recovery_attempts > self.max_recovery_attempts:
            return False
        
        try:
            # Attempt to recover
            pygame.display.quit()
            pygame.display.init()
            self.__init__()
            return True
        except:
            return False

    def reset_game(self) -> None:
        """Reset the game state with improved cleanup."""
        try:
            self.board = [[None for _ in range(3)] for _ in range(3)]
            self.current_player = True
            self.game_over = False
            self.winner = None
            self.in_menu = True
            self.show_winner_screen = False
            self.fade_alpha = 0.0
            self.player_symbol = None
            self.computer_symbol = None
            self.player_color = (0.2, 0.8, 0.2)  # Default green
            self.computer_color = (0.8, 0.2, 0.2)  # Default red
            self.move_history.clear()
            self.score = {'player': 0, 'computer': 0, 'draws': 0}
            self.last_computer_move = (-1, -1)
            
            # If player chose O, let computer make first move
            if not self.current_player and not self.in_menu:
                pygame.time.wait(500)  # Slight delay before computer's first move
                self.computer_move()
                self.current_player = False
                self.animation_progress = 0.0

        except Exception as e:
            print(f"Error resetting game: {e}")
            self.handle_error(e)

    def check_winner(self) -> Optional[str]:
        """
        Check if there's a winner on the board.

        Returns:
            Optional[str]: 'X' for player win, 'O' for computer win, None for no winner
        """
        # Check rows
        for i in range(3):
            if (self.board[i][0] == self.board[i][1] == self.board[i][2] is not None):
                return self.board[i][0]
        
        # Check columns
        for i in range(3):
            if (self.board[0][i] == self.board[1][i] == self.board[2][i] is not None):
                return self.board[0][i]
        
        # Check diagonals
        if (self.board[0][0] == self.board[1][1] == self.board[2][2] is not None):
            return self.board[0][0]
        if (self.board[0][2] == self.board[1][1] == self.board[2][0] is not None):
            return self.board[0][2]
        
        return None

    def is_board_full(self) -> bool:
        """
        Check if the board is full.

        Returns:
            bool: True if the board is full, False otherwise
        """
        return all(all(cell is not None for cell in row) for row in self.board)

    def computer_move(self) -> bool:
        """Make a smart move for the computer."""
        # Store the last move for history
        self.last_computer_move = (-1, -1)
        
        # Try to win
        move = self.find_winning_move(self.computer_symbol)
        if move:
            row, col = move
            self.board[row][col] = self.computer_symbol
            self.last_computer_move = (row, col)
            return True

        # Block player's winning move
        move = self.find_winning_move(self.player_symbol)
        if move:
            row, col = move
            self.board[row][col] = self.computer_symbol
            self.last_computer_move = (row, col)
            return True

        # Try to take center
        if self.board[1][1] is None:
            self.board[1][1] = self.computer_symbol
            self.last_computer_move = (1, 1)
            return True

        # Try to take corners
        corners = [(0, 0), (0, 2), (2, 0), (2, 2)]
        empty_corners = [
            (r, c) for r, c in corners
            if self.board[r][c] is None
        ]
        if empty_corners:
            row, col = random.choice(empty_corners)
            self.board[row][col] = self.computer_symbol
            self.last_computer_move = (row, col)
            return True

        # Take any available edge
        edges = [(0, 1), (1, 0), (1, 2), (2, 1)]
        empty_edges = [
            (r, c) for r, c in edges
            if self.board[r][c] is None
        ]
        if empty_edges:
            row, col = random.choice(empty_edges)
            self.board[row][col] = self.computer_symbol
            self.last_computer_move = (row, col)
            return True

        return False

    def find_winning_move(self, player: str) -> Optional[Tuple[int, int]]:
        """Find a winning move for the specified player."""
        for i in range(3):
            for j in range(3):
                if self.board[i][j] is None:
                    # Try the move
                    self.board[i][j] = player
                    if self.check_winner() == player:
                        self.board[i][j] = None
                        return (i, j)
                    self.board[i][j] = None
        return None

    def draw_board(self) -> None:
        """Draw the game board with improved visual effects."""
        GL.glEnable(GL.GL_BLEND)
        GL.glBlendFunc(GL.GL_SRC_ALPHA, GL.GL_ONE_MINUS_SRC_ALPHA)
        
        current_time = pygame.time.get_ticks() * 0.001
        pulse = (math.sin(current_time) + 1) * 0.5
        
        # Update grid pulse animation
        if self.current_player and not self.game_over:
            self.grid_pulse_intensity += (1.0 - self.grid_pulse_intensity) * self.grid_animation_speed
        else:
            self.grid_pulse_intensity += (0.0 - self.grid_pulse_intensity) * self.grid_animation_speed
        
        # Draw outer border with glow
        glow_size = 0.02 + 0.01 * pulse * self.grid_pulse_intensity
        GL.glColor4f(1, 1, 1, 0.2)
        GL.glBegin(GL.GL_QUADS)
        GL.glVertex3f(-0.9 - glow_size, -0.9 - glow_size, 0)
        GL.glVertex3f(0.9 + glow_size, -0.9 - glow_size, 0)
        GL.glVertex3f(0.9 + glow_size, 0.9 + glow_size, 0)
        GL.glVertex3f(-0.9 - glow_size, 0.9 + glow_size, 0)
        GL.glEnd()
        
        # Draw outer border
        GL.glColor4f(1, 1, 1, 0.8 + 0.2 * pulse * self.grid_pulse_intensity)
        GL.glLineWidth(8)
        GL.glBegin(GL.GL_LINE_LOOP)
        GL.glVertex3f(-0.9, -0.9, 0)
        GL.glVertex3f(0.9, -0.9, 0)
        GL.glVertex3f(0.9, 0.9, 0)
        GL.glVertex3f(-0.9, 0.9, 0)
        GL.glEnd()

        # Draw grid lines with enhanced gradient and glow
        GL.glLineWidth(5)
        for x in [-0.3, 0.3]:
            # Draw glow
            if self.grid_pulse_intensity > 0.01:
                GL.glBegin(GL.GL_QUADS)
                glow_alpha = 0.1 * self.grid_pulse_intensity
                GL.glColor4f(1, 1, 1, glow_alpha)
                GL.glVertex3f(x - glow_size, -0.9, 0)
                GL.glVertex3f(x + glow_size, -0.9, 0)
                GL.glVertex3f(x + glow_size, 0.9, 0)
                GL.glVertex3f(x - glow_size, 0.9, 0)
                GL.glEnd()
            
            # Draw line
            GL.glBegin(GL.GL_LINES)
            GL.glColor4f(1, 1, 1, 0.8 + 0.2 * pulse * self.grid_pulse_intensity)
            GL.glVertex3f(x, 0.9, 0)
            GL.glColor4f(0.7, 0.7, 1, 0.6 + 0.2 * pulse * self.grid_pulse_intensity)
            GL.glVertex3f(x, -0.9, 0)
            GL.glEnd()
            
        for y in [-0.3, 0.3]:
            # Draw glow
            if self.grid_pulse_intensity > 0.01:
                GL.glBegin(GL.GL_QUADS)
                glow_alpha = 0.1 * self.grid_pulse_intensity
                GL.glColor4f(1, 1, 1, glow_alpha)
                GL.glVertex3f(-0.9, y - glow_size, 0)
                GL.glVertex3f(0.9, y - glow_size, 0)
                GL.glVertex3f(0.9, y + glow_size, 0)
                GL.glVertex3f(-0.9, y + glow_size, 0)
                GL.glEnd()
            
            # Draw line
            GL.glBegin(GL.GL_LINES)
            GL.glColor4f(1, 1, 1, 0.8 + 0.2 * pulse * self.grid_pulse_intensity)
            GL.glVertex3f(-0.9, y, 0)
            GL.glColor4f(0.7, 0.7, 1, 0.6 + 0.2 * pulse * self.grid_pulse_intensity)
            GL.glVertex3f(0.9, y, 0)
            GL.glEnd()

    def draw_x(self, x_pos: float, y_pos: float, alpha: float = 1.0) -> None:
        """Draw an X with smooth animation."""
        color = self.player_color if self.player_symbol == 'X' else self.computer_color
        GL.glColor4f(color[0], color[1], color[2], alpha)
        GL.glLineWidth(8)
        GL.glBegin(GL.GL_LINES)
        # Animate each line of the X
        progress = min(1.0, self.animation_progress * 2)
        if progress > 0:
            # First diagonal
            GL.glVertex3f(x_pos - 0.2, y_pos - 0.2, 0)
            GL.glVertex3f(
                x_pos - 0.2 + (0.4 * progress),
                y_pos - 0.2 + (0.4 * progress),
                0
            )
        progress = max(0.0, min(1.0, self.animation_progress * 2 - 1))
        if progress > 0:
            # Second diagonal
            GL.glVertex3f(x_pos + 0.2, y_pos - 0.2, 0)
            GL.glVertex3f(
                x_pos + 0.2 - (0.4 * progress),
                y_pos - 0.2 + (0.4 * progress),
                0
            )
        GL.glEnd()

    def draw_o(self, x_pos: float, y_pos: float, alpha: float = 1.0) -> None:
        """Draw an O with smooth animation."""
        color = self.player_color if self.player_symbol == 'O' else self.computer_color
        GL.glColor4f(color[0], color[1], color[2], alpha)
        GL.glLineWidth(8)
        num_segments = 50
        radius = 0.2
        progress = min(1.0, self.animation_progress * 1.5)
        
        if progress > 0:
            GL.glBegin(GL.GL_LINE_STRIP)
            for i in range(int(num_segments * progress) + 1):
                angle = 2.0 * math.pi * i / num_segments
                GL.glVertex3f(
                    x_pos + math.cos(angle) * radius,
                    y_pos + math.sin(angle) * radius,
                    0
                )
            GL.glEnd()

    def get_cell(self, x_pos: float, y_pos: float) -> Tuple[int, int]:
        """Convert screen coordinates to board cell indices."""
        # Convert from [-1, 1] to [0, 3] range
        board_x = (x_pos + 1) * 1.5
        board_y = (y_pos + 1) * 1.5
        
        # Check if cursor is outside the board
        if board_x < 0 or board_x > 3 or board_y < 0 or board_y > 3:
            return (-1, -1)
        
        # Get cell coordinates
        col = int(board_x)
        row = int(board_y)
        
        # Ensure coordinates are within valid range
        if row < 0 or row > 2 or col < 0 or col > 2:
            return (-1, -1)
            
        return (row, col)

    def animate_effect(self) -> None:
        """Show animation effect after a move."""
        for _ in range(5):
            GL.glClear(GL.GL_COLOR_BUFFER_BIT | GL.GL_DEPTH_BUFFER_BIT)
            self.draw_board()
            GL.glColor3f(1, 1, 0)
            GL.glBegin(GL.GL_QUADS)
            GL.glVertex3f(-1, -1, 0)
            GL.glVertex3f(1, -1, 0)
            GL.glVertex3f(1, 1, 0)
            GL.glVertex3f(-1, 1, 0)
            GL.glEnd()
            pygame.display.flip()
            pygame.time.wait(30)

    def draw_game_over(self) -> None:
        """Draw game over screen."""
        GL.glColor3f(1, 1, 0)
        GL.glBegin(GL.GL_QUADS)
        GL.glVertex3f(-0.5, -0.1, 0)
        GL.glVertex3f(0.5, -0.1, 0)
        GL.glVertex3f(0.5, 0.1, 0)
        GL.glVertex3f(-0.5, 0.1, 0)
        GL.glEnd()

    def draw_winner_screen(self) -> None:
        """Draw an enhanced winner announcement screen with interactive elements."""
        if not self.show_winner_screen:
            return

        # Draw animated background with parallax effect
        current_time = pygame.time.get_ticks() * 0.001
        bg_pulse = (math.sin(current_time * 0.5) + 1) * 0.5
        
        # Draw animated particles in background
        GL.glEnable(GL.GL_BLEND)
        GL.glBlendFunc(GL.GL_SRC_ALPHA, GL.GL_ONE_MINUS_SRC_ALPHA)
        
        # Draw particle effects
        GL.glPointSize(3)
        GL.glBegin(GL.GL_POINTS)
        for i in range(50):
            angle = current_time + i * math.pi / 25
            radius = 0.8 + math.sin(angle * 0.5) * 0.2
            x = math.cos(angle) * radius
            y = math.sin(angle) * radius
            
            if self.winner == self.player_symbol:
                GL.glColor4f(0.2, 1.0, 0.2, (0.3 + 0.2 * math.sin(current_time * 2 + i)) * self.fade_alpha)
            elif self.winner == self.computer_symbol:
                GL.glColor4f(1.0, 0.2, 0.2, (0.3 + 0.2 * math.sin(current_time * 2 + i)) * self.fade_alpha)
            else:
                GL.glColor4f(1.0, 1.0, 0.2, (0.3 + 0.2 * math.sin(current_time * 2 + i)) * self.fade_alpha)
            
            GL.glVertex3f(x, y, 0)
        GL.glEnd()

        # Draw gradient background with pulse
        bg_alpha = min(0.9, self.fade_alpha)
        GL.glBegin(GL.GL_QUADS)
        
        if self.winner == self.player_symbol:
            GL.glColor4f(0.0, 0.2, 0.0, bg_alpha)
        elif self.winner == self.computer_symbol:
            GL.glColor4f(0.2, 0.0, 0.0, bg_alpha)
        else:
            GL.glColor4f(0.2, 0.2, 0.0, bg_alpha)
        GL.glVertex3f(-1, -1, 0)
        GL.glVertex3f(1, -1, 0)
        
        if self.winner == self.player_symbol:
            GL.glColor4f(0.0, 0.3, 0.0, bg_alpha)
        elif self.winner == self.computer_symbol:
            GL.glColor4f(0.3, 0.0, 0.0, bg_alpha)
        else:
            GL.glColor4f(0.3, 0.3, 0.0, bg_alpha)
        GL.glVertex3f(1, 1, 0)
        GL.glVertex3f(-1, 1, 0)
        GL.glEnd()

        if self.fade_alpha >= 0.7:
            message_scale = 1.0 + bg_pulse * 0.1
            
            # Determine message and colors
            if self.winner == self.player_symbol:
                message = "VICTORY!"
                color = (0.2, 1, 0.2)
                glow_color = (0.4, 1, 0.4)
                sub_message = "Congratulations!"
            elif self.winner == self.computer_symbol:
                message = "DEFEAT!"
                color = (1, 0.2, 0.2)
                glow_color = (1, 0.4, 0.4)
                sub_message = "Better luck next time!"
            else:
                message = "DRAW!"
                color = (1, 1, 0.2)
                glow_color = (1, 1, 0.4)
                sub_message = "Close match!"

            # Draw main message with enhanced effects
            x_pos = -0.4
            y_pos = 0.3
            
            # Draw message glow
            num_layers = 5
            for i in range(num_layers):
                offset = 0.02 * (1 + i) * message_scale
                alpha = 0.15 * (1 - i/num_layers) * (0.7 + 0.3 * bg_pulse)
                self.draw_text_base(x_pos, y_pos, message, 2.5 * message_scale, glow_color, alpha)
                
                # Draw radial glow
                angle_step = math.pi * 2 / 8
                for j in range(8):
                    angle = j * angle_step + current_time
                    gx = x_pos + math.cos(angle) * offset * 0.5
                    gy = y_pos + math.sin(angle) * offset * 0.5
                    self.draw_text_base(gx, gy, message, 2.5 * message_scale, glow_color, alpha * 0.5)
            
            # Draw main text with shadow
            shadow_offset = 0.03 * message_scale
            self.draw_text_base(x_pos + shadow_offset, y_pos - shadow_offset, message, 
                              2.5 * message_scale, (0.1, 0.1, 0.1), 0.5)
            self.draw_text_base(x_pos, y_pos, message, 2.5 * message_scale, color, 1.0)

            # Draw sub-message with animation
            sub_scale = 0.8 + bg_pulse * 0.1
            sub_y = 0.0
            self.draw_text_base(-0.35, sub_y, sub_message, 1.2 * sub_scale, color, 0.8)

            # Draw interactive buttons
            button_y = -0.3
            button_spacing = 0.2
            
            # Restart button
            restart_hover = self.is_point_in_rect(
                x_pos, y_pos,
                -0.4, button_y, 0.3, 0.1
            )
            self.draw_popup_button("RESTART", -0.4, button_y, 0.3, 0.1, restart_hover)
            
            # Menu button
            menu_hover = self.is_point_in_rect(
                x_pos, y_pos,
                0.1, button_y, 0.3, 0.1
            )
            self.draw_popup_button("MENU", 0.1, button_y, 0.3, 0.1, menu_hover)

            # Draw score summary
            score_y = -0.5
            score_text = f"SCORE: You {self.score['player']} - {self.score['computer']} Computer"
            self.draw_text_base(-0.35, score_y, score_text, 0.8, (1, 1, 1), 0.8)

    def draw_popup_button(self, text: str, x: float, y: float, w: float, h: float, hover: bool) -> None:
        """Draw an interactive button in the popup screen."""
        current_time = pygame.time.get_ticks() * 0.001
        pulse = (math.sin(current_time * 4) + 1) * 0.5
        
        # Draw button glow when hovered
        if hover:
            glow_size = 0.01 + 0.005 * pulse
            GL.glBegin(GL.GL_QUADS)
            GL.glColor4f(1, 1, 1, 0.2)
            GL.glVertex3f(x - glow_size, y - glow_size, 0)
            GL.glVertex3f(x + w + glow_size, y - glow_size, 0)
            GL.glVertex3f(x + w + glow_size, y + h + glow_size, 0)
            GL.glVertex3f(x - glow_size, y + h + glow_size, 0)
            GL.glEnd()
        
        # Draw button background
        GL.glBegin(GL.GL_QUADS)
        if hover:
            GL.glColor4f(0.8, 0.8, 0.8, 0.9)
        else:
            GL.glColor4f(0.4, 0.4, 0.4, 0.7)
        GL.glVertex3f(x, y, 0)
        GL.glVertex3f(x + w, y, 0)
        GL.glVertex3f(x + w, y + h, 0)
        GL.glVertex3f(x, y + h, 0)
        GL.glEnd()
        
        # Draw button border
        GL.glLineWidth(2)
        GL.glBegin(GL.GL_LINE_LOOP)
        if hover:
            GL.glColor4f(1, 1, 1, 0.8 + 0.2 * pulse)
        else:
            GL.glColor4f(1, 1, 1, 0.5)
        GL.glVertex3f(x, y, 0)
        GL.glVertex3f(x + w, y, 0)
        GL.glVertex3f(x + w, y + h, 0)
        GL.glVertex3f(x, y + h, 0)
        GL.glEnd()
        
        # Draw button text
        text_scale = 0.8
        text_x = x + w/2 - (len(text) * 30 * text_scale * 0.001)
        text_y = y + h/2 - (50 * text_scale * 0.001)
        if hover:
            self.draw_text_base(text_x, text_y, text, text_scale, (1, 1, 0.8), 1.0)
        else:
            self.draw_text_base(text_x, text_y, text, text_scale, (1, 1, 1), 0.8)

    def is_point_in_rect(self, px: float, py: float, x: float, y: float, w: float, h: float) -> bool:
        """Check if a point is inside a rectangle."""
        return x <= px <= x + w and y <= py <= y + h

    def handle_winner_screen_click(self, x_pos: float, y_pos: float) -> None:
        """Handle clicks in the winner screen."""
        if not self.show_winner_screen or self.fade_alpha < 0.7:
            return
            
        button_y = -0.3
        
        try:
            # Check restart button with improved hit detection
            if self.is_point_in_rect(x_pos, y_pos, -0.4, button_y, 0.3, 0.1):
                self.animation_progress = 0.0
                self.fade_alpha = 0.0
                self.reset_game()
                return
                
            # Check menu button with improved hit detection
            if self.is_point_in_rect(x_pos, y_pos, 0.1, button_y, 0.3, 0.1):
                self.animation_progress = 0.0
                self.fade_alpha = 0.0
                self.in_menu = True
                self.reset_game()
                return
        except Exception as e:
            print(f"Error in winner screen click: {e}")
            self.handle_error(e)

    def handle_click(self, x_pos: float, y_pos: float) -> None:
        """Handle mouse click with improved error handling and animations."""
        if self.game_over or not self.current_player:
            return

        try:
            row, col = self.get_cell(x_pos, y_pos)
            if row < 0 or row > 2 or col < 0 or col > 2:
                return

            current_time = time.time()
            if current_time - self.last_move_time < self.move_delay:
                return  # Prevent too rapid clicks

            if self.board[row][col] is None:
                # Player's move with animation
                self.board[row][col] = self.player_symbol
                self.move_history.append((row, col, self.player_symbol))
                self.animation_progress = 0.0
                self.last_move_time = current_time
                
                # Check for win or draw after player's move
                self.winner = self.check_winner()
                if self.winner or self.is_board_full():
                    self.game_over = True
                    self.show_winner_screen = True
                    self.fade_alpha = 0.0
                    self.update_score()
                    return

                # Computer's move with delay and animation
                self.current_player = False
                pygame.time.wait(200)  # Slight delay for better UX
                
                if self.computer_move():
                    comp_row, comp_col = self.last_computer_move
                    self.move_history.append((comp_row, comp_col, self.computer_symbol))
                    self.animation_progress = 0.0
                    
                    # Check for win or draw after computer's move
                    self.winner = self.check_winner()
                    if self.winner or self.is_board_full():
                        self.game_over = True
                        self.show_winner_screen = True
                        self.fade_alpha = 0.0
                        self.update_score()
                
                self.current_player = True

        except Exception as e:
            print(f"Error handling click: {e}")
            self.handle_error(e)

    def draw_current_player(self) -> None:
        """Draw indicator for current player's turn."""
        if not self.game_over and not self.in_menu:
            turn_text = "Your Turn" if self.current_player else "Computer's Turn"
            color = self.player_color if self.current_player else self.computer_color
            self.draw_text(-0.9, 0.85, turn_text, scale=0.7, color=color)

    def draw_pieces(self) -> None:
        """Draw all X's and O's on the board."""
        for i in range(3):
            for j in range(3):
                x_pos = -0.6 + j * 0.6
                y_pos = 0.6 - i * 0.6
                if self.board[i][j] == 'X':
                    self.draw_x(x_pos, y_pos)
                elif self.board[i][j] == 'O':
                    self.draw_o(x_pos, y_pos)

    def draw_button(self, button: dict, active: bool = True) -> None:
        """Draw a button with enhanced visual effects."""
        try:
            x, y, w, h = button['rect']
            hover = button.get('hover', False) and active
            text = button.get('text', '')
            color = button.get('color', (0.5, 0.5, 0.5))
            
            # Draw button background
            GL.glBegin(GL.GL_QUADS)
            if hover:
                GL.glColor4f(color[0] * 1.2, color[1] * 1.2, color[2] * 1.2, 0.8)
            else:
                GL.glColor4f(color[0], color[1], color[2], 0.6)
            GL.glVertex2f(x, y)
            GL.glVertex2f(x + w, y)
            GL.glVertex2f(x + w, y + h)
            GL.glVertex2f(x, y + h)
            GL.glEnd()
            
            # Draw button border
            GL.glLineWidth(2.0)
            GL.glBegin(GL.GL_LINE_LOOP)
            GL.glColor4f(1.0, 1.0, 1.0, 0.8)
            GL.glVertex2f(x, y)
            GL.glVertex2f(x + w, y)
            GL.glVertex2f(x + w, y + h)
            GL.glVertex2f(x, y + h)
            GL.glEnd()
            
            # Draw button text
            text_x = x + w/2 - len(text) * 0.01
            text_y = y + h/2
            
            # Draw text shadow
            GL.glColor4f(0.0, 0.0, 0.0, 0.5)
            self.draw_text_base(text_x + 0.002, text_y - 0.002, text, 1.0, (0, 0, 0), 0.5)
            
            # Draw main text
            if hover:
                text_color = (1.0, 1.0, 1.0)
            else:
                text_color = (0.9, 0.9, 0.9)
            self.draw_text_base(text_x, text_y, text, 1.0, text_color, 1.0)
            
            # Draw subtext if present
            subtext = button.get('subtext', '')
            if subtext:
                subtext_x = x + w/2 - len(subtext) * 0.008  # Smaller text
                subtext_y = y + h/4
                
                # Draw subtext shadow
                self.draw_text_base(subtext_x + 0.002, subtext_y - 0.002, subtext, 0.8, (0, 0, 0), 0.3)
                
                # Draw main subtext
                self.draw_text_base(subtext_x, subtext_y, subtext, 0.8, (0.8, 0.8, 0.8), 0.7)
            
        except Exception as e:
            print(f"Error drawing button: {e}")

    def draw_text_base(self, x: float, y: float, text: str, scale: float, color: Tuple[float, float, float], alpha: float) -> None:
        """Base text drawing function with improved letter spacing."""
        try:
            GL.glColor4f(color[0], color[1], color[2], alpha)
            GL.glLineWidth(2 if alpha == 1.0 else 1.5)
            GL.glPushMatrix()
            GL.glTranslatef(x, y, 0)
            GL.glScalef(scale * 0.001, scale * 0.001, 1)
            
            letter_spacing = 60  # Adjusted for better readability
            for char in text:
                if char == ' ':
                    GL.glTranslatef(letter_spacing * 0.8, 0, 0)
                    continue

                GL.glBegin(GL.GL_LINES)
                self.draw_character(char)
                GL.glEnd()
                GL.glTranslatef(letter_spacing, 0, 0)
            GL.glPopMatrix()
        except Exception as e:
            print(f"Error drawing text base: {e}")
            self.handle_error(e)

    def draw_text(self, x: float, y: float, text: str, scale: float = 1.0, color: Tuple[float, float, float] = (1, 1, 1)) -> None:
        """Draw text with enhanced visual effects."""
        try:
            # Draw text shadow
            shadow_offset = 0.002
            self.draw_text_base(x + shadow_offset, y - shadow_offset, text, scale, (0, 0, 0), 0.5)
            
            # Draw main text
            self.draw_text_base(x, y, text, scale, color, 1.0)
        except Exception as e:
            print(f"Error drawing text: {e}")
            self.handle_error(e)

    def draw_score(self) -> None:
        """Draw the current score."""
        try:
            score_text = f"Score - You: {self.score['player']} Computer: {self.score['computer']} Draws: {self.score['draws']}"
            self.draw_text(-0.9, 0.95, score_text, scale=0.7, color=(1, 1, 1))
        except Exception as e:
            print(f"Error drawing score: {e}")
            self.handle_error(e)

    def update_score(self) -> None:
        """Update the score based on game result."""
        try:
            if self.winner == self.player_symbol:
                self.score['player'] += 1
            elif self.winner == self.computer_symbol:
                self.score['computer'] += 1
            elif self.game_over:
                self.score['draws'] += 1
        except Exception as e:
            print(f"Error updating score: {e}")
            self.handle_error(e)

    def draw_character(self, char: str) -> None:
        """Draw a single character using line segments."""
        try:
            # Character dimensions
            width = 40
            height = 80
            
            # Define character shapes
            if char == 'A':
                GL.glVertex2f(0, 0)
                GL.glVertex2f(width/2, height)
                GL.glVertex2f(width/2, height)
                GL.glVertex2f(width, 0)
                GL.glVertex2f(width/4, height/2)
                GL.glVertex2f(width*3/4, height/2)
            elif char == 'B':
                GL.glVertex2f(0, 0)
                GL.glVertex2f(0, height)
                GL.glVertex2f(0, height)
                GL.glVertex2f(width*2/3, height)
                GL.glVertex2f(width*2/3, height)
                GL.glVertex2f(width, height*2/3)
                GL.glVertex2f(width, height*2/3)
                GL.glVertex2f(width*2/3, height/2)
                GL.glVertex2f(width*2/3, height/2)
                GL.glVertex2f(0, height/2)
                GL.glVertex2f(width*2/3, height/2)
                GL.glVertex2f(width, height/3)
                GL.glVertex2f(width, height/3)
                GL.glVertex2f(width*2/3, 0)
                GL.glVertex2f(width*2/3, 0)
                GL.glVertex2f(0, 0)
            elif char == 'C':
                GL.glVertex2f(width, 0)
                GL.glVertex2f(0, 0)
                GL.glVertex2f(0, 0)
                GL.glVertex2f(0, height)
                GL.glVertex2f(0, height)
                GL.glVertex2f(width, height)
            elif char == 'D':
                GL.glVertex2f(0, 0)
                GL.glVertex2f(0, height)
                GL.glVertex2f(0, height)
                GL.glVertex2f(width*2/3, height)
                GL.glVertex2f(width*2/3, height)
                GL.glVertex2f(width, height/2)
                GL.glVertex2f(width, height/2)
                GL.glVertex2f(width*2/3, 0)
                GL.glVertex2f(width*2/3, 0)
                GL.glVertex2f(0, 0)
            elif char == 'E':
                GL.glVertex2f(width, 0)
                GL.glVertex2f(0, 0)
                GL.glVertex2f(0, 0)
                GL.glVertex2f(0, height)
                GL.glVertex2f(0, height)
                GL.glVertex2f(width, height)
                GL.glVertex2f(0, height/2)
                GL.glVertex2f(width*2/3, height/2)
            elif char == 'F':
                GL.glVertex2f(0, 0)
                GL.glVertex2f(0, height)
                GL.glVertex2f(0, height)
                GL.glVertex2f(width, height)
                GL.glVertex2f(0, height/2)
                GL.glVertex2f(width*2/3, height/2)
            elif char == 'G':
                GL.glVertex2f(width, 0)
                GL.glVertex2f(0, 0)
                GL.glVertex2f(0, 0)
                GL.glVertex2f(0, height)
                GL.glVertex2f(0, height)
                GL.glVertex2f(width, height)
                GL.glVertex2f(width, height)
                GL.glVertex2f(width, height/2)
                GL.glVertex2f(width, height/2)
                GL.glVertex2f(width/2, height/2)
            elif char == 'H':
                GL.glVertex2f(0, 0)
                GL.glVertex2f(0, height)
                GL.glVertex2f(width, 0)
                GL.glVertex2f(width, height)
                GL.glVertex2f(0, height/2)
                GL.glVertex2f(width, height/2)
            elif char == 'I':
                GL.glVertex2f(width/2, 0)
                GL.glVertex2f(width/2, height)
                GL.glVertex2f(0, 0)
                GL.glVertex2f(width, 0)
                GL.glVertex2f(0, height)
                GL.glVertex2f(width, height)
            elif char == 'J':
                GL.glVertex2f(width*3/4, 0)
                GL.glVertex2f(width*3/4, height)
                GL.glVertex2f(0, height/4)
                GL.glVertex2f(width*3/4, 0)
            elif char == 'K':
                GL.glVertex2f(0, 0)
                GL.glVertex2f(0, height)
                GL.glVertex2f(0, height/2)
                GL.glVertex2f(width, height)
                GL.glVertex2f(0, height/2)
                GL.glVertex2f(width, 0)
            elif char == 'L':
                GL.glVertex2f(0, height)
                GL.glVertex2f(0, 0)
                GL.glVertex2f(0, 0)
                GL.glVertex2f(width, 0)
            elif char == 'M':
                GL.glVertex2f(0, 0)
                GL.glVertex2f(0, height)
                GL.glVertex2f(0, height)
                GL.glVertex2f(width/2, height/2)
                GL.glVertex2f(width/2, height/2)
                GL.glVertex2f(width, height)
                GL.glVertex2f(width, height)
                GL.glVertex2f(width, 0)
            elif char == 'N':
                GL.glVertex2f(0, 0)
                GL.glVertex2f(0, height)
                GL.glVertex2f(0, height)
                GL.glVertex2f(width, 0)
                GL.glVertex2f(width, 0)
                GL.glVertex2f(width, height)
            elif char == 'O':
                GL.glVertex2f(0, 0)
                GL.glVertex2f(width, 0)
                GL.glVertex2f(width, 0)
                GL.glVertex2f(width, height)
                GL.glVertex2f(width, height)
                GL.glVertex2f(0, height)
                GL.glVertex2f(0, height)
                GL.glVertex2f(0, 0)
            elif char == 'P':
                GL.glVertex2f(0, 0)
                GL.glVertex2f(0, height)
                GL.glVertex2f(0, height)
                GL.glVertex2f(width*2/3, height)
                GL.glVertex2f(width*2/3, height)
                GL.glVertex2f(width, height*3/4)
                GL.glVertex2f(width, height*3/4)
                GL.glVertex2f(width*2/3, height/2)
                GL.glVertex2f(width*2/3, height/2)
                GL.glVertex2f(0, height/2)
            elif char == 'Q':
                GL.glVertex2f(0, 0)
                GL.glVertex2f(width, 0)
                GL.glVertex2f(width, 0)
                GL.glVertex2f(width, height)
                GL.glVertex2f(width, height)
                GL.glVertex2f(0, height)
                GL.glVertex2f(0, height)
                GL.glVertex2f(0, 0)
                GL.glVertex2f(width/2, height/2)
                GL.glVertex2f(width, 0)
            elif char == 'R':
                GL.glVertex2f(0, 0)
                GL.glVertex2f(0, height)
                GL.glVertex2f(0, height)
                GL.glVertex2f(width*2/3, height)
                GL.glVertex2f(width*2/3, height)
                GL.glVertex2f(width, height*3/4)
                GL.glVertex2f(width, height*3/4)
                GL.glVertex2f(width*2/3, height/2)
                GL.glVertex2f(width*2/3, height/2)
                GL.glVertex2f(0, height/2)
                GL.glVertex2f(width*2/3, height/2)
                GL.glVertex2f(width, 0)
            elif char == 'S':
                GL.glVertex2f(width, 0)
                GL.glVertex2f(width/4, 0)
                GL.glVertex2f(width/4, 0)
                GL.glVertex2f(0, height/4)
                GL.glVertex2f(0, height/4)
                GL.glVertex2f(width/4, height/2)
                GL.glVertex2f(width/4, height/2)
                GL.glVertex2f(width*3/4, height/2)
                GL.glVertex2f(width*3/4, height/2)
                GL.glVertex2f(width, height*3/4)
                GL.glVertex2f(width, height*3/4)
                GL.glVertex2f(width*3/4, height)
                GL.glVertex2f(width*3/4, height)
                GL.glVertex2f(0, height)
            elif char == 'T':
                GL.glVertex2f(width/2, 0)
                GL.glVertex2f(width/2, height)
                GL.glVertex2f(0, height)
                GL.glVertex2f(width, height)
            elif char == 'U':
                GL.glVertex2f(0, height)
                GL.glVertex2f(0, height/4)
                GL.glVertex2f(0, height/4)
                GL.glVertex2f(width/2, 0)
                GL.glVertex2f(width/2, 0)
                GL.glVertex2f(width, height/4)
                GL.glVertex2f(width, height/4)
                GL.glVertex2f(width, height)
            elif char == 'V':
                GL.glVertex2f(0, height)
                GL.glVertex2f(width/2, 0)
                GL.glVertex2f(width/2, 0)
                GL.glVertex2f(width, height)
            elif char == 'W':
                GL.glVertex2f(0, height)
                GL.glVertex2f(width/4, 0)
                GL.glVertex2f(width/4, 0)
                GL.glVertex2f(width/2, height/2)
                GL.glVertex2f(width/2, height/2)
                GL.glVertex2f(width*3/4, 0)
                GL.glVertex2f(width*3/4, 0)
                GL.glVertex2f(width, height)
            elif char == 'X':
                GL.glVertex2f(0, 0)
                GL.glVertex2f(width, height)
                GL.glVertex2f(0, height)
                GL.glVertex2f(width, 0)
            elif char == 'Y':
                GL.glVertex2f(0, height)
                GL.glVertex2f(width/2, height/2)
                GL.glVertex2f(width/2, height/2)
                GL.glVertex2f(width, height)
                GL.glVertex2f(width/2, height/2)
                GL.glVertex2f(width/2, 0)
            elif char == 'Z':
                GL.glVertex2f(0, height)
                GL.glVertex2f(width, height)
                GL.glVertex2f(width, height)
                GL.glVertex2f(0, 0)
                GL.glVertex2f(0, 0)
                GL.glVertex2f(width, 0)
            elif char.isdigit():
                # Numbers
                if char == '0':
                    GL.glVertex2f(0, 0)
                    GL.glVertex2f(width, 0)
                    GL.glVertex2f(width, 0)
                    GL.glVertex2f(width, height)
                    GL.glVertex2f(width, height)
                    GL.glVertex2f(0, height)
                    GL.glVertex2f(0, height)
                    GL.glVertex2f(0, 0)
                elif char == '1':
                    GL.glVertex2f(width/2, 0)
                    GL.glVertex2f(width/2, height)
                    GL.glVertex2f(width/4, height*3/4)
                    GL.glVertex2f(width/2, height)
                elif char == '2':
                    GL.glVertex2f(0, height)
                    GL.glVertex2f(width, height)
                    GL.glVertex2f(width, height)
                    GL.glVertex2f(width, height/2)
                    GL.glVertex2f(width, height/2)
                    GL.glVertex2f(0, height/2)
                    GL.glVertex2f(0, height/2)
                    GL.glVertex2f(0, 0)
                    GL.glVertex2f(0, 0)
                    GL.glVertex2f(width, 0)
                elif char == '3':
                    GL.glVertex2f(0, height)
                    GL.glVertex2f(width, height)
                    GL.glVertex2f(width, height)
                    GL.glVertex2f(width, 0)
                    GL.glVertex2f(width, 0)
                    GL.glVertex2f(0, 0)
                    GL.glVertex2f(width/2, height/2)
                    GL.glVertex2f(width, height/2)
                elif char == '4':
                    GL.glVertex2f(width*3/4, 0)
                    GL.glVertex2f(width*3/4, height)
                    GL.glVertex2f(0, height/2)
                    GL.glVertex2f(width, height/2)
                elif char == '5':
                    GL.glVertex2f(width, height)
                    GL.glVertex2f(0, height)
                    GL.glVertex2f(0, height)
                    GL.glVertex2f(0, height/2)
                    GL.glVertex2f(0, height/2)
                    GL.glVertex2f(width, height/2)
                    GL.glVertex2f(width, height/2)
                    GL.glVertex2f(width, 0)
                    GL.glVertex2f(width, 0)
                    GL.glVertex2f(0, 0)
                elif char == '6':
                    GL.glVertex2f(width, height)
                    GL.glVertex2f(0, height)
                    GL.glVertex2f(0, height)
                    GL.glVertex2f(0, 0)
                    GL.glVertex2f(0, 0)
                    GL.glVertex2f(width, 0)
                    GL.glVertex2f(width, 0)
                    GL.glVertex2f(width, height/2)
                    GL.glVertex2f(width, height/2)
                    GL.glVertex2f(0, height/2)
                elif char == '7':
                    GL.glVertex2f(0, height)
                    GL.glVertex2f(width, height)
                    GL.glVertex2f(width, height)
                    GL.glVertex2f(width/2, 0)
                elif char == '8':
                    GL.glVertex2f(0, 0)
                    GL.glVertex2f(width, 0)
                    GL.glVertex2f(width, 0)
                    GL.glVertex2f(width, height)
                    GL.glVertex2f(width, height)
                    GL.glVertex2f(0, height)
                    GL.glVertex2f(0, height)
                    GL.glVertex2f(0, 0)
                    GL.glVertex2f(0, height/2)
                    GL.glVertex2f(width, height/2)
                elif char == '9':
                    GL.glVertex2f(width, height/2)
                    GL.glVertex2f(0, height/2)
                    GL.glVertex2f(0, height/2)
                    GL.glVertex2f(0, height)
                    GL.glVertex2f(0, height)
                    GL.glVertex2f(width, height)
                    GL.glVertex2f(width, height)
                    GL.glVertex2f(width, 0)
            else:
                # Default shape for unknown characters
                GL.glVertex2f(0, 0)
                GL.glVertex2f(width, 0)
                GL.glVertex2f(width, 0)
                GL.glVertex2f(width, height)
                GL.glVertex2f(width, height)
                GL.glVertex2f(0, height)
                GL.glVertex2f(0, height)
                GL.glVertex2f(0, 0)
        except Exception as e:
            print(f"Error drawing character: {e}")
            self.handle_error(e)

    def draw_menu(self) -> None:
        """Draw the main menu screen."""
        # Clear background
        GL.glClear(GL.GL_COLOR_BUFFER_BIT | GL.GL_DEPTH_BUFFER_BIT)
        
        # Draw title
        self.draw_text(-0.4, 0.7, "TIC TAC TOE", scale=1.5, color=(1, 1, 1))
        
        # Draw menu buttons
        for button in self.menu_buttons.values():
            self.draw_button(button)

    def handle_menu_click(self, x_pos: float, y_pos: float) -> None:
        """Handle clicks in the menu screen."""
        for name, button in self.menu_buttons.items():
            if self.is_point_in_rect(x_pos, y_pos, *button['rect']):
                if name == 'play_x':
                    self.player_symbol = 'X'
                    self.computer_symbol = 'O'
                    self.current_player = True
                    self.in_menu = False
                elif name == 'play_o':
                    self.player_symbol = 'O'
                    self.computer_symbol = 'X'
                    self.current_player = False
                    self.in_menu = False
                    # Computer makes first move
                    self.computer_move()
                elif name.startswith('color_'):
                    color = name.split('_')[1]
                    if color == 'red':
                        self.player_color = (0.8, 0.2, 0.2)
                    elif color == 'blue':
                        self.player_color = (0.2, 0.2, 0.8)
                    elif color == 'green':
                        self.player_color = (0.2, 0.8, 0.2)
                    elif color == 'purple':
                        self.player_color = (0.6, 0.2, 0.8)
                break

    def draw_hover_effect(self) -> None:
        """Draw hover effect on the current cell."""
        if self.hover_cell != (-1, -1) and self.board[self.hover_cell[0]][self.hover_cell[1]] is None:
            row, col = self.hover_cell
            cell_size = 2/3
            x = -1 + (col + 0.5) * cell_size
            y = 1 - (row + 0.5) * cell_size
            
            # Draw semi-transparent hover piece
            if self.player_symbol == 'X':
                self.draw_x(x, y, alpha=0.3)
            else:
                self.draw_o(x, y, alpha=0.3)

    def draw_cursor_pointer(self, x: float, y: float) -> None:
        """Draw an ultra-smooth cursor with trail and dynamic effects."""
        # Update cursor position with smooth interpolation
        self.cursor_target = [x, y]
        self.cursor_pos[0] += (self.cursor_target[0] - self.cursor_pos[0]) * self.cursor_smoothing
        self.cursor_pos[1] += (self.cursor_target[1] - self.cursor_pos[1]) * self.cursor_smoothing
        
        # Add current position to trail
        self.cursor_trail.append((self.cursor_pos[0], self.cursor_pos[1], 1.0))
        if len(self.cursor_trail) > self.max_trail_length:
            self.cursor_trail.pop(0)
        
        # Update trail fade
        for i in range(len(self.cursor_trail)):
            x, y, alpha = self.cursor_trail[i]
            self.cursor_trail[i] = (x, y, max(0, alpha - self.trail_fade_speed))
        
        # Draw trail
        GL.glEnable(GL.GL_BLEND)
        GL.glBlendFunc(GL.GL_SRC_ALPHA, GL.GL_ONE_MINUS_SRC_ALPHA)
        
        current_time = pygame.time.get_ticks() * 0.001
        base_size = 0.015
        
        # Draw trail with dynamic effects
        for i, (trail_x, trail_y, alpha) in enumerate(self.cursor_trail):
            if alpha <= 0:
                continue
                
            progress = i / len(self.cursor_trail)
            pulse = (math.sin(current_time * 5 + progress * math.pi) + 1) * 0.5
            size = base_size * (0.5 + 0.5 * pulse) * (0.3 + 0.7 * progress)
            
            # Trail glow
            GL.glBegin(GL.GL_TRIANGLES)
            GL.glColor4f(1, 1, 1, alpha * 0.2)
            GL.glVertex3f(trail_x, trail_y + size * 2, 0)
            GL.glVertex3f(trail_x - size, trail_y - size, 0)
            GL.glVertex3f(trail_x + size, trail_y - size, 0)
            GL.glEnd()
            
            # Trail core
            GL.glBegin(GL.GL_TRIANGLES)
            GL.glColor4f(1, 1, 1, alpha * 0.5)
            GL.glVertex3f(trail_x, trail_y + size * 1.5, 0)
            GL.glVertex3f(trail_x - size * 0.8, trail_y - size * 0.8, 0)
            GL.glVertex3f(trail_x + size * 0.8, trail_y - size * 0.8, 0)
            GL.glEnd()
        
        # Update cursor effects
        hover_intensity = 0.0
        if not self.in_menu:
            row, col = self.get_cell(self.cursor_pos[0], self.cursor_pos[1])
            if row != -1 and col != -1 and self.board[row][col] is None:
                hover_intensity = 1.0
        
        self.cursor_glow_intensity += (hover_intensity - self.cursor_glow_intensity) * 0.1
        self.cursor_scale += ((1.0 + 0.2 * self.cursor_glow_intensity) - self.cursor_scale) * 0.1
        
        # Draw main cursor with dynamic effects
        main_size = base_size * self.cursor_scale
        pulse = (math.sin(current_time * 4) + 1) * 0.5
        glow_size = main_size * (1.2 + 0.2 * pulse)
        
        # Outer glow
        GL.glBegin(GL.GL_TRIANGLES)
        GL.glColor4f(1, 1, 1, 0.2 * (1.0 + self.cursor_glow_intensity))
        GL.glVertex3f(self.cursor_pos[0], self.cursor_pos[1] + glow_size * 2, 0)
        GL.glVertex3f(self.cursor_pos[0] - glow_size, self.cursor_pos[1] - glow_size, 0)
        GL.glVertex3f(self.cursor_pos[0] + glow_size, self.cursor_pos[1] - glow_size, 0)
        GL.glEnd()
        
        # Inner glow
        GL.glBegin(GL.GL_TRIANGLES)
        GL.glColor4f(1, 1, 1, 0.4 * (1.0 + self.cursor_glow_intensity))
        GL.glVertex3f(self.cursor_pos[0], self.cursor_pos[1] + main_size * 1.8, 0)
        GL.glVertex3f(self.cursor_pos[0] - main_size * 0.9, self.cursor_pos[1] - main_size * 0.9, 0)
        GL.glVertex3f(self.cursor_pos[0] + main_size * 0.9, self.cursor_pos[1] - main_size * 0.9, 0)
        GL.glEnd()
        
        # Main cursor
        GL.glBegin(GL.GL_TRIANGLES)
        GL.glColor4f(1, 1, 1, 0.9)
        GL.glVertex3f(self.cursor_pos[0], self.cursor_pos[1] + main_size * 1.5, 0)
        GL.glVertex3f(self.cursor_pos[0] - main_size * 0.8, self.cursor_pos[1] - main_size * 0.8, 0)
        GL.glVertex3f(self.cursor_pos[0] + main_size * 0.8, self.cursor_pos[1] - main_size * 0.8, 0)
        GL.glEnd()

    def update_button_hover(self, x: float, y: float) -> None:
        """Update button hover states."""
        buttons = self.menu_buttons if self.in_menu else self.buttons
        for button in buttons.values():
            rect = button['rect']
            button['hover'] = self.is_point_in_rect(x, y, *rect)
            
            # Update button animation
            target_scale = 1.1 if button['hover'] else 1.0
            current_scale = button.get('scale', 1.0)
            button['scale'] = current_scale + (target_scale - current_scale) * 0.2
            
            target_glow = 1.0 if button['hover'] else 0.0
            current_glow = button.get('glow', 0.0)
            button['glow'] = current_glow + (target_glow - current_glow) * 0.2

    def handle_button_click(self, x: float, y: float) -> bool:
        """Handle clicks on game buttons."""
        for name, button in self.buttons.items():
            if self.is_point_in_rect(x, y, *button['rect']):
                if name == 'restart':
                    self.reset_game()
                elif name == 'menu':
                    self.in_menu = True
                elif name == 'undo':
                    self.undo_last_move()
                return True
        return False

    def undo_last_move(self) -> None:
        """Undo the last move if possible."""
        if len(self.move_history) >= 2:
            # Undo both player's and computer's moves
            for _ in range(2):
                if self.move_history:
                    row, col, _ = self.move_history.pop()
                    self.board[row][col] = None
            
            self.game_over = False
            self.winner = None
            self.show_winner_screen = False
            self.current_player = True
            self.animation_progress = 0.0

    def run(self) -> None:
        """Run the game loop with improved error handling and performance."""
        try:
            clock = pygame.time.Clock()
            running = True
            last_time = time.time()
            
            # Hide system cursor and enable raw input for better precision
            pygame.mouse.set_visible(False)
            pygame.event.set_grab(True)
            
            # Enable relevant events and disable others for better performance
            pygame.event.set_allowed([
                pygame.QUIT, 
                pygame.KEYDOWN, 
                pygame.MOUSEBUTTONDOWN,
                pygame.MOUSEMOTION,
                pygame.VIDEORESIZE
            ])
            
            while running:
                try:
                    # Calculate delta time with maximum value to prevent large jumps
                    current_time = time.time()
                    delta_time = min(current_time - last_time, 0.1)
                    last_time = current_time

                    # Update FPS counter
                    self.frame_count += 1
                    if current_time - self.last_frame_time > 1.0:
                        self.fps = self.frame_count / (current_time - self.last_frame_time)
                        self.frame_count = 0
                        self.last_frame_time = current_time

                    # Handle events
                    for event in pygame.event.get():
                        if event.type == pygame.QUIT:
                            running = False
                        elif event.type == pygame.VIDEORESIZE:
                            self.resize_viewport(event.w, event.h)
                        elif event.type == pygame.KEYDOWN:
                            if event.key == pygame.K_ESCAPE:
                                if not self.in_menu:
                                    self.in_menu = True
                                else:
                                    running = False
                            elif event.key == pygame.K_SPACE and self.game_over:
                                self.reset_game()
                            elif event.key == pygame.K_z and pygame.key.get_mods() & pygame.KMOD_CTRL:
                                self.undo_last_move()
                        elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                            if self.in_menu:
                                self.handle_menu_click(x_pos, y_pos)
                            else:
                                if not self.handle_button_click(x_pos, y_pos):
                                    if self.show_winner_screen:
                                        self.handle_winner_screen_click(x_pos, y_pos)
                                    elif self.current_player and not self.game_over:
                                        self.handle_click(x_pos, y_pos)

                    # Get mouse position with error handling
                    try:
                        mouse_x, mouse_y = pygame.mouse.get_pos()
                        x_pos = (mouse_x / (self.display_size[0] / 2)) - 1
                        y_pos = 1 - (mouse_y / (self.display_size[1] / 2))
                    except:
                        x_pos, y_pos = 0, 0

                    # Update game state
                    self.update_button_hover(x_pos, y_pos)
                    if not self.in_menu and not self.game_over:
                        self.hover_cell = self.get_cell(x_pos, y_pos)

                    # Update animations
                    if not self.game_over:
                        self.animation_progress = min(1.0, self.animation_progress + self.animation_speed * delta_time * 60)
                    if self.show_winner_screen:
                        self.fade_alpha = min(1.0, self.fade_alpha + self.hover_speed * delta_time * 60)

                    # Clear the screen
                    GL.glClear(GL.GL_COLOR_BUFFER_BIT | GL.GL_DEPTH_BUFFER_BIT)
                    GL.glLoadIdentity()

                    # Draw current screen
                    if self.in_menu:
                        self.draw_menu()
                    else:
                        self.draw_board()
                        if not self.game_over:
                            self.draw_hover_effect()
                        self.draw_pieces()
                        self.draw_score()
                        self.draw_current_player()
                        if self.show_winner_screen:
                            self.draw_winner_screen()
                        
                        # Draw game buttons
                        for button in self.buttons.values():
                            self.draw_button(button, not self.show_winner_screen)

                    # Draw custom cursor
                    self.draw_cursor_pointer(x_pos, y_pos)

                    # Draw FPS counter
                    self.draw_text(0.7, 0.95, f"FPS: {int(self.fps)}", scale=0.5, color=(0.8, 0.8, 0.8))

                    # Update display
                    pygame.display.flip()
                    clock.tick(60)  # Limit to 60 FPS

                except Exception as e:
                    print(f"Error in game loop: {e}")
                    if not self.handle_error(e):
                        running = False

        except Exception as e:
            print(f"Fatal game error: {e}")
            raise
        finally:
            pygame.event.set_grab(False)
            pygame.mouse.set_visible(True)
            pygame.quit()

def main() -> None:
    """Start the enhanced game."""
    try:
        game = TicTacToe()
        game.run()
    except Exception as e:
        print(f"Fatal error: {e}", file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__":
    main()

    