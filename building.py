"""First Floor: Smith Hall v0.10.

Approximate navigable interpretation of the supplied first-floor plan.
X increases east; Z increases north. Measurements are game units.
"""
from ursina import Entity, Text, color, load_texture

WALL_HEIGHT = 3.5
GEOMETRY = []

BEIGE = color.rgb32(194, 180, 153)
CARPET = color.rgb32(70, 89, 100)
ROOM_FLOOR = color.rgb32(111, 119, 116)
TRIM = color.rgb32(91, 103, 112)
CEILING = color.rgb32(210, 207, 195)
DOOR_BROWN = color.rgb32(135, 88, 53)

# All textures are bundled locally. No external downloads or network access.
TEXTURES = {
    name: load_texture('textures/' + name + '.png')
    for name in ('paint_wall', 'carpet_blue', 'tile_floor', 'ceiling_tile',
                 'wood_laminate', 'desk_laminate', 'metal', 'whiteboard')
}

def finish_surface(entity, texture_name, tile=(1, 1)):
    entity.texture = TEXTURES[texture_name]
    entity.texture_scale = tile
    # Use a neutral tint so original colored blocks don't darken textures.
    entity.color = color.white
    return entity



def block(position, scale, tint, collider='box'):
    item = Entity(model='cube', position=position, scale=scale,
                  color=tint, collider=collider, double_sided=True)
    GEOMETRY.append(item)
    return item


def floor(x1, x2, z1, z2, tint=ROOM_FLOOR):
    surface = block(((x1+x2)/2, -.5, (z1+z2)/2),
                    (x2-x1, 1, z2-z1), tint)
    finish_surface(surface, 'carpet_blue' if tint == CARPET else 'tile_floor',
                   (max(1, (x2-x1)/3), max(1, (z2-z1)/3)))


def ceiling(x1, x2, z1, z2):
    surface = block(((x1+x2)/2, WALL_HEIGHT+.1, (z1+z2)/2),
                    (x2-x1, .2, z2-z1), CEILING, collider=None)
    finish_surface(surface, 'ceiling_tile',
                   (max(1, (x2-x1)/3), max(1, (z2-z1)/3)))


def wall_x(x1, x2, z):
    if x2-x1 > .05:
        surface = block(((x1+x2)/2, WALL_HEIGHT/2, z),
                        (x2-x1, WALL_HEIGHT, .25), BEIGE)
        finish_surface(surface, 'paint_wall', (max(1, (x2-x1)/3), 1.5))


def wall_z(z1, z2, x):
    if z2-z1 > .05:
        surface = block((x, WALL_HEIGHT/2, (z1+z2)/2),
                        (.25, WALL_HEIGHT, z2-z1), BEIGE)
        finish_surface(surface, 'paint_wall', (max(1, (z2-z1)/3), 1.5))


def sign(room, x, z, orientation='x'):
    """Small number plaque facing the corridor; attached text uses local units."""
    if orientation == 'x':
        rotation = 180 if z > 0 else 0
        plaque = Entity(model='cube', position=(x, 2.99, z + (-.18 if z > 0 else .18)),
                        rotation_y=rotation, scale=(1.0, .35, .07),
                        color=color.rgb32(38, 47, 53), double_sided=True)
    else:
        rotation = -90 if x > 0 else 90
        plaque = Entity(model='cube', position=(x + (-.18 if x > 0 else .18), 2.99, z),
                        rotation_y=rotation, scale=(1.0, .35, .07),
                        color=color.rgb32(38, 47, 53), double_sided=True)
    GEOMETRY.append(plaque)
    # Keep the known v0.5 technique for 3D sign text.
    label = Text(parent=plaque, text=room, position=(0, -.14, -.55),
                 rotation_y=180, scale=(2.3, 5.5), origin=(0, 0),
                 color=color.white, billboard=False)
    GEOMETRY.append(label)


class Door(Entity):
    """Sliding door. The opening is in the corresponding corridor wall."""
    def __init__(self, room, x, z, narrator, orientation='x'):
        self.orientation = orientation
        super().__init__(model='cube', position=(x, 1.35, z),
                         scale=(1.8, 2.7, .16) if orientation == 'x'
                         else (.16, 2.7, 1.8),
                         color=DOOR_BROWN, collider='box', double_sided=True)
        finish_surface(self, 'wood_laminate', (1, 2))
        # Local coordinates are scaled by the door; decoration follows the slide.
        Entity(parent=self, model='cube', position=(0, -.43, -.53),
               scale=(.82, .10, .05), color=color.rgb32(122, 132, 137),
               collider=None)
        Entity(parent=self, model='cube', position=(.32, 0, -.56),
               scale=(.055, .17, .07), color=color.rgb32(186, 190, 188),
               collider=None)
        self.room = room
        self.narrator = narrator
        self.is_open = False
        self.closed_x = x
        self.closed_z = z
        self.busy = False

    def interact(self):
        if self.busy:
            return
        self.is_open = not self.is_open
        self.busy = True
        if self.is_open:
            self.collider = None
            if self.orientation == 'x':
                self.animate_x(self.closed_x + 2.05, duration=.45)
            else:
                self.animate_z(self.closed_z + 2.05, duration=.45)
            if self.room == '114':
                self.narrator('Room 114. You have arrived. That was suspiciously easy.')
            else:
                self.narrator(f'Room {self.room}. That was not in your instructions.')
        else:
            if self.orientation == 'x':
                self.animate_x(self.closed_x, duration=.45)
            else:
                self.animate_z(self.closed_z, duration=.45)
            self.narrator(f'Room {self.room} is closed again.')
        # Delay the next interaction until the slide finishes.
        from ursina import invoke
        invoke(self.finish_slide, delay=.5)

    def finish_slide(self):
        if not self.is_open:
            self.collider = 'box'
        self.busy = False


def doorway_on_horizontal_wall(room, x, z, narrator, doors):
    """Door in a wall running along X, centered at x."""
    # Header fills the space above the 2.7-high door.
    block((x, 3.1, z), (2, .8, .25), TRIM)
    door = Door(room, x, z, narrator, orientation='x')
    doors.append(door)
    sign(room, x, z)


def doorway_on_vertical_wall(room, x, z, narrator, doors):
    """Door in a wall running along Z, centered at z."""
    block((x, 3.1, z), (.25, .8, 2), TRIM)
    door = Door(room, x, z, narrator, orientation='z')
    doors.append(door)
    sign(room, x, z, orientation='z')


def horizontal_door_wall(x1, x2, z, room_positions, narrator, doors):
    left = x1
    for room, x in sorted(room_positions, key=lambda p: p[1]):
        wall_x(left, x-1, z)
        doorway_on_horizontal_wall(room, x, z, narrator, doors)
        left = x+1
    wall_x(left, x2, z)


def vertical_door_wall(z1, z2, x, room_positions, narrator, doors):
    bottom = z1
    for room, z in sorted(room_positions, key=lambda p: p[1]):
        wall_z(bottom, z-1, x)
        doorway_on_vertical_wall(room, x, z, narrator, doors)
        bottom = z+1
    wall_z(bottom, z2, x)


def build_main_corridor(narrator, doors):
    """199D, with the major rooms to north and south."""
    floor(-30, 28, -3, 3, CARPET)
    ceiling(-30, 28, -3, 3)

    north = [('115', -23), ('107', -8.5), ('105', 3.5),
             ('105A', 11), ('103', 16.5), ('101', 21.5), ('101A', 26)]
    south = [('114', -22), ('110', -6.5), ('108', 15)]
    horizontal_door_wall(-30, 28, 3, north, narrator, doors)
    horizontal_door_wall(-30, 28, -3, south, narrator, doors)

    # Room shells are intentionally empty for the architecture milestone.
    north_bounds = [-30, -16, -1, 8, 14, 19, 24, 28]
    south_bounds = [-30, -15, 2, 28]
    for a, b in zip(north_bounds, north_bounds[1:]):
        floor(a, b, 3, 15)
        ceiling(a, b, 3, 15)
        wall_x(a, b, 15)
    for x in north_bounds[1:-1]:
        wall_z(3, 15, x)
    for a, b in zip(south_bounds, south_bounds[1:]):
        floor(a, b, -15, -3)
        ceiling(a, b, -15, -3)
        wall_x(a, b, -15)
    for x in south_bounds[1:-1]:
        wall_z(-15, -3, x)
    # The western end remains open into corridor 199E.


def build_west_wing(narrator, doors):
    """120-series rooms around western passage 199E."""
    floor(-47, -30, -2.5, 2.5, CARPET)
    ceiling(-47, -30, -2.5, 2.5)
    wall_z(-2.5, 2.5, -47)

    # North and south clusters of smaller rooms.
    north_bounds = [-47, -41, -35, -30]
    south_bounds = [-47, -41, -35, -30]
    north_rooms = [('120D', -44), ('120F', -38), ('120G', -32.5)]
    south_rooms = [('120B', -44), ('120C', -38), ('120A', -32.5)]
    horizontal_door_wall(-47, -30, 2.5, north_rooms, narrator, doors)
    horizontal_door_wall(-47, -30, -2.5, south_rooms, narrator, doors)
    for a, b in zip(north_bounds, north_bounds[1:]):
        floor(a, b, 2.5, 10)
        ceiling(a, b, 2.5, 10)
        wall_x(a, b, 10)
        floor(a, b, -10, -2.5)
        ceiling(a, b, -10, -2.5)
        wall_x(a, b, -10)
    for x in north_bounds[1:-1]:
        wall_z(2.5, 10, x)
        wall_z(-10, -2.5, x)
    wall_z(2.5, 10, -47)
    wall_z(-10, -2.5, -47)
    # Simplified stairwell marker at the western end.
    block((-46.5, .12, 0), (.8, .24, 4.2), color.rgb32(120, 126, 132), collider=None)


def build_east_lobby(narrator, doors):
    """East entrance and Room 190 (former 090)."""
    floor(28, 43, -3, 7, CARPET)
    ceiling(28, 43, -3, 7)
    wall_x(28, 43, 7)
    wall_z(-3, 7, 43)
    # Lobby opens westward into the main corridor at x=28, z=-3..3.
    wall_z(3, 7, 28)

    # Elevator recess on north lobby wall, recognizable but not operational.
    block((37, 1.35, 6.78), (2.4, 2.7, .18),
          color.rgb32(115, 139, 159))
    block((37, 2.95, 6.58), (2.8, .3, .15), TRIM, collider=None)

    # Room 190 takes the large southeast area of the reference plan.
    floor(28, 43, -16, -3)
    ceiling(28, 43, -16, -3)
    wall_x(28, 43, -16)
    wall_z(-16, -3, 28)
    wall_z(-16, -3, 43)
    horizontal_door_wall(28, 43, -3, [('190', 35)], narrator, doors)

    # Simple entrance marker on east exterior wall.
    block((42.82, 1.4, 2), (.1, 2.8, 2.5),
          color.rgb32(103, 146, 167), collider=None)



def build_room_114():
    """Low-poly classroom inside the existing south-west Room 114 shell.

    The shell is x=-30..-15, z=-15..-3. Keep the door at (-22,-3)
    and its entry aisle clear so the player can walk inside.
    """
    desk_wood = color.rgb32(139, 112, 81)
    metal = color.rgb32(78, 84, 88)
    chair_blue = color.rgb32(54, 76, 94)
    board_white = color.rgb32(230, 232, 222)

    # Whiteboard on the south wall, facing toward the door.
    finish_surface(block((-22.5, 2.05, -14.80), (6.8, 1.35, .12),
                         board_white, collider=None), 'whiteboard')
    block((-22.5, 1.32, -14.68), (7.0, .06, .18), metal, collider=None)

    # Instructor podium and desk near the front (south) wall.
    finish_surface(block((-26.4, .92, -12.8), (1.4, .12, .8), desk_wood), 'desk_laminate')
    block((-26.4, .47, -12.8), (.9, .85, .55), metal)

    # Two rows of student tables with clear space at the entrance.
    # All furniture remains well south of the door at z=-3.
    for x in (-27.4, -23.8, -20.2, -16.9):
        for z in (-10.2, -7.3):
            finish_surface(block((x, .76, z), (1.75, .12, .85), desk_wood), 'desk_laminate')
            for dx in (-.69, .69):
                block((x + dx, .36, z), (.10, .7, .10), metal)
            # Chair placed behind each table toward the door.
            block((x, .43, z + .83), (.73, .15, .65), chair_blue)
            block((x, .82, z + 1.12), (.73, .84, .12), chair_blue)

    # Retro wall clock, mounted on the classroom's west wall.
    block((-29.82, 2.65, -10.5), (.09, .58, .58),
          color.rgb32(220, 218, 203), collider=None)


def build_hall_atmosphere():
    """Fluorescent fixtures and modest institutional hallway details."""
    fixture = color.rgb32(228, 224, 191)
    frame = color.rgb32(111, 119, 121)
    bulletin = color.rgb32(115, 84, 55)

    # Ceiling underside is at y=3.5. Fixtures hang just below it.
    for x in range(-27, 28, 7):
        block((x, 3.43, 0), (2.7, .08, .72), frame, collider=None)
        block((x, 3.37, 0), (2.5, .035, .56), fixture, collider=None)

    # Smaller fixtures in the lobby and classroom.
    for x, z in ((35, 1.5), (35, 4.8),
                 (-26, -9), (-19, -9)):
        block((x, 3.43, z), (2.4, .08, .7), frame, collider=None)
        block((x, 3.37, z), (2.2, .035, .54), fixture, collider=None)

    # Soft glow plates create the impression of illuminated fluorescent panels.
    # No realtime shadows: the late-1990s appearance stays inexpensive to render.
    for x in range(-27, 28, 7):
        block((x, 3.325, 0), (2.36, .012, .48),
              color.rgb32(255, 249, 211), collider=None)
    for x, z in ((35, 1.5), (35, 4.8), (-26, -9), (-19, -9)):
        block((x, 3.325, z), (2.05, .012, .46),
              color.rgb32(255, 249, 211), collider=None)

    # Bulletin board in a wall stretch between north-side doorways.
    block((-15.1, 1.85, 2.81), (2.5, 1.2, .10), bulletin,
          collider=None)
    for x, y in ((-15.8, 1.9), (-15.0, 2.0), (-14.2, 1.7)):
        block((x, y, 2.73), (.55, .7, .025),
              color.rgb32(218, 216, 195), collider=None)

    # Low-profile baseboards on safe uninterrupted wall stretches.
    for x1, x2, z in ((-30, -24.1, 2.78),
                       (-16, -9.6, 2.78),
                       (-30, -23.1, -2.78),
                       (-20.9, -15, -2.78)):
        block(((x1+x2)/2, .13, z), (x2-x1, .26, .10),
              frame, collider=None)


def build(narrator):
    """Return every interactive door for main.py."""
    GEOMETRY.clear()
    doors = []
    build_main_corridor(narrator, doors)
    build_west_wing(narrator, doors)
    build_east_lobby(narrator, doors)
    build_room_114()
    build_hall_atmosphere()
    print(f'Smith Hall v0.10 built: {len(doors)} doors, {len(GEOMETRY)} static pieces')
    return doors
