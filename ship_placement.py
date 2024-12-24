
import RPi.GPIO as GPIO
import time
import board
import random
from adafruit_neotrellis.neotrellis import NeoTrellis
from adafruit_neotrellis.multitrellis import MultiTrellis
from collections import deque
# Create the I2C object for the NeoTrellis
i2c_bus = board.I2C()  

# Pin number where the button is connected
button_pin = 17

# Set up GPIO mode and pin
GPIO.setmode(GPIO.BCM) 
GPIO.setup(button_pin, GPIO.IN, pull_up_down=GPIO.PUD_UP)  # Enable pull-up resistor


start_time = time.time()


# # This is for a 2x2 array of NeoTrellis boards:
trelli = [
    [NeoTrellis(i2c_bus, False, addr=0x2E), NeoTrellis(i2c_bus, False, addr=0x2F)],
    [NeoTrellis(i2c_bus, False, addr=0x30), NeoTrellis(i2c_bus, False, addr=0x31)],
]

trellis = MultiTrellis(trelli)

end_time = time.time()
elapsed_time = end_time - start_time
print(elapsed_time)

trellis.brightness = 0.5

# some color definitions
OFF = (0, 0, 0)
RED = (255, 0, 0)
YELLOW = (255, 150, 0)
GREEN = (0, 255, 0)
CYAN = (0, 255, 255)
BLUE = (0, 0, 255)
PURPLE = (180, 0, 255)
WHITE = (255,255,255)
WHITE = (255,255,255)

SHIP_SIZES = [4, 3, 2, 2, 1, 1]
# 1) user will select all the buttons they want
#2) press submit
#3) the code will check if the grid has the correct number of ship siwth correct dimensions
#4a) if valid, check if any ships are touching
    #4aa) if valid, indication that the board is valid and gameplay can begin
    #4ab) if not valid, indication would show play it is invalid and request they make changes, and submit again
#)4b if not valid,  indicate that ship placement and request that more ships be put down


# wait for button submission
# get all the coordinates of pressed buttons
# check for correct ship lengths
# check for padding(non-touching ships)
# then gameplay can begin

#for loop starting from top (0,0)
    #upon examining a saved coordinate, check if (x,y+1) and or (x+1,y) are selected
    #if only one of the surrounding(touching) coordinates is also selected and all other surroundings of the current coordinate are unselected
        #then check another surrounding for the new coordinate
    #the new coordinate has to follow the same row/column pattern as previously checked coordinate or 
    #continues until there are no surrounding pressed buttons
shipCoord = []
shipDict = {4: [], 3: [], 2: [], 1: []} #shipDict[4] = [[list of coordinates]], starting with a length of 4

button_state = [[False for _ in range(8)] for _ in range(8)]

directions = [(0,1), (1,0), (0,-1), (-1,0)]

def is_within_bounds(x, y):
    return 0 <= x < 8 and 0 <= y < 8

# Group connected coordinates into ships using BFS with direction enforcement
def bfs(start_x, start_y, visited):
    queue = deque([(start_x, start_y)])
    visited[start_x][start_y] = True
    group = [(start_x, start_y)]
    direction = None  # To track if the ship is horizontal or vertical

    while queue:
        x, y = queue.popleft()

        # Check all 4 directions (right, down, left, up)
        for direction_val in directions:
            new_x = x + direction_val[0]
            new_y = y + direction_val[1]

            if is_within_bounds(new_x, new_y) and not visited[new_x][new_y] and button_state[new_x][new_y]:
                # Determine the direction of the ship based on the first neighbor
                if direction is None:
                    if new_x != x:
                        direction = "vertical"  # If the x changes, it's a vertical ship
                    elif new_y != y:
                        direction = "horizontal"  # If the y changes, it's a horizontal ship

                # If the ship is horizontal, only accept neighbors that change the y-coordinate
                if direction == "horizontal" and new_x == x:
                    queue.append((new_x, new_y))
                    visited[new_x][new_y] = True
                    group.append((new_x, new_y))

                # If the ship is vertical, only accept neighbors that change the x-coordinate
                elif direction == "vertical" and new_y == y:
                    queue.append((new_x, new_y))
                    visited[new_x][new_y] = True
                    group.append((new_x, new_y))

    return group # None means no invalid coordinates found

# Validate all ships placed on the board
def validate_ship_placement():
    visited = [[False for _ in range(8)] for _ in range(8)]
    ship_groups = []
    diagonal_invalid_coords = []  # To track diagonally adjacent coordinates
    shipDict.clear()
    errors_found = False  # Flag to track if any errors were found

    # Initialize shipDict with empty lists for each allowed ship length
    for size in SHIP_SIZES:
        shipDict[size] = []

    max_ship_size = max(SHIP_SIZES)  # Get the highest ship size

    # Step 1: Group ship parts and identify ships
    for x in range(8):
        for y in range(8):
            if button_state[x][y] and not visited[x][y]:
                ship_group = bfs(x, y, visited)
                ship_groups.append(ship_group)

                ship_length = len(ship_group)
                if ship_length in shipDict:
                    shipDict[ship_length].append(ship_group)

    # Step 2: Check for incomplete ship placements and mark as yellow if sizes don’t match
    ship_lengths = [len(group) for group in ship_groups]
    ship_lengths.sort(reverse=True)
    if ship_lengths != sorted(SHIP_SIZES, reverse=True):
        errors_found = True
        print("Invalid ship placement: Incorrect ship sizes.")
        for x in range(8):
            for y in range(8):
                if button_state[x][y]:
                    trellis.color(x, y, YELLOW)

    # Step 3: Check for excess ships based on expected counts and mark as purple if found
    total_required_ships = len(SHIP_SIZES)
    required_counts = {size: SHIP_SIZES.count(size) for size in SHIP_SIZES}
    found_counts = {size: 0 for size in SHIP_SIZES}

    for group in ship_groups:
        group_size = len(group)

        # Check if the group size is within the allowed sizes
        if group_size not in required_counts:
            # Mark oversized ship in red
            errors_found = True
            for coord in group:
                trellis.color(coord[0], coord[1], RED)
            print(f"Ship exceeds maximum allowed size at coordinates: {group}")
            continue  # Skip further checks for the oversized ship

        # Continue with normal count check
        if found_counts[group_size] < required_counts[group_size]:
            found_counts[group_size] += 1
        else:
            errors_found = True
            # Mark the extra ship as purple
            for coord in group:
                trellis.color(coord[0], coord[1], PURPLE)
            print(f"Extra ship detected with length {group_size} at coordinates: {group}")



    # Step 4: Check for diagonally adjacent ship parts
    for x in range(8):
        for y in range(8):
            if button_state[x][y]:
                # Check all diagonal coordinates
                diagonal_neighbors = [
                    (x - 1, y - 1), (x - 1, y + 1), 
                    (x + 1, y - 1), (x + 1, y + 1)
                ]
                
                for dx, dy in diagonal_neighbors:
                    if is_within_bounds(dx, dy) and button_state[dx][dy]:
                        diagonal_invalid_coords.append((dx, dy))
                        errors_found = True

    # Highlight diagonally adjacent parts in red
    for diag_coord in diagonal_invalid_coords:
        trellis.color(diag_coord[0], diag_coord[1], RED)

    if diagonal_invalid_coords:
        print("Invalid ship placement detected: Diagonal adjacency is not allowed.")

    

    

    # Final validation: if no errors were found, turn all ship parts green
    if not errors_found:
        for group in ship_groups:
            for coord in group:
                trellis.color(coord[0], coord[1], GREEN)
        print("Valid ship placement!")
        print("Ship Dictionary:", shipDict)
        return True
    else:
        print("Errors detected. Please correct ship placement.")
        return False



def shipPlacement(xcoord, ycoord, edge):
    pair = (xcoord, ycoord)

    if (edge == NeoTrellis.EDGE_RISING):
        button_state[xcoord][ycoord] = not button_state[xcoord][ycoord]

        if (button_state[xcoord][ycoord]):
            trellis.color(xcoord, ycoord, BLUE)
            shipCoord.append(pair)
        else:
            trellis.color(xcoord, ycoord, OFF)
            if pair in shipCoord:
                shipCoord.remove(pair)
