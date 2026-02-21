GRAVITY = 0.6
SPEED = 4
JUMP_FORCE = -13
PLAYER_W = 32
PLAYER_H = 48
STEP_HEIGHT = 10  # px; lets player walk up onto thin plates/platforms

class Player:
    def __init__(self, pid, x, y, color):
        self.id = pid
        self.x = float(x)
        self.y = float(y)
        self.vx = 0.0
        self.vy = 0.0
        self.on_ground = False
        self.color = color

class GameState:
    def __init__(self, session_id, num_players=1, level_num=1):
        self.session_id = session_id
        self.num_players = num_players
        self.current_level = level_num
        self.level = self.load_level(self.current_level)
        self.players = {}
        self._spawn_players()

    def _spawn_players(self):
        spawns = self.level.get('spawns', [{'x': 100, 'y': 300}, {'x': 160, 'y': 300}])
        colors = ['#e74c3c', '#3498db']
        for i in range(self.num_players):
            pid = f'p{i+1}'
            sp = spawns[i] if i < len(spawns) else {'x': 100 + i * 60, 'y': 300}
            self.players[pid] = Player(pid, sp['x'], sp['y'], colors[i])

    def respawn_all(self):
        spawns = self.level.get('spawns', [{'x': 100, 'y': 300}, {'x': 160, 'y': 300}])
        for i, (pid, p) in enumerate(self.players.items()):
            sp = spawns[i] if i < len(spawns) else {'x': 100 + i * 60, 'y': 300}
            p.x, p.y = float(sp['x']), float(sp['y'])
            p.vx, p.vy = 0, 0

    def apply_input(self, pid, inp):
        p = self.players.get(pid)
        if not p:
            return
        p.vx = 0
        if inp.get('left'):
            p.vx = -SPEED
        if inp.get('right'):
            p.vx = SPEED
        if inp.get('jump') and p.on_ground:
            p.vy = JUMP_FORCE
            p.on_ground = False

    def update(self):
        for p in self.players.values():
            p.vy = min(p.vy + GRAVITY, 20)  # gravity + terminal velocity cap
            # X axis: move then resolve horizontal collisions
            p.x += p.vx
            self._resolve_x(p)
            # Y axis: move then resolve vertical collisions
            p.y += p.vy
            self._resolve_y(p)

        # Check if any player fell into a pit (below canvas)
        for p in self.players.values():
            if p.y > 600:
                self.respawn_all()
                break

        # Update pressure plates
        self._update_pressure_plates()

    def _get_solid_tiles(self):
        """Returns all currently solid tiles for collision."""
        tiles = self.level['tiles'][:]

        # Main doors: solid until all door plates triggered
        if not self._all_plates_active():
            for door in self.level.get('doors', []):
                tiles.append(door)

        # Door pressure plates: solid until triggered
        for plate in self.level.get('pressure_plates', []):
            if not plate.get('triggered', False):
                tiles.append(plate)

        # Goal plate: solid until triggered
        goal_plate = self.level.get('goal_plate')
        if goal_plate and not goal_plate.get('triggered', False):
            tiles.append(goal_plate)

        # Goal door: solid until goal plate triggered
        if self.level.get('goal_locked', True):
            goal_door = self.level.get('goal_door')
            if goal_door:
                tiles.append(goal_door)

        return tiles

    def _resolve_x(self, p):
        """Resolve horizontal collisions only. Allows stepping up thin ledges."""
        for tile in self._get_solid_tiles():
            tx, ty = tile['x'], tile['y']
            tw, th = tile['w'], tile['h']
            if (p.x < tx + tw and p.x + PLAYER_W > tx and
                    p.y < ty + th and p.y + PLAYER_H > ty):
                # If feet barely clip the tile's top surface, let Y resolve it (step-up)
                feet_overlap = (p.y + PLAYER_H) - ty
                if 0 < feet_overlap <= STEP_HEIGHT:
                    continue
                if p.vx > 0:
                    p.x = tx - PLAYER_W
                elif p.vx < 0:
                    p.x = tx + tw

    def _resolve_y(self, p):
        """Resolve vertical collisions only. Prevents jumping through tile bottoms."""
        p.on_ground = False
        for tile in self._get_solid_tiles():
            tx, ty = tile['x'], tile['y']
            tw, th = tile['w'], tile['h']
            if (p.x < tx + tw and p.x + PLAYER_W > tx and
                    p.y < ty + th and p.y + PLAYER_H > ty):
                if p.vy >= 0:    # falling / standing: land on top surface
                    p.y = ty - PLAYER_H
                    p.vy = 0
                    p.on_ground = True
                else:            # moving upward: blocked by underside
                    p.y = ty + th
                    p.vy = 0

    def _check_plate(self, plate):
        """Returns True if any player is standing on the given plate."""
        for p in self.players.values():
            px_center = p.x + PLAYER_W / 2
            py_bottom = p.y + PLAYER_H
            in_x = plate['x'] <= px_center <= plate['x'] + plate['w']
            on_top = abs(py_bottom - plate['y']) < 10
            if in_x and on_top:
                return True
        return False

    def _update_pressure_plates(self):
        # Regular door plates
        for plate in self.level.get('pressure_plates', []):
            if plate.get('triggered'):
                continue
            plate['active'] = False
            if self._check_plate(plate):
                plate['triggered'] = True
                plate['active'] = True

        # Special goal plate — reveals goal when triggered
        goal_plate = self.level.get('goal_plate')
        if goal_plate and not goal_plate.get('triggered', False):
            goal_plate['active'] = False
            if self._check_plate(goal_plate):
                goal_plate['triggered'] = True
                goal_plate['active'] = True
                self.level['goal_locked'] = False

    def _all_plates_active(self):
        plates = self.level.get('pressure_plates', [])
        if not plates:
            return True
        return all(plate.get('triggered', False) for plate in plates)

    def check_win(self):
        if self.level.get('goal_locked', True):
            return False
        goal = self.level['goal']
        return all(
            goal['x'] <= p.x + PLAYER_W / 2 <= goal['x'] + goal['w'] and
            goal['y'] <= p.y + PLAYER_H / 2 <= goal['y'] + goal['h']
            for p in self.players.values()
        )

    def load_level(self, n):
        levels = {
            1: {
                'spawns': [{'x': 60, 'y': 320}, {'x': 120, 'y': 320}],
                'tiles': [
                    # Left ground (spawn zone)
                    {'x': 0,   'y': 400, 'w': 250, 'h': 20},
                    # Middle + goal room ground (continuous after door opens)
                    {'x': 330, 'y': 400, 'w': 470, 'h': 20},
                    # Platforms in middle zone
                    {'x': 400, 'y': 310, 'w': 100, 'h': 16},
                    {'x': 560, 'y': 255, 'w': 100, 'h': 16},
                    # Walls
                    {'x': 0,   'y': 0,   'w': 16,  'h': 420},
                    {'x': 784, 'y': 0,   'w': 16,  'h': 420},
                ],
                'doors': [{'x': 310, 'y': 0, 'w': 20, 'h': 420}],
                'pressure_plates': [
                    {'x': 180, 'y': 392, 'w': 60, 'h': 8, 'active': False, 'triggered': False}
                ],
                'goal_plate': {'x': 490, 'y': 392, 'w': 60, 'h': 8, 'active': False, 'triggered': False},
                'goal_door': {'x': 680, 'y': 0, 'w': 20, 'h': 420},
                'goal_locked': True,
                'goal': {'x': 712, 'y': 355, 'w': 55, 'h': 45},
            },
            2: {
                # Level 2: plates are elevated on platforms — requires platforming to reach
                'spawns': [{'x': 60, 'y': 320}, {'x': 110, 'y': 320}],
                'tiles': [
                    # Left ground
                    {'x': 0,   'y': 400, 'w': 250, 'h': 20},
                    # Left stepping platforms (staircase upward)
                    {'x': 80,  'y': 320, 'w': 80,  'h': 16},
                    {'x': 190, 'y': 240, 'w': 80,  'h': 16},
                    # Right ground (after door)
                    {'x': 330, 'y': 400, 'w': 50, 'h': 20},
                    # Right platforms
                    {'x': 380, 'y': 320, 'w': 80,  'h': 16},
                    {'x': 510, 'y': 200, 'w': 80,  'h': 16},
                    {'x': 620, 'y': 320, 'w': 80,  'h': 16},
                    {'x': 715, 'y': 110, 'w': 100,  'h': 16},
                    # Walls
                    {'x': 0,   'y': 0,   'w': 16,  'h': 420},
                    {'x': 784, 'y': 0,   'w': 16,  'h': 420},
                ],
                # Main barrier
                'doors': [{'x': 310, 'y': 0, 'w': 20, 'h': 420}],
                # Door plate on the upper-left platform — must jump up staircase to reach
                'pressure_plates': [
                    {'x': 200, 'y': 232, 'w': 60, 'h': 8, 'active': False, 'triggered': False}
                ],
                # Goal plate on lower right platform — must drop down to reach
                'goal_plate': {'x': 626, 'y': 312, 'w': 60, 'h': 8, 'active': False, 'triggered': False},
                'goal_door': {'x': 690, 'y': 0, 'w': 20, 'h': 420},
                'goal_locked': True,
                'goal': {'x': 715, 'y': 55, 'w': 55, 'h': 45},
            }
        }
        return levels.get(n, levels[1])

    def serialize(self):
        return {
            'players': {
                pid: {
                    'x': p.x, 'y': p.y,
                    'vx': p.vx, 'vy': p.vy,
                    'color': p.color,
                    'on_ground': p.on_ground
                }
                for pid, p in self.players.items()
            },
            'level': {
                'tiles': self.level['tiles'],
                'doors': self.level.get('doors', []),
                'pressure_plates': self.level.get('pressure_plates', []),
                'goal_plate': self.level.get('goal_plate'),
                'goal_door': self.level.get('goal_door'),
                'goal': self.level['goal'],
                'goal_locked': self.level.get('goal_locked', True),
                'doors_open': self._all_plates_active()
            }
        }