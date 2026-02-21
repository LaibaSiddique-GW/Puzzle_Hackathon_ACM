GRAVITY = 0.6
SPEED = 4
JUMP_FORCE = -13
PLAYER_W = 32
PLAYER_H = 48

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
    def __init__(self, session_id, num_players=1):
        self.session_id = session_id
        self.num_players = num_players
        self.current_level = 1
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
            p.vy += GRAVITY
            p.x += p.vx
            p.y += p.vy
            self._resolve_collisions(p)

        # Check if any player fell into a pit (below canvas)
        for p in self.players.values():
            if p.y > 600:
                self.respawn_all()
                break

        # Update pressure plates
        self._update_pressure_plates()

    def _resolve_collisions(self, p):
        p.on_ground = False
        tiles = self.level['tiles'][:]

        # Doors are solid until all plates are triggered
        if not self._all_plates_active():
            for door in self.level.get('doors', []):
                tiles.append(door)

        # Pressure plates are solid until triggered (then disappear)
        for plate in self.level.get('pressure_plates', []):
            if not plate.get('triggered', False):
                tiles.append(plate)

        for tile in tiles:
            tx, ty = tile['x'], tile['y']
            tw, th = tile['w'], tile['h']

            overlap_x = (p.x < tx + tw) and (p.x + PLAYER_W > tx)
            overlap_y = (p.y < ty + th) and (p.y + PLAYER_H > ty)

            if overlap_x and overlap_y:
                # Calculate overlap depths
                from_left  = (tx + tw) - p.x
                from_right = (p.x + PLAYER_W) - tx
                from_top   = (ty + th) - p.y
                from_bottom = (p.y + PLAYER_H) - ty

                min_overlap = min(from_left, from_right, from_top, from_bottom)

                if min_overlap == from_bottom and p.vy >= 0:
                    p.y = ty - PLAYER_H
                    p.vy = 0
                    p.on_ground = True
                elif min_overlap == from_top and p.vy < 0:
                    p.y = ty + th
                    p.vy = 0
                elif min_overlap == from_left and p.vx > 0:
                    p.x = tx - PLAYER_W
                elif min_overlap == from_right and p.vx < 0:
                    p.x = tx + tw

    def _update_pressure_plates(self):
        plates = self.level.get('pressure_plates', [])
        for plate in plates:
            if plate.get('triggered'):
                continue  # permanently activated — skip
            plate['active'] = False
            for p in self.players.values():
                px_center = p.x + PLAYER_W / 2
                py_bottom = p.y + PLAYER_H
                in_x = plate['x'] <= px_center <= plate['x'] + plate['w']
                on_top = abs(py_bottom - plate['y']) < 8
                if in_x and on_top:
                    plate['triggered'] = True   # one-shot, permanent
                    plate['active'] = True

    def _all_plates_active(self):
        plates = self.level.get('pressure_plates', [])
        if not plates:
            return True
        return all(plate.get('triggered', False) for plate in plates)

    def check_win(self):
        goal = self.level['goal']
        return all(
            goal['x'] <= p.x + PLAYER_W / 2 <= goal['x'] + goal['w'] and
            goal['y'] <= p.y + PLAYER_H / 2 <= goal['y'] + goal['h']
            for p in self.players.values()
        )

    def load_level(self, n):
        levels = {
            1: {
                'spawns': [{'x': 80, 'y': 320}, {'x': 140, 'y': 320}],
                'tiles': [
                    # Left ground (spawn zone)
                    {'x': 0,   'y': 400, 'w': 250, 'h': 20},
                    # Right ground (middle zone + goal room, continuous)
                    {'x': 350, 'y': 400, 'w': 450, 'h': 20},
                    # Platforms in middle zone (only reachable after doors open)
                    {'x': 420, 'y': 300, 'w': 100, 'h': 16},
                    {'x': 580, 'y': 250, 'w': 100, 'h': 16},
                    # Walls
                    {'x': 0,   'y': 0,   'w': 16,  'h': 420},
                    {'x': 784, 'y': 0,   'w': 16,  'h': 420},
                ],
                # Two full-height barriers — both vanish when plate is triggered
                'doors': [
                    {'x': 330, 'y': 0, 'w': 20, 'h': 420},  # gap wall
                    {'x': 690, 'y': 0, 'w': 20, 'h': 420},  # goal room seal
                ],
                # Plate is on the LEFT (accessible from spawn without crossing any door)
                'pressure_plates': [
                    {'x': 180, 'y': 392, 'w': 60, 'h': 8, 'active': False, 'triggered': False}
                ],
                'goal': {'x': 715, 'y': 360, 'w': 55, 'h': 40},
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
                'goal': self.level['goal'],
                'doors_open': self._all_plates_active()
            }
        }