#!/usr/bin/python3

from time import sleep, time
import RPi.GPIO as GPIO
import board
from random import randint, choice
from neopixel import NeoPixel
from collections import deque
from adafruit_neotrellis.neotrellis import NeoTrellis
from adafruit_neotrellis.multitrellis import MultiTrellis
from ship_placement import validate_ship_placement, shipPlacement, button_state, shipDict, is_within_bounds, trelli, trellis, directions
from bot_ship_placement import place_ships, ship_coordinates, bot_button_state
import testBuzzer as buzzer

# Initialize GPIO and NeoTrellis
i2c_bus = board.I2C()
button_pin = 17 
GPIO.setmode(GPIO.BCM)
GPIO.setup(button_pin, GPIO.IN, pull_up_down=GPIO.PUD_UP)

# Define GPIO pins for each encoder (A2, A1, A0)
x_encoder_outputs = [24, 25, 12]  # Encoder for x (row) position
y_encoder_outputs = [5, 6, 13]    # Encoder for y (column) position

# NeoPixel setup
NUM_PIXELS = 64
PIXEL_PIN = board.D18 
pixels = NeoPixel(PIXEL_PIN, NUM_PIXELS, brightness=0.1, auto_write=False)

# Set up encoder pins as inputs with pull-up resistors
for pin in x_encoder_outputs + y_encoder_outputs:
    GPIO.setup(pin, GPIO.IN, pull_up_down=GPIO.PUD_UP)


# Define RGB LED GPIO pins
RED_PIN = 16
GREEN_PIN = 20
BLUE_PIN = 21

# Set up RGB LED pins
GPIO.setup(RED_PIN, GPIO.OUT)
GPIO.setup(GREEN_PIN, GPIO.OUT)
GPIO.setup(BLUE_PIN, GPIO.OUT)



# Function to set RGB LED color
def set_led_color(red, green, blue):
    GPIO.output(RED_PIN, red)
    GPIO.output(GREEN_PIN, green)
    GPIO.output(BLUE_PIN, blue)

# Color constants for RGB LED
PLAYER_TURN_COLOR = (0, 0, 1)  # Blue for player's turn
BOT_TURN_COLOR = (0, 1, 0)     # Green for bot's turn
OFF_COLOR = (0, 0, 0)          


# some color definitions
OFF = (0, 0, 0)
RED = (255, 0, 0)
YELLOW = (255, 150, 0)
GREEN = (0, 255, 0)
CYAN = (0, 255, 255)
BLUE = (0, 0, 255)
PURPLE = (180, 0, 255)
WHITE = (255,255,255)

# Initialize ship size and coordinates
SHIP_SIZES = [4, 3, 2, 2, 1, 1]

'''Data structures to store bots hits, misses, and sunk ships'''
# Track the last hit coordinates
last_hit = None

# Track all guessed coordinates to avoid repetition
guessed_positions = set()


# Track coordinates of sunk ships
sunk_coordinates = set()

#Track all neighbors of sunk coordinates to avoid irrelevant guessing
#sunk_coordinates_neighbors = set()

'''Data structures to store human player's hits, misses, and sunk ships'''
# Store previously hit pixels in a set (to keep track of them)
hit_pixels = set()

#Store all user guesses
guessed_pixels = set()

# Store previously missed pixels in a set (to keep track of them)
missed_pixels = set()

# Store ships that are sunk
sunk_ships = set() 

# Function to read the encoder position
def read_encoder_position(encoder_outputs):
    a2, a1, a0 = (GPIO.input(pin) for pin in encoder_outputs)
    return (not a2) << 2 | (not a1) << 1 | (not a0)

def stable_reading(encoder_outputs, required_stable_cycles=3, delay=0.01):
    """Ensure stable reading by checking multiple times."""
    last_read = read_encoder_position(encoder_outputs)
    stable_count = 0

    while stable_count < required_stable_cycles:
        sleep(delay)
        current_read = read_encoder_position(encoder_outputs)

        # Treat '7' as a placeholder position for transition
        if current_read == 7:
            # Allow 7 as a valid transition state temporarily
            stable_count += 1
            continue  # Skip this cycle to allow further stabilization

        if current_read == last_read:
            stable_count += 1
        else:
            last_read = current_read
            stable_count = 0

    return last_read

# Function to calculate NeoPixel index based on row and column in snake pattern
def get_pixel_index(row, column):
    #Note: (0, 0) is in the top left
    adjusted_row = 7 - row
    if (adjusted_row % 2 == 0):
        return adjusted_row * 8 + column
    else:
        return adjusted_row * 8 + (7-column)

# Function to check if a ship is fully hit and update its sunk state
def is_ship_sunk(ship_index):
    ship = ship_coordinates[ship_index]
    if all(coord in user_ship_hits[ship_index] for coord in ship):
        sunk_ships.add(ship_index)  # Mark ship as sunk
        return True
    return False

# Function to update ship's LED to purple if all parts are hit
def update_ship_color():
    for ship_index, ship in enumerate(ship_coordinates):
        if ship_index in sunk_ships:
            for coord in ship:
                active_pixel = get_pixel_index(coord[0], coord[1])
                pixels[active_pixel] = PURPLE
    pixels.show()





def get_random_coordinate():
    """Generate a random (x, y) coordinate within bounds."""
    return randint(0, 7), randint(0, 7)

def get_nearby_coordinate(hit_coord):
    """Generate a coordinate near the last hit."""
    x, y = hit_coord
    possible_moves = [(x + dx, y + dy) for dx, dy in [(-1, 0), (1, 0), (0, -1), (0, 1)]]
    # Filter moves to stay within bounds and avoid already guessed or sunk positions
    valid_moves = [(nx, ny) for nx, ny in possible_moves if is_within_bounds(nx, ny) and (nx, ny) not in guessed_positions and (nx, ny) not in sunk_coordinates]
    return choice(valid_moves) if valid_moves else get_random_coordinate()

def all_ships_sunk():
    """Check if all ships have been sunk (all hits equal to ship length for player or bot)."""
    
    # Check if all user ships are sunk
    all_user_ships_sunk = all(ship_hits[tuple(ship)] == len(ship) for length, ships in shipDict.items() for ship in ships)
    
    # Check if all bot ships are sunk
    all_bot_ships_sunk = all(len(user_ship_hits[i]) == len(ship_coordinates[i]) for i in range(len(ship_coordinates)))

    if all_bot_ships_sunk:
        buzzer.victory_sound()
        print("User sunk all bots ships!")
        return True
    elif all_user_ships_sunk:
        buzzer.defeat_sound()
        print("User lost")
        return True

    return False

def all_coordinates_guessed():
    """Check if all valid coordinates have been guessed."""
    return len(guessed_positions) == 64

def guess_coordinate():
    """Bot makes a single guess."""
    global last_hit
    # Choose a random coordinate (or based on last hit if desired)
    if last_hit and last_hit not in sunk_coordinates:
        # If there was a previous hit and it is not a sunken ship, try to guess nearby
        x, y = get_nearby_coordinate(last_hit)
    else:
        # Otherwise, pick a random coordinate
        x, y = get_random_coordinate()

    #Ensure the newly acquired coordinate is not a direct neighbor or diagonal neighbor of a sunken ship
    # Ensure the newly acquired coordinate has not been guessed already or part of a sunken ship
    while (x, y) in guessed_positions or (x, y) in sunk_coordinates: #or (x,y) in sunk_coordinates_neighbors:
        x, y = get_random_coordinate() if not last_hit else get_nearby_coordinate(last_hit)

    guessed_positions.add((x, y))
    print(len(guessed_positions))
    # print(f"Bot guesses: ({x}, {y})")

    # Check if the guess hits a ship
    hit = False
    for ship_length, ships in shipDict.items():
        for ship in ships:
            if (x, y) in ship:
                hit = True
                last_hit = (x, y)  # Update last hit position
                ship_hits[tuple(ship)] += 1
                # print(f"Hit at ({x}, {y})!")

                # Check if the ship is sunk
                if ship_hits[tuple(ship)] == ship_length:
                    buzzer.bot_ship_sunk_sound()
                    print(f"Ship of length {ship_length} is sunk!")
                    for coord in ship:
                        sunk_coordinates.add(coord)  # Mark ship coordinates as sunk
                        # for i in directions:
                        #     sunk_neighbors_x = coord[0] + i[0]
                        #     sunk_neighbors_y = coord[1] + i[1]
                        #     sunk_neighbors = (sunk_neighbors_x, sunk_neighbors_y)
                        #     print(sunk_neighbors)
                        #     if is_within_bounds(sunk_neighbors_x, sunk_neighbors_y) and sunk_neighbors not in sunk_coordinates:
                        #         sunk_coordinates_neighbors.add(sunk_neighbors)
                        #         trellis.color(sunk_neighbors[0], sunk_neighbors[1], WHITE)
                        trellis.color(coord[0], coord[1], PURPLE) 
                else:
                    trellis.color(x, y, RED)
                break
        if hit:
            break

    if not hit:
        # print(f"Miss at ({x}, {y}).")
        trellis.color(x, y, WHITE)

    


def reset_game():
    """Reset game settings, clear board, and reinitialize."""
    global shipDict, ship_coordinates, button_state, bot_button_state
    shipDict.clear()
    ship_coordinates.clear()
    button_state = [[False for _ in range(8)] for _ in range(8)]
    bot_button_state = [[False for _ in range(8)] for _ in range(8)]
    for x in range(8):
        for y in range(8):
            trellis.color(x, y, OFF)
    set_led_color(*OFF_COLOR)
    print("Game has been reset. You can place ships again.")
    
ship_already_sunk=[]
DEBOUNCE_DELAY = 0.1
def player_turn():
    global user_ship_hits
    """Actions for the player's turn."""
    set_led_color(*PLAYER_TURN_COLOR)
    buzzer.turn_indication_sound()
    # print("Player's turn")

    # Reset position variables at the start of the player's turn
    current_x = 0
    current_y = 0
    previous_x = current_x
    previous_y = current_y
    last_active_pixel = get_pixel_index(current_x, current_y)  # Index of the initial active pixel

    while True:
        # Get stable positions from both encoders
        new_x = stable_reading(x_encoder_outputs)
        new_y = stable_reading(y_encoder_outputs)

        # Update the active pixel only when the position changes
        if new_x != previous_x or new_y != previous_y:
            active_pixel = get_pixel_index(new_x, new_y)

            # First, reset all pixels (turn them off)
            for i in range(NUM_PIXELS):
                pixels[i] = OFF

            # Light up all the previously hit pixels in red
            for hit_pixel in hit_pixels:
                pixels[hit_pixel] = RED

            # Light up all the previously missed pixels in white
            for miss_pixel in missed_pixels:
                pixels[miss_pixel] = WHITE

            # Ensure ships that have been sunk stay purple
            update_ship_color()

            # Light up the active pixel in blue
            pixels[active_pixel] = BLUE  # Blue for active pixel

            pixels.show()

            # Update previous positions and last active pixel
            previous_x = new_x
            previous_y = new_y
            last_active_pixel = active_pixel

        if GPIO.input(button_pin) == GPIO.LOW:
            print(f"Button pressed at position ({new_x}, {new_y})")
            active_pixel = get_pixel_index(new_x, new_y)
            # guessed_pixels.add(active_pixel)

            if (active_pixel) in guessed_pixels:
                print(f"Position was already guessed")
                for i in range(3):
                    buzzer.error_sound()
                    pixels[active_pixel] = YELLOW
                    pixels.show()
                    sleep(0.1)
                    pixels[active_pixel] = OFF
                    pixels.show()
                    sleep(0.1)
                if active_pixel in hit_pixels:
                    pixels[active_pixel] = RED
                elif active_pixel in missed_pixels:
                    pixels[active_pixel] = WHITE
                elif active_pixel in sunk_coordinates:
                    pixels[active_pixel] = PURPLE
                pixels.show()
                continue

            else:
                guessed_pixels.add(active_pixel)

            # Check if the current position matches any ship coordinates
            hit = False
            for ship_index, ship in enumerate(ship_coordinates):
                if (new_x, new_y) in ship:
                    if (new_x, new_y) not in user_ship_hits[ship_index]:
                        buzzer.hit_on_ship_sound()
                        # Mark the pixel red if it's part of a ship
                        active_pixel = get_pixel_index(new_x, new_y)
                        pixels[active_pixel] = RED 
                        user_ship_hits[ship_index].add((new_x, new_y))  # Record the hit
                        hit_pixels.add(active_pixel)  # Keep track of the hit pixel
                        pixels.show()
                        print("Hit!")
                        hit = True
                        break

            if not hit:
                buzzer.missed_shot_sound()
                # If it's not a hit, mark it as a miss (white)
                active_pixel = get_pixel_index(new_x, new_y)
                pixels[active_pixel] = WHITE
                missed_pixels.add(active_pixel)
                pixels.show()
                print("Miss!")

            # After each hit, check if any ship is sunk
            for ship_index in range(len(ship_coordinates)):
                if is_ship_sunk(ship_index) and ship_index not in ship_already_sunk:
                    buzzer.ship_sunk_sound()
                    ship_already_sunk.append(ship_index)

            # After each hit, update the ship colors to reflect sunk ships
            update_ship_color()

            # Break after the turn ends (after one shot)
            break

        # Wait for a short time to debounce
        sleep(DEBOUNCE_DELAY)



def bot_turn():
    global ship_hits
    """Actions for the bot's turn."""
    set_led_color(*BOT_TURN_COLOR)
    print("Bot's turn")
    
    sleep(2)
    guess_coordinate()


for x in range(8):
    for y in range(8):
        # Activate rising edge events on all keys
        trellis.activate_key(x, y, NeoTrellis.EDGE_RISING)
        trellis.set_callback(x, y, shipPlacement)



def start_turns():
    """Starts alternating turns between the player and bot."""
    global ship_hits, user_ship_hits
    while True:
        player_turn()
        sleep(1)

        bot_turn()
        sleep(0.3)

        # Game conditions checked here to end loop
        if all_ships_sunk():
            print("The game is over! All ships have been sunk.")
            break

def place_ships_and_start_game():
    """Place ships and start alternating turns."""
    if validate_ship_placement():
        buzzer.ship_placement_confirmation()
        # Initialize ship_hits with zeros for each ship's coordinates, converting lists to tuples
        global ship_hits, user_ship_hits
        ship_hits = {}
        
        # Store the ship coordinates as tuples in the ship_hits dictionary
        for ships in shipDict.values():
            for ship in ships:
                ship_hits[tuple(ship)] = 0  # Initialize the hit count for each ship (as tuple)
        
        print("Ship hits initialized:", ship_hits)
        sleep(3)
        for x in range(8):
            for y in range(8):
                if button_state[x][y]:
                    trellis.color(x, y, BLUE)

        place_ships()  # Bot places ships
        # Track the hits for each ship
        user_ship_hits = {i: set() for i in range(len(ship_coordinates))}  # Index of ship to list of hit coordinates
        print("user Ship hits initialized:", user_ship_hits)
        print("Game can begin")
        print("User ships:", shipDict)
        print("Bot ships:", ship_coordinates)
        
        start_turns() 
    else:
        buzzer.error_sound()


def play_game():
    """Main game loop."""
    global ship_hits
    while True:
        # Sync Trellis events
        trellis.sync()
        sleep(0.02)
        
        if GPIO.input(button_pin) == GPIO.LOW:
            # After placing ships, the game will proceed
            place_ships_and_start_game()

try:
    print("Ready to place ships.")
    buzzer.game_ready_sound()
    play_game()

finally:
    for x in range(8):
        for y in range(8):
            trellis.color(x, y, OFF)
    set_led_color(*OFF_COLOR)  
    pixels.fill((0, 0, 0))
    pixels.show()
    buzzer.pwm.stop()
    GPIO.cleanup()