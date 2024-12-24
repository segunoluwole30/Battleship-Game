import RPi.GPIO as GPIO
import time

# GPIO setup
BUZZER_PIN = 26  # Replace with your GPIO pin
GPIO.setmode(GPIO.BCM)
GPIO.setup(BUZZER_PIN, GPIO.OUT)

# Initialize PWM
pwm = GPIO.PWM(BUZZER_PIN, 1)  # Set initial frequency to 1Hz

def play_sound(frequency, duration):
    """Play a single tone."""
    pwm.ChangeFrequency(frequency)
    pwm.start(50)  # 50% duty cycle
    time.sleep(duration)
    pwm.stop()

def sweep_sound(start_freq, end_freq, duration):
    """Play a frequency sweep."""
    step = (end_freq - start_freq) / (duration * 100)  # Step size
    freq = start_freq
    for _ in range(int(duration * 100)):
        pwm.ChangeFrequency(freq)
        pwm.start(50)
        time.sleep(0.01)
        freq += step
    pwm.stop()

# Ship Placement Confirmation
def ship_placement_confirmation():
    sweep_sound(300, 600, 0.5)

# Missed Shot
def missed_shot_sound():
    for _ in range(2):
        play_sound(150, 0.3)
        time.sleep(0.1)

# Hit on a Ship
def hit_on_ship_sound():
    play_sound(800, 0.1)


def ship_sunk_sound():
    """Play a celebratory ascending and descending tone for a sunk ship."""
    # Ascending tones
    play_sound(400, 0.3)
    time.sleep(0.1)
    play_sound(600, 0.3)
    time.sleep(0.1)
    play_sound(800, 0.3)
    time.sleep(0.1)

def victory_sound():
    """Play a triumphant melody for victory."""
    # Rising tones to build excitement
    play_sound(400, 0.2)
    time.sleep(0.1)
    play_sound(500, 0.2)
    time.sleep(0.1)
    play_sound(600, 0.2)
    time.sleep(0.1)
    play_sound(800, 0.3)  # Peak triumphant note
    time.sleep(0.2)
    
    # Short celebratory melody
    play_sound(700, 0.2)
    time.sleep(0.1)
    play_sound(800, 0.2)
    time.sleep(0.1)
    play_sound(900, 0.3)
    time.sleep(0.2)
    
    # Concluding with a sweeping celebratory tone
    sweep_sound(500, 1000, 1)  # Sweeping up for a grand finish

# Error (Invalid Move)
def error_sound():
    play_sound(200, 0.2)

def bot_ship_sunk_sound():
    """Long, dissonant descending tone for a sunk ship."""
    sweep_sound(700, 200, 1.5)

def turn_indication_sound():
    """Play a quick, neutral beep to indicate a turn change."""
    play_sound(500, 0.2)
    time.sleep(0.05)
    play_sound(600, 0.2)
# Game Ready Sound
def game_ready_sound():
    """Play a welcoming tone to indicate the game is ready to be played."""
    play_sound(500, 0.5) 
    time.sleep(0.1)  
    play_sound(600, 0.5)  
    time.sleep(0.1)  
    play_sound(700, 0.5)  

def defeat_sound():
    """Play a deep, somber tone sequence for a game loss."""
    # Slow descending tones to convey sadness
    play_sound(500, 0.5)  # Start with a low, strong note
    time.sleep(0.3)
    play_sound(400, 0.4)  # Descend to a deeper note
    time.sleep(0.3)
    play_sound(300, 0.4)  # Continue descent
    time.sleep(0.3)
    play_sound(200, 0.5)  # End with the lowest, somber note
    time.sleep(0.4)

    # Final deep pulse to reinforce the sense of loss
    for _ in range(3):
        play_sound(150, 0.2)  # A low, short pulse
        time.sleep(0.1)
