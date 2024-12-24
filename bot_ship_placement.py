import random

# Define the ship sizes and counts
SHIP_SIZES = [4, 3, 2, 2, 1, 1]  # One 4-long, one 3-long, two 2-long, two 1-long
GRID_SIZE = 8

# Create the grid
bot_button_state = [[False for _ in range(GRID_SIZE)] for _ in range(GRID_SIZE)]  # This will represent the occupied cells
ship_coordinates = []  # List to hold the coordinates of all placed ships

def is_within_bounds(x, y):
    return 0 <= x < GRID_SIZE and 0 <= y < GRID_SIZE

def can_place_ship(x, y, size, direction):
    if direction == "H":
        # Check if the ship fits horizontally
        if y + size > GRID_SIZE:
            return False
        # Check for occupied cells and adjacent cells
        for i in range(size):
            if bot_button_state[x][y + i] or not is_surrounding_cells_free(x, y + i):
                return False
    elif direction == "V":
        # Check if the ship fits vertically
        if x + size > GRID_SIZE:
            return False
        # Check for occupied cells and adjacent cells
        for i in range(size):
            if bot_button_state[x + i][y] or not is_surrounding_cells_free(x + i, y):
                return False
    return True

def is_surrounding_cells_free(x, y):
    # Check surrounding cells including diagonals
    for dx in [-1, 0, 1]:
        for dy in [-1, 0, 1]:
            if dx == 0 and dy == 0:
                continue  # Skip the cell itself
            nx, ny = x + dx, y + dy
            if is_within_bounds(nx, ny) and bot_button_state[nx][ny]:
                return False
    return True

def place_ship(size):
    placed = False
    while not placed:
        direction = random.choice(["H", "V"])
        x = random.randint(0, GRID_SIZE - 1)
        y = random.randint(0, GRID_SIZE - 1)
        if can_place_ship(x, y, size, direction):
            ship_coords = []  # List to store coordinates for the current ship
            for i in range(size):
                if direction == "H":
                    bot_button_state[x][y + i] = True
                    ship_coords.append((x, y + i))
                else:
                    bot_button_state[x + i][y] = True
                    ship_coords.append((x + i, y))
            ship_coordinates.append(ship_coords)  # Store the coordinates of this ship
            placed = True
            print(f"Placed ship of size {size} at {ship_coords} in direction {direction}")

def place_ships():
    for size in SHIP_SIZES:
        place_ship(size)

