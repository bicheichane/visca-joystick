import os
import time

os.environ['PYGAME_HIDE_SUPPORT_PROMPT'] = "hide"

from visca_over_ip.exceptions import ViscaException
from numpy import interp

from config import ips, mappings, sensitivity_tables, help_text, Camera, long_press_time
from startup_shutdown import shut_down, configure
import pyglet

class JoystickEventHandler:
    def on_joyaxis_motion(_self, joystick, axis, value):
        print(f'axis {axis}: {value}')
        pass

invert_tilt = True
cam = None
last_focus_time = None
button_down_time = {key: None for key in mappings['preset']}

joystick = pyglet.input.get_joysticks()[0]
joystick.open()





def joystick_init(print_battery=False):
    """Initializes pygame and the joystick.
    This is done occasionally because pygame seems to put the controller to sleep otherwise
    :param print_battery: If set to True, the battery charge status of the joystick will be printed out
    """
    global joystick, joystick_reset_time

    

    while True:
        try:
            joystick = pygame.joystick.Joystick(0)
        except pygame.error:
            input('No controller found. Please connect one then press enter: ')
        else:
            break

    if print_battery:
        print('Joystick battery is', joystick.get_power_level())

    print("axis count: " + str(joystick.get_numaxes()))
    print("axis 0: " + str(joystick.get_axis(0)))
    print("axis 1: " + str(joystick.get_axis(1)))
    print("axis 2: " + str(joystick.get_axis(2)))


def joy_pos_to_cam_speed(axis_position: float, table_name: str, invert=True) -> int:
    """Converts from a joystick axis position to a camera speed using the given mapping

    :param axis_position: the raw value of an axis of the joystick -1 to 1
    :param table_name: one of the keys in sensitivity_tables
    :param invert: if True, the sign of the output will be flipped
    :return: an integer which can be fed to a Camera driver method
    """
    sign = 1 if axis_position >= 0 else -1
    if invert:
        sign *= -1

    table = sensitivity_tables[table_name]

    return sign * round(
        interp(abs(axis_position), table['joy'], table['cam'])
    )


def update_focus():
    """Reads the state of the bumpers and toggles manual focus, focuses near, or focuses far."""
    global last_focus_time
    time_since_last_adjust = time.time() - last_focus_time if last_focus_time else 30

    focus_near = joystick.get_button(mappings['focus']['near'])
    focus_far = joystick.get_button(mappings['focus']['far'])
    manual_focus = cam.get_focus_mode() == 'manual'

    if focus_near and focus_far and time_since_last_adjust > .4:
        last_focus_time = time.time()
        if manual_focus:
            cam.set_focus_mode('auto')
            print('Auto focus')
        else:
            cam.set_focus_mode('manual')
            print('Manual focus')

    elif focus_far and manual_focus and time_since_last_adjust > .1:
        last_focus_time = time.time()

        cam.manual_focus(-1)
        time.sleep(.01)
        cam.manual_focus(0)

    elif focus_near and manual_focus and time_since_last_adjust > .1:
        last_focus_time = time.time()

        cam.manual_focus(1)
        time.sleep(.01)
        cam.manual_focus(0)


def update_brightness():
    if joystick.get_axis(mappings['brightness']['up']) > .9:
        cam.increase_exposure_compensation()

    if joystick.get_axis(mappings['brightness']['down']) > .9:
        cam.decrease_exposure_compensation()


def connect_to_camera(cam_index) -> Camera:
    """Connects to the camera specified by cam_index and returns it"""
    global cam

    if cam:
        cam.zoom(0)
        cam.pantilt(0, 0)
        cam.close_connection()

    cam = Camera(ips[cam_index])

    try:
        cam.zoom(0)
    except ViscaException:
        pass

    print(f"Camera {cam_index + 1}")

    return cam


def handle_button_presses():
    global invert_tilt, cam

    for event in pygame.event.get(eventtype=pygame.JOYBUTTONDOWN):
        btn_no = event.dict['button']
        if btn_no == mappings['other']['exit']:
            shut_down(cam)

        elif btn_no in mappings['cam_select']:
            cam = connect_to_camera(mappings['cam_select'][btn_no])

        elif btn_no == mappings['other']['invert_tilt']:
            invert_tilt = not invert_tilt
            print('Tilt', 'inverted' if not invert_tilt else 'not inverted')


def handle_preset_buttons():
    """Distinguishes between short presses and long presses for recalling and saving presets"""
    global cam, button_down_time

    for event in pygame.event.get(eventtype=pygame.JOYBUTTONUP):
        btn_no = event.dict['button']

        if btn_no in mappings['preset']:
            cam.recall_preset(mappings['preset'][btn_no])

    for btn_no in mappings['preset']:
        if joystick.get_button(btn_no):
            if button_down_time[btn_no] is None:
                button_down_time[btn_no] = time.time()

            elif time.time() - button_down_time[btn_no] > long_press_time:
                cam.save_preset(mappings['preset'][btn_no])

        else:
            button_down_time[btn_no] = None


def main_loop():
    while True:
        timeout = pyglet.clock.tick()
        pyglet.app.platform_event_loop.step(timeout)
        #handle_button_presses()
        #update_brightness()
        #update_focus()
        #handle_preset_buttons()

        global joystick

        #cam.pantilt(
        #    pan_speed=joy_pos_to_cam_speed(joystick.get_axis(mappings['movement']['pan']), 'pan'),
        #    tilt_speed=joy_pos_to_cam_speed(joystick.get_axis(mappings['movement']['tilt']), 'tilt', invert_tilt)
        #)
        
        pan_speed=joy_pos_to_cam_speed(joystick.x, 'pan'),
        tilt_speed=joy_pos_to_cam_speed(joystick.y, 'tilt', invert_tilt)
        zoom_speed=joy_pos_to_cam_speed(joystick.z, 'zoom')

        print(f"pan= {pan_speed} | tilt= {tilt_speed} | zoom= {zoom_speed}")

        #120 fps
        #time.sleep(0.0083)
        time.sleep(0.1)
        #cam.zoom(joy_pos_to_cam_speed(joystick.get_axis(mappings['movement']['zoom']), 'zoom'))


if __name__ == "__main__":
    print('Welcome to VISCA Joystick!')
    #joystick_init()
    #print()
    #print(help_text)
    #configure()
    #cam = connect_to_camera(0)



    while True:
        try:
            #pyglet.app.run(1)
            main_loop()

        except Exception as exc:
            print("Exception: " + str(exc))
        
        time.sleep(1)
