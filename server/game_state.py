import math

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
        self.tick = 0
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

        # Check if any player fell into a pit / lava (below canvas)
        death_y = self.level.get('death_y', 600)
        for p in self.players.values():
            if p.y > death_y:
                self.respawn_all()
                break

        # Animate oscillating tiles and plates
        self.tick += 1
        for tile in self.level['tiles']:
            if tile.get('moving'):
                tile['x'] = tile['move_center_x'] + tile['move_amp'] * math.sin(self.tick * tile['move_speed'])
        for plate in self.level.get('pressure_plates', []):
            if plate.get('moving'):
                plate['x'] = plate['move_center_x'] + plate['move_amp'] * math.sin(self.tick * plate['move_speed'])

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

        # Goal plate: solid until triggered (solo mode)
        goal_plate = self.level.get('goal_plate')
        if goal_plate and not goal_plate.get('triggered', False):
            tiles.append(goal_plate)

        # Duo goal plates: each solid until triggered
        for gp in self.level.get('goal_plates', []):
            if not gp.get('triggered', False):
                tiles.append(gp)

        # Goal door: solid until goal plate(s) triggered
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
            if self._player_on_plate(p, plate):
                return True
        return False

    def _player_on_plate(self, player, plate):
        """Returns True if a specific player object is standing on the plate."""
        px_center = player.x + PLAYER_W / 2
        py_bottom = player.y + PLAYER_H
        in_x  = plate['x'] <= px_center <= plate['x'] + plate['w']
        on_top = abs(py_bottom - plate['y']) < 10
        return in_x and on_top

    def _update_pressure_plates(self):
        plates = self.level.get('pressure_plates', [])
        duo_plates  = [pl for pl in plates if pl.get('duo')  and not pl.get('triggered')]
        solo_plates = [pl for pl in plates if not pl.get('duo') and not pl.get('triggered')]

        # Solo door plates: one-shot on first contact by any player
        for plate in solo_plates:
            plate['active'] = False
            if self._check_plate(plate):
                plate['triggered'] = True
                plate['active'] = True

        # Duo door plates: each plate has a 'player' field (e.g. 'p1' or 'p2').
        # It only becomes active when THAT specific player is standing on it.
        for plate in duo_plates:
            assigned_pid = plate.get('player')   # e.g. 'p1' or 'p2'
            player_obj   = self.players.get(assigned_pid)
            if player_obj and self._player_on_plate(player_obj, plate):
                plate['active'] = True
            else:
                plate['active'] = False

        # Open the door permanently only when ALL duo plates are active simultaneously
        if duo_plates and all(pl['active'] for pl in duo_plates):
            for plate in duo_plates:
                plate['triggered'] = True

        # Solo goal plate — any player triggers alone
        goal_plate = self.level.get('goal_plate')
        if goal_plate and not goal_plate.get('triggered', False):
            goal_plate['active'] = False
            if self._check_plate(goal_plate):
                goal_plate['triggered'] = True
                goal_plate['active'] = True
                self.level['goal_locked'] = False

        # Duo goal plates — each assigned to a specific player;
        # BOTH must stand on their plate simultaneously to unlock the goal
        goal_plates = self.level.get('goal_plates', [])
        untriggered_gps = [gp for gp in goal_plates if not gp.get('triggered')]
        for gp in untriggered_gps:
            player_obj = self.players.get(gp.get('player'))
            gp['active'] = bool(player_obj and self._player_on_plate(player_obj, gp))
        if untriggered_gps and all(gp['active'] for gp in untriggered_gps):
            for gp in untriggered_gps:
                gp['triggered'] = True
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
        if self.num_players >= 2:
            return self._load_duo_level(n)
        return self._load_solo_level(n)

    def _load_solo_level(self, n):
        levels = {
            1: {
                'spawns': [{'x': 60, 'y': 320}, {'x': 120, 'y': 320}],
                'tiles': [
                    {'x': 0,   'y': 400, 'w': 250, 'h': 20},
                    {'x': 330, 'y': 400, 'w': 470, 'h': 20},
                    {'x': 400, 'y': 310, 'w': 100, 'h': 16},
                    {'x': 560, 'y': 255, 'w': 100, 'h': 16},
                    {'x': 0,   'y': 0,   'w': 16,  'h': 420},
                    {'x': 784, 'y': 0,   'w': 16,  'h': 420},
                ],
                'doors': [{'x': 310, 'y': 0, 'w': 20, 'h': 420}],
                'pressure_plates': [
                    {'x': 180, 'y': 392, 'w': 60, 'h': 8, 'active': False, 'triggered': False}
                ],
                'goal_plate': {'x': 580, 'y': 247, 'w': 60, 'h': 8, 'active': False, 'triggered': False},
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
            },
            3: {
                # Level 3 — Lava World: no ground, only floating rock platforms.
                # Falling past death_y (into lava) respawns all players.
                'theme': 'lava',
                'death_y': 420,
                'spawns': [{'x': 30, 'y': 310}, {'x': 75, 'y': 310}],
                'tiles': [
                    # Spawn platform (anchored to left wall)
                    {'x': 16,  'y': 365, 'w': 110, 'h': 16, 'color': '#6b6b6b', 'shadow': '#3a3a3a'},
                    # Platform 2
                    {'x': 175, 'y': 320, 'w': 80,  'h': 16, 'color': '#5a5a5a', 'shadow': '#2e2e2e'},
                    # Platform 3 — door plate sits here (oscillates left-right)
                    {'x': 280, 'y': 200, 'w': 80,  'h': 16, 'color': '#6b6b6b', 'shadow': '#3a3a3a',
                     'moving': True, 'move_center_x': 280, 'move_amp': 55, 'move_speed': 0.025},
                    # Platform 4 (right of door)
                    # {'x': 440, 'y': 352, 'w': 80,  'h': 16, 'color': '#5a5a5a', 'shadow': '#2e2e2e'},
                    # Platform 5 — elevated, goal plate sits here
                    {'x': 535, 'y': 150, 'w': 85,  'h': 16, 'color': '#6b6b6b', 'shadow': '#3a3a3a'},
                    # Platform 6 — landing before goal door
                    {'x': 640, 'y': 350, 'w': 75,  'h': 16, 'color': '#5a5a5a', 'shadow': '#2e2e2e'},
                    # Goal platform (against right wall)
                    {'x': 16, 'y': 125, 'w': 48,  'h': 16, 'color': '#4a4a4a', 'shadow': '#222222'},
                    # Walls (dark rock)
                    {'x': 0,   'y': 0,   'w': 16,  'h': 420, 'color': '#4a4a4a', 'shadow': '#222222'},
                    {'x': 784, 'y': 0,   'w': 16,  'h': 420, 'color': '#4a4a4a', 'shadow': '#222222'},
                ],
                'doors': [{'x': 400, 'y': 0, 'w': 20, 'h': 420}],
                'pressure_plates': [
                    # Plate x offset matches platform (tile center 280, plate center 290 = +10px)
                    {'x': 290, 'y': 192, 'w': 60, 'h': 8, 'active': False, 'triggered': False,
                     'moving': True, 'move_center_x': 290, 'move_amp': 55, 'move_speed': 0.025}
                ],
                'goal_plate': {'x': 547, 'y': 142, 'w': 60, 'h': 8, 'active': False, 'triggered': False},
                # 'goal_door':  {'x': 716, 'y': 0,   'w': 20, 'h': 420},
                'goal_locked': True,
                'goal': {'x': 16, 'y': 75, 'w': 48, 'h': 45},
            }
        }
        return levels.get(n, levels[1])

    def _load_duo_level(self, n):
        # All duo plates assigned per-player; doors/goal only open when BOTH
        # assigned players stand on their plates simultaneously.
        levels = {
            1: {
                # Both players spawn together center-left
                'spawns': [{'x': 100, 'y': 350}, {'x': 145, 'y': 350}],
                'tiles': [
                    # Left ground
                    {'x': 0,   'y': 400, 'w': 300, 'h': 20},
                    # P1 door platform (left) — P1 jumps up here
                    {'x': 28,  'y': 295, 'w': 100, 'h': 16},
                    # P2 door platform (right of left zone) — P2 jumps up here
                    {'x': 183, 'y': 295, 'w': 100, 'h': 16},
                    # Right ground
                    {'x': 335, 'y': 400, 'w': 450, 'h': 20},
                    # P1 goal platform (mid-left)
                    {'x': 375, 'y': 310, 'w': 100, 'h': 16},
                    # P2 goal platform (mid-upper)
                    {'x': 530, 'y': 245, 'w': 100, 'h': 16},
                    # Landing platform near goal room
                    {'x': 655, 'y': 310, 'w': 90,  'h': 16},
                    # Walls
                    {'x': 0,   'y': 0,   'w': 16,  'h': 420},
                    {'x': 784, 'y': 0,   'w': 16,  'h': 420},
                ],
                'doors': [{'x': 315, 'y': 0, 'w': 20, 'h': 420}],
                # P1 door plate on left platform; P2 door plate on right platform
                'pressure_plates': [
                    {'x': 38,  'y': 287, 'w': 70, 'h': 8, 'active': False, 'triggered': False, 'duo': True, 'player': 'p1'},
                    {'x': 193, 'y': 287, 'w': 70, 'h': 8, 'active': False, 'triggered': False, 'duo': True, 'player': 'p2'},
                ],
                # P1 star plate on mid-left platform; P2 star plate on mid-upper platform
                'goal_plates': [
                    {'x': 385, 'y': 302, 'w': 70, 'h': 8, 'active': False, 'triggered': False, 'duo': True, 'player': 'p1'},
                    {'x': 540, 'y': 237, 'w': 70, 'h': 8, 'active': False, 'triggered': False, 'duo': True, 'player': 'p2'},
                ],
                'goal_door':  {'x': 700, 'y': 0, 'w': 20, 'h': 420},
                'goal_locked': True,
                'goal': {'x': 722, 'y': 355, 'w': 55, 'h': 45},
            },
            2: {
                # Level 2 — split staircase: each player climbs their own tower
                'spawns': [{'x': 100, 'y': 350}, {'x': 145, 'y': 350}],
                'tiles': [
                    # Left ground
                    {'x': 0,   'y': 400, 'w': 280, 'h': 20},
                    # Shared first step (both can use)
                    {'x': 65,  'y': 330, 'w': 170, 'h': 16},
                    # P1 tower (left branch, two steps)
                    # {'x': 16,  'y': 255, 'w': 90,  'h': 16},
                    {'x': 16,  'y': 175, 'w': 90,  'h': 16},
                    # P2 tower (right branch, two steps)
                    {'x': 200, 'y': 255, 'w': 90,  'h': 16},
                    {'x': 210, 'y': 175, 'w': 90,  'h': 16},
                    # Right ground
                    {'x': 335, 'y': 400, 'w': 455, 'h': 20},
                    # Right landing step
                    {'x': 365, 'y': 330, 'w': 90,  'h': 16},
                    # P1 goal tower (right zone)
                    {'x': 460, 'y': 275, 'w': 90,  'h': 16},
                    {'x': 460, 'y': 175, 'w': 90,  'h': 16},
                    # P2 goal tower (further right)
                    # {'x': 570, 'y': 255, 'w': 90,  'h': 16},
                    {'x': 570, 'y': 230, 'w': 90,  'h': 16},
                    # Walls
                    {'x': 0,   'y': 0,   'w': 16,  'h': 420},
                    {'x': 784, 'y': 0,   'w': 16,  'h': 420},
                ],
                'doors': [{'x': 315, 'y': 0, 'w': 20, 'h': 420}],
                # P1 door plate on top of P1 left tower; P2 door plate on top of P2 left tower
                'pressure_plates': [
                    {'x': 25,  'y': 167, 'w': 70, 'h': 8, 'active': False, 'triggered': False, 'duo': True, 'player': 'p1'},
                    {'x': 220, 'y': 167, 'w': 70, 'h': 8, 'active': False, 'triggered': False, 'duo': True, 'player': 'p2'},
                ],
                # P1 star plate on top of P1 right tower; P2 star plate on top of P2 right tower
                'goal_plates': [
                    {'x': 469, 'y': 167, 'w': 70, 'h': 8, 'active': False, 'triggered': False, 'duo': True, 'player': 'p1'},
                    {'x': 579, 'y': 222, 'w': 70, 'h': 8, 'active': False, 'triggered': False, 'duo': True, 'player': 'p2'},
                ],
                'goal_door':  {'x': 700, 'y': 0, 'w': 20, 'h': 420},
                'goal_locked': True,
                'goal': {'x': 722, 'y': 355, 'w': 55, 'h': 45},
            },
            3: {
                # Duo Level 3 — Lava World.
                # P1 spawns far-left, P2 far-right. Each has a door plate on
                # their own elevated platform. Two doors split the level;
                # both must stand simultaneously to open them.
                # After the doors open, both players converge to the middle
                # and must stand on their assigned ★ plates simultaneously
                # to reveal the goal on the upper central platform.
                'theme': 'lava',
                'death_y': 420,
                'spawns': [{'x': 50, 'y': 317}, {'x': 720, 'y': 317}],
                'tiles': [
                    # Walls (dark rock)
                    {'x': 0,   'y': 0,   'w': 16,  'h': 420, 'color': '#4a4a4a', 'shadow': '#222222'},
                    {'x': 784, 'y': 0,   'w': 16,  'h': 420, 'color': '#4a4a4a', 'shadow': '#222222'},
                    # ── P1 zone (left) ────────────────────
                    # P1 spawn platform — anchored to left wall
                    {'x': 16,  'y': 365, 'w': 110, 'h': 16, 'color': '#6b6b6b', 'shadow': '#3a3a3a'},
                    # P1 hop platform (moving — must time the jump!)
                    # {'x': 165, 'y': 310, 'w': 80,  'h': 16, 'color': '#5a5a5a', 'shadow': '#2e2e2e',
                    #  'moving': True, 'move_center_x': 165, 'move_amp': 25, 'move_speed': 0.020},
                    # P1 door plate platform (elevated, moving — must time the jump!)
                    {'x': 150, 'y': 245, 'w': 80,  'h': 16, 'color': '#6b6b6b', 'shadow': '#3a3a3a',
                     'moving': True, 'move_center_x': 150, 'move_amp': 35, 'move_speed': 0.022},
                    # ── Middle zone ────────────────────
                    # P1 ★ goal platform (left of center, static)
                    {'x': 315, 'y': 300, 'w': 75,  'h': 16, 'color': '#5a5a5a', 'shadow': '#2e2e2e'},
                    # Upper central platform — goal appears here (static)
                    {'x': 350, 'y': 215, 'w': 100, 'h': 16, 'color': '#6b6b6b', 'shadow': '#3a3a3a'},
                    # P2 ★ goal platform (right of center, static)
                    {'x': 410, 'y': 300, 'w': 75,  'h': 16, 'color': '#5a5a5a', 'shadow': '#2e2e2e'},
                    # ── P2 zone (right) ────────────────────
                    # P2 door plate platform (elevated, moving — mirrors P1 door platform)
                    {'x': 545, 'y': 245, 'w': 80,  'h': 16, 'color': '#6b6b6b', 'shadow': '#3a3a3a',
                     'moving': True, 'move_center_x': 545, 'move_amp': 35, 'move_speed': 0.022},
                    # P2 hop platform (moving — mirrors P1 hop)
                    # {'x': 565, 'y': 310, 'w': 80,  'h': 16, 'color': '#5a5a5a', 'shadow': '#2e2e2e',
                    #  'moving': True, 'move_center_x': 565, 'move_amp': 25, 'move_speed': 0.020},
                    # P2 spawn platform — anchored to right wall
                    {'x': 674, 'y': 365, 'w': 110, 'h': 16, 'color': '#6b6b6b', 'shadow': '#3a3a3a'},
                    #  Goal platform (against right wall)
                    {'x': 16, 'y': 125, 'w': 48,  'h': 16, 'color': '#4a4a4a', 'shadow': '#222222'},
                ],
                # Two doors: one blocking each player from the middle.
                # Both permanently open when all duo door plates triggered simultaneously.
                'doors': [
                    {'x': 295, 'y': 0, 'w': 20, 'h': 420},  # Left door
                    {'x': 485, 'y': 0, 'w': 20, 'h': 420},  # Right door
                ],
                'pressure_plates': [
                    # P1 plate — tracks P1 door platform (same amp/speed, +8px offset)
                    {'x': 158, 'y': 237, 'w': 60, 'h': 8, 'active': False, 'triggered': False, 'duo': True, 'player': 'p1',
                     'moving': True, 'move_center_x': 158, 'move_amp': 35, 'move_speed': 0.022},
                    # P2 plate — tracks P2 door platform (same amp/speed, +8px offset)
                    {'x': 552, 'y': 237, 'w': 60, 'h': 8, 'active': False, 'triggered': False, 'duo': True, 'player': 'p2',
                     'moving': True, 'move_center_x': 552, 'move_amp': 35, 'move_speed': 0.022},
                ],
                'goal_plates': [
                    # P1 ★ plate — static
                    {'x': 323, 'y': 292, 'w': 60, 'h': 8, 'active': False, 'triggered': False, 'duo': True, 'player': 'p1'},
                    # P2 ★ plate — static
                    {'x': 418, 'y': 292, 'w': 60, 'h': 8, 'active': False, 'triggered': False, 'duo': True, 'player': 'p2'},
                ],
                'goal_locked': True,
                # Goal appears on the upper central platform when both ★ plates triggered
                'goal': {'x': 16, 'y': 75, 'w': 48, 'h': 45},
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
                'theme': self.level.get('theme'),
                'doors': self.level.get('doors', []),
                'pressure_plates': [
                    {**pl, 'player': pl.get('player'), 'duo': pl.get('duo', False)}
                    for pl in self.level.get('pressure_plates', [])
                ],
                'goal_plate': self.level.get('goal_plate'),
                'goal_plates': self.level.get('goal_plates', []),
                'goal_door': self.level.get('goal_door'),
                'goal': self.level['goal'],
                'goal_locked': self.level.get('goal_locked', True),
                'doors_open': self._all_plates_active()
            }
        }