"""First Floor: Smith Hall v0.10 — The Empty Classroom.

Branching narrative layer over the stable v0.7 building geometry.
"""
from ursina import *
from ursina.prefabs.first_person_controller import FirstPersonController
from building import build
from pathlib import Path

ASSET_DIR = Path(__file__).resolve().parent / "sounds"

app = Ursina()
window.title = 'First Floor: Smith Hall v0.10 — The Empty Classroom'
window.borderless = False
window.color = color.rgb32(40, 60, 90)
camera.fov = 90
camera.clip_plane_near = .1
camera.clip_plane_far = 200

subtitle = Text(text='', position=(-.72, -.43), scale=.75,
                color=color.white, background=True)
help_text = Text(text='WASD move | Mouse look | E door | Shift run | R restart | F3 debug | M sound | Esc mouse',
                 position=(-.72, .45), scale=.60, color=color.black)
objective_text = Text(text='', position=(-.72, .31), scale=.75,
                      color=color.rgb32(245, 232, 174), background=True)
interaction = Text(text='', position=(-.15, -.28), scale=1, color=color.white)
debug = Text(text='', position=(-.72, .38), scale=.7, color=color.black)
debug_enabled = True
sound_enabled = True
footstep_clock = 0.0
footstep_index = 0

# Audio files are bundled locally. A missing audio device should not prevent play.
def sound(name, volume=.3, loop=False, autoplay=False):
    try:
        return Audio(str(ASSET_DIR / name), volume=volume, loop=loop, autoplay=autoplay)
    except Exception as exc:
        print('Audio unavailable:', name, exc)
        return None

ambient_hum = sound('fluorescent_hum.wav', .12, loop=True, autoplay=True)
elevator_hum = sound('elevator_hum.wav', .07, loop=True, autoplay=True)
step_sounds = [sound('footstep1.wav', .30), sound('footstep2.wav', .30)]
door_sound = sound('door_slide.wav', .35)
ending_sound = sound('ending_chime.wav', .25)

# Light tint, rather than expensive dynamic shadows, preserves the retro look.
AmbientLight(color=color.rgba(175, 179, 188, 255))
DirectionalLight(rotation=(35, -30, 15), color=color.rgba(115, 115, 110, 255))


# Narrative states: FIND_114 -> GO_TO_190 -> ENDING
story_state = 'FIND_114'
ending = None
visited_west_early = False
visited_190_early = False


def narrate(message):
    """Called by both the story and the existing door objects."""
    subtitle.text = 'NARRATOR: ' + message


def set_objective(message):
    objective_text.text = 'OBJECTIVE: ' + message


doors = build(narrate)
player = FirstPersonController(position=(35, 0, 0), speed=4.5, enabled=True)
player.rotation_y = -90
player.camera_pivot.rotation_x = 0
player.gravity = 1
player.mouse_sensitivity = Vec2(40, 40)
mouse.locked = True
mouse.visible = False


def inside(x1, x2, z1, z2):
    """Check whether the player's feet are within a rectangular room area."""
    return x1 < player.x < x2 and z1 < player.z < z2


def nearest_door():
    nearest = None
    best_distance = 2.7
    for door in doors:
        dx = door.closed_x - player.x
        dz = door.closed_z - player.z
        distance = (dx * dx + dz * dz) ** .5
        if distance < best_distance:
            nearest = door
            best_distance = distance
    return nearest


def finish_story(route):
    global story_state, ending
    if story_state == 'ENDING':
        return
    story_state = 'ENDING'
    ending = route
    if sound_enabled and ending_sound: ending_sound.play()
    if route == 'obedient':
        narrate('Room 190. Precisely where you were told to go. The meeting has apparently moved again. ENDING: THE MODEL EMPLOYEE. Press R to restart.')
        set_objective('The Model Employee ending — press R to restart')
    else:
        narrate('The west wing. You have chosen curiosity over instructions. I suppose we will have to rewrite the itinerary. ENDING: THE DETOUR. Press R to restart.')
        set_objective('The Detour ending — press R to restart')


def reset_story():
    global story_state, ending, visited_west_early, visited_190_early
    story_state = 'FIND_114'
    ending = None
    visited_west_early = False
    visited_190_early = False
    player.position = (35, 0, 0)
    player.rotation_y = -90
    player.camera_pivot.rotation_x = 0
    # Restore every door without animations so a restart is deterministic.
    for door in doors:
        door.is_open = False
        door.busy = False
        door.x = door.closed_x
        door.z = door.closed_z
        door.collider = 'box'
    set_objective('Find Room 114')
    narrate('Welcome to Smith Hall. Please proceed to Room 114. This should be simple.')
    mouse.locked = True
    mouse.visible = False
    if ending_sound: ending_sound.stop()


def update():
    global story_state, visited_west_early, visited_190_early, footstep_clock, footstep_index

    player.speed = 7 if held_keys['shift'] else 4.5
    # Footsteps trigger only while the player is moving on the floor.
    moving = any(held_keys[k] for k in ('w', 'a', 's', 'd')) and mouse.locked
    if moving and getattr(player, 'grounded', True):
        footstep_clock += time.dt
        interval = .32 if held_keys['shift'] else .47
        if footstep_clock >= interval:
            footstep_clock = 0
            if sound_enabled and step_sounds[footstep_index]:
                step_sounds[footstep_index].play()
            footstep_index = 1 - footstep_index
    else:
        footstep_clock = .20

    # The elevator motor becomes a little more audible in the east lobby.
    if elevator_hum:
        near_elevator = max(0, 1 - ((player.x-37)**2 + (player.z-6)**2)**.5 / 14)
        elevator_hum.volume = (.025 + .15 * near_elevator) if sound_enabled else 0

    door = nearest_door()
    interaction.text = (f'[E] {"Close" if door.is_open else "Open"} Room {door.room}'
                        if door else '')
    debug.text = (f'XYZ: {player.x:.1f}, {player.y:.1f}, {player.z:.1f} '
                  f'| Facing: {player.rotation_y:.0f} | Story: {story_state}') if debug_enabled else ''

    if story_state == 'ENDING':
        return

    # Coordinates are based on the room shells in building.py v0.7.
    in_114 = inside(-29.7, -15.3, -14.7, -4.6)
    in_190 = inside(28.4, 42.6, -15.7, -4.6)
    in_west = inside(-46.7, -30.3, -2.2, 2.2)

    if story_state == 'FIND_114':
        if in_114:
            story_state = 'GO_TO_190'
            set_objective('Go to Room 190 — or explore the west wing')
            narrate('Room 114. Empty. Not a student in sight. No matter. The meeting has been relocated to Room 190. Please proceed there directly.')
        elif in_west and not visited_west_early:
            visited_west_early = True
            narrate('That is the west wing. Room 114 is in the other direction. I was under the impression that we had agreed on a destination.')
        elif in_190 and not visited_190_early:
            visited_190_early = True
            narrate('Room 190? Already? That is remarkably premature. You have not even discovered why you need to be here.')

    elif story_state == 'GO_TO_190':
        if in_190:
            finish_story('obedient')
        elif in_west:
            finish_story('detour')


def input(key):
    global debug_enabled, sound_enabled
    if key == 'e':
        door = nearest_door()
        if door:
            door.interact()
            if sound_enabled and door_sound: door_sound.play()
    elif key == 'r':
        reset_story()
    elif key == 'm':
        sound_enabled = not sound_enabled
        if ambient_hum: ambient_hum.volume = .12 if sound_enabled else 0
        if elevator_hum and not sound_enabled: elevator_hum.volume = 0
        narrate('Building audio ' + ('enabled.' if sound_enabled else 'muted.'))
    elif key == 'f3':
        debug_enabled = not debug_enabled
    elif key == 'escape':
        mouse.locked = not mouse.locked
        mouse.visible = not mouse.locked


reset_story()
print('Smith Hall v0.10 loaded:', len(doors), 'interactive doors')
app.run()
