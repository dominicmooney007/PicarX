# Robot HAT & PiCar-X Student User Guide

> **Libraries covered:** `robot_hat` v2.3.5 (HAL) and `picarx` v2.0.5 (car control)
> **Target platform:** Raspberry Pi with Robot HAT V2 expansion board
> **Requires:** Python 3.7+

---

## Table of Contents

1. [Introduction](#1-introduction)
2. [Hardware Overview](#2-hardware-overview)
3. [Installation & First Boot](#3-installation--first-boot)
4. [Digital GPIO — Pin Class](#4-digital-gpio--pin-class)
5. [Analog Input — ADC Class](#5-analog-input--adc-class)
6. [PWM Output](#6-pwm-output)
7. [Servo Motors](#7-servo-motors)
8. [DC Motors](#8-dc-motors)
9. [Sensor Modules](#9-sensor-modules)
10. [Audio — Music & TTS](#10-audio--music--tts)
11. [Configuration & Calibration](#11-configuration--calibration)
12. [Robot Class — Multi-Servo Framework](#12-robot-class--multi-servo-framework)
13. [PiCar-X — High-Level Car Control](#13-picar-x--high-level-car-control)
14. [Autonomous Behaviors](#14-autonomous-behaviors)
15. [Utilities & Troubleshooting](#15-utilities--troubleshooting)
16. [API Quick Reference](#16-api-quick-reference)
17. [Pin Map & Wiring Appendix](#17-pin-map--wiring-appendix)

---

## 1. Introduction

### What Is the Robot HAT?

The **Robot HAT V2** is a Raspberry Pi expansion board that turns a Pi into a robot controller. It sits on top of the Pi's 40-pin GPIO header and adds:

- An **AT32F413 ARM Cortex-M4 co-processor** (MCU) running at 200 MHz that handles all PWM generation and analog-to-digital conversion
- A **DC motor driver** (2 channels)
- **20 PWM channels** for servos and motors
- **8 ADC channels** for analog sensors
- An **I2S audio speaker** with text-to-speech
- **Bluetooth** for wireless control

Your Raspberry Pi talks to this co-processor over **I2C** (a simple two-wire communication bus). This means the Pi doesn't have to waste CPU cycles generating precise PWM signals — the MCU handles all the real-time hardware work.

### Two-Library Architecture

You interact with the Robot HAT through two Python libraries:

```
Your Python Scripts
        │
        ▼
┌─────────────────────┐
│   picarx (v2.0.5)   │  High-level: "drive forward", "turn left"
│   Picarx class      │
└────────┬────────────┘
         │
         ▼
┌─────────────────────┐
│ robot_hat (v2.3.5)  │  Low-level: "set PWM channel 0 to 1500μs"
│ Servo, Motor, PWM,  │
│ Pin, ADC, I2C, ...  │
└────────┬────────────┘
         │
         ▼
┌─────────────────────┐
│ gpiozero / smbus2 / │  System libraries
│ pygame / pyaudio    │
└────────┬────────────┘
         │
         ▼
┌─────────────────────┐
│ Raspberry Pi +      │  Physical hardware
│ Robot HAT board     │
└─────────────────────┘
```

- **`robot_hat`** is the Hardware Abstraction Layer (HAL). It gives you Python classes for every piece of hardware on the board: GPIO pins, PWM channels, ADC inputs, servos, motors, and sensors. Use this library when you want fine-grained control or are building a custom robot.

- **`picarx`** is the high-level library specifically for the PiCar-X smart car kit. It wraps `robot_hat` classes into simple methods like `forward(speed)`, `get_distance()`, and `set_dir_servo_angle(angle)`. Use this library when you're working with a PiCar-X and want to get moving quickly.

### Prerequisites

- A Raspberry Pi (3B+, 4, 5, or Zero W) with Raspberry Pi OS
- A Robot HAT V2 board assembled and mounted on the Pi
- Python 3.7 or later
- I2C enabled (see Installation)

---

## 2. Hardware Overview

### Physical Layout

The Robot HAT board provides:

| Feature | Details |
|---------|---------|
| **Motor ports** | 2 DC motor outputs (XH2.54 connectors) |
| **Servo headers** | Up to 12 servo pins (P0–P11) on 3-pin headers (Signal/VCC/GND) |
| **ADC inputs** | 8 analog channels (A0–A7) |
| **GPIO pins** | Digital I/O (D0–D16) exposed on pin headers |
| **I2C connectors** | 2.54mm 4-pin header + SH1.0 (QWIIC/STEMMA QT compatible) |
| **SPI header** | 7-pin 2.54mm header |
| **UART header** | 4-pin 2.54mm header |
| **Speaker** | Onboard I2S mono speaker (2030 audio chamber) |
| **User LED** | Programmable LED on GPIO26 |
| **User button** | Button on GPIO25 |
| **Reset button** | Resets the onboard MCU |

### Pin Naming Convention

The Robot HAT uses a simple naming scheme:

- **D0–D16** — Digital GPIO pins. These are general-purpose input/output pins for reading buttons, controlling LEDs, and similar on/off tasks.
- **P0–P19** — PWM output channels. These generate precisely timed electrical pulses for controlling servos and motor speed.
- **A0–A7** — ADC (Analog-to-Digital Converter) input channels. These read continuously varying voltages (like from a light sensor or potentiometer).

### I2C Communication to the MCU

The Pi communicates with the Robot HAT's onboard MCU over **I2C bus 1**:

- **Primary address:** `0x14`
- **Fallback addresses:** `0x15`, `0x16`

The library automatically scans for the MCU at these addresses and uses whichever one responds. All PWM and ADC operations go through I2C. If the MCU gets stuck (which can happen), every I2C operation is wrapped in a **5-retry mechanism** that automatically retries failed communications.

### Board Versions: v4.x vs v5.x

| Feature | v4.x | v5.x |
|---------|------|------|
| Motor driver chip | TC1508S (PWM + GPIO direction) | TC618S (dual PWM) |
| Motor count | 2 | Up to 4 |
| Speaker enable pin | GPIO20 | GPIO12 |
| PWM channels | P0–P13 | P0–P19 |
| Detection | Default (fallback) | UUID in `/proc/device-tree/` |

The library auto-detects which board version you have and selects the correct motor driver mode. You generally don't need to worry about this.

### Power System

| Spec | Detail |
|------|--------|
| Battery | 2x 18650 lithium cells |
| Input voltage | 6.0–8.4V |
| Charging | USB Type-C |
| DC-DC output | 5V / 3A to Raspberry Pi |
| Battery monitoring | ADC channel A4 (voltage divider: reads up to ~9.9V) |
| LED indicators | 2 LEDs: both on (>7.6V), 1 on (7.15–7.6V), both off (<7.15V) |

### PiCar-X Default Wiring

If you're using the PiCar-X kit, here's how everything is connected:

| Component | Pin(s) |
|-----------|--------|
| Camera pan servo | P0 |
| Camera tilt servo | P1 |
| Steering servo | P2 |
| Left motor direction | D4 (GPIO23) |
| Right motor direction | D5 (GPIO24) |
| Left motor PWM | P13 |
| Right motor PWM | P12 |
| Grayscale sensor (left) | A0 |
| Grayscale sensor (middle) | A1 |
| Grayscale sensor (right) | A2 |
| Ultrasonic trigger | D2 (GPIO27) |
| Ultrasonic echo | D3 (GPIO22) |

### Beginner Concepts

**GPIO (General-Purpose Input/Output):** A pin on the Raspberry Pi that you can set to HIGH (3.3V) or LOW (0V) to turn things on and off, or read whether something external (like a button) is HIGH or LOW.

**I2C (Inter-Integrated Circuit):** A communication protocol that uses just two wires (SDA for data, SCL for clock) to let the Pi talk to the MCU. Think of it like a two-lane road where the Pi sends commands and receives data back.

**PWM (Pulse Width Modulation):** A technique for controlling how much power a device gets by rapidly switching a signal on and off. The percentage of time the signal is on (the "duty cycle") determines the effective power. It's like flickering a light switch very fast — the faster and longer you keep it on during each cycle, the brighter the light appears.

**ADC (Analog-to-Digital Converter):** A circuit that converts a continuously varying voltage (analog) into a number (digital) that a computer can understand. The Robot HAT's ADC has 12-bit resolution, meaning it divides the 0–3.3V range into 4096 steps (0–4095).

---

## 3. Installation & First Boot

### Install Robot HAT (install first — PiCar-X depends on it)

```bash
cd robot-hat-2.0
sudo python3 install.py
```

This full install will:
- Install system dependencies via `apt` and `pip`
- Enable I2C and SPI interfaces
- Configure audio output
- Install the `robot_hat` Python package

**Lighter install options:**
```bash
sudo python3 install.py --no-dep     # Skip system dependencies
sudo python3 install.py --only-lib   # Library only, no deps or hardware config
```

### Install PiCar-X

```bash
cd picar-x-2.0
sudo python3 setup.py install
```

### Verify Your Installation

**Step 1: Check I2C communication**

```bash
i2cdetect -y 1
```

You should see address `0x14` (or `0x15`/`0x16`) in the output. This confirms the Pi can see the Robot HAT MCU.

**Step 2: Test the Python import**

```python
from robot_hat import Pin, PWM, ADC, Servo
print("robot_hat imported successfully!")
```

**Step 3: Check battery voltage**

```python
from robot_hat import ADC

adc = ADC("A4")
raw = adc.read_voltage()
battery_voltage = raw * 3  # voltage divider ratio
print(f"Battery: {battery_voltage:.1f}V")
```

A healthy battery reads 7.0–8.4V.

### The MCU Reset Ritual

When you first create hardware objects, you should **reset the MCU** first and wait for it to boot:

```python
from robot_hat.utils import reset_mcu
import time

reset_mcu()
time.sleep(0.2)  # Give the MCU time to reboot
```

**Why?** The MCU can sometimes get stuck in the middle of an I2C data transfer (for example, if a previous script crashed). Resetting it clears its state and ensures clean communication. The `Picarx()` class does this automatically in its constructor, but if you're using `robot_hat` directly, do it yourself at the start of your script.

### Troubleshooting

| Problem | Solution |
|---------|----------|
| `IOError` or `OSError` when accessing PWM/ADC | Reset the MCU: `reset_mcu()` then `time.sleep(0.2)` |
| `i2cdetect` shows no devices | Enable I2C: `sudo raspi-config` → Interface Options → I2C → Enable |
| `ModuleNotFoundError: robot_hat` | Re-run `sudo python3 install.py` in the `robot-hat-2.0` directory |
| Battery reads 0V | Check that batteries are inserted and the power switch is on |

---

## 4. Digital GPIO — Pin Class

The `Pin` class controls digital (on/off) GPIO pins on the Raspberry Pi through the `gpiozero` library.

### Concepts: Digital Signals

Digital signals have only two states: **HIGH** (3.3V on the Pi) and **LOW** (0V/ground). This is perfect for things like LEDs (on or off), buttons (pressed or not pressed), and direction control for motors.

### Output Mode

Use output mode to control external devices like LEDs:

```python
from robot_hat import Pin

# Create a pin in output mode
led = Pin("D0", mode=Pin.OUT)

# Turn it on and off
led.on()        # Set HIGH (3.3V)
led.off()       # Set LOW (0V)
led.value(1)    # Same as on()
led.value(0)    # Same as off()
```

### Input Mode

Use input mode to read the state of external devices like buttons:

```python
from robot_hat import Pin

# Create a pin in input mode with a pull-up resistor
button = Pin("D0", mode=Pin.IN, pull=Pin.PULL_UP)

# Read the current value
state = button.value()  # Returns 0 or 1
print(f"Button state: {state}")
```

**Pull-up and pull-down resistors:** When a button is not pressed, the pin is "floating" — it's not connected to anything, so its voltage is unpredictable. A **pull-up resistor** connects the pin to 3.3V through a high-value resistor, giving it a default HIGH state. When the button is pressed, it connects the pin to ground, pulling it LOW. A **pull-down resistor** does the opposite: default LOW, goes HIGH when pressed.

- `Pin.PULL_UP` — Pin reads HIGH when not connected, LOW when grounded
- `Pin.PULL_DOWN` — Pin reads LOW when not connected, HIGH when powered
- `Pin.PULL_NONE` — No internal pull resistor

### Interrupts

Instead of constantly checking a button's state in a loop ("polling"), you can set up an **interrupt** that automatically calls a function when the pin changes state:

```python
from robot_hat import Pin
import time

def button_pressed(pin):
    print("Button was pressed!")

button = Pin("D0")
button.irq(
    handler=button_pressed,
    trigger=Pin.IRQ_FALLING,    # Trigger when signal goes HIGH→LOW
    bouncetime=200,             # Ignore bounces for 200ms
    pull=Pin.PULL_UP
)

# Keep the program running
while True:
    time.sleep(1)
```

**Trigger options:**
- `Pin.IRQ_FALLING` — Fires when the signal drops from HIGH to LOW
- `Pin.IRQ_RISING` — Fires when the signal rises from LOW to HIGH
- `Pin.IRQ_RISING_FALLING` — Fires on any change

**Debouncing:** Mechanical buttons don't make clean contact — they "bounce" rapidly between on and off for a few milliseconds. The `bouncetime` parameter (in milliseconds) tells the system to ignore these bounces.

### Special Pins

| Pin Name | GPIO | Purpose |
|----------|------|---------|
| `"LED"` | GPIO26 | Onboard programmable LED |
| `"SW"` or `"USER"` | GPIO25 | Onboard user button |
| `"MCURST"` | GPIO5 | MCU reset (used by `reset_mcu()`) |

### Example: Blink the Onboard LED

```python
from robot_hat import Pin
import time

led = Pin("LED", mode=Pin.OUT)

try:
    while True:
        led.on()
        time.sleep(0.5)
        led.off()
        time.sleep(0.5)
except KeyboardInterrupt:
    led.off()
```

### Example: Read the User Button

```python
from robot_hat import Pin
import time

button = Pin("SW", mode=Pin.IN, pull=Pin.PULL_UP)

while True:
    if button.value() == 0:  # Button pressed (pulled LOW)
        print("Button pressed!")
    time.sleep(0.1)
```

---

## 5. Analog Input — ADC Class

The `ADC` class reads analog voltages from the Robot HAT's 8 ADC channels (A0–A7). The actual analog-to-digital conversion happens on the MCU, and values are sent to the Pi over I2C.

### Concepts: Analog vs Digital

While digital signals are either on or off, **analog signals** vary continuously. A light sensor might output 0.5V in dim light and 2.8V in bright light. The ADC converts these continuous voltages into numbers your code can work with.

The Robot HAT uses a **12-bit ADC**, which means:
- It divides the 0–3.3V range into **4096 steps** (2^12 = 4096)
- Each step = 3.3V / 4095 ≈ 0.0008V (0.8mV)
- A reading of 0 means 0V, a reading of 4095 means 3.3V

### Basic Usage

```python
from robot_hat import ADC

# Create an ADC object for channel A0
sensor = ADC("A0")

# Read the raw digital value (0–4095)
raw_value = sensor.read()
print(f"Raw ADC value: {raw_value}")

# Read as voltage (0.0–3.3V)
voltage = sensor.read_voltage()
print(f"Voltage: {voltage:.2f}V")
```

### Battery Voltage Monitoring

Channel **A4** is connected to the battery through a voltage divider (20K/10K resistors), so the ADC reads one-third of the actual battery voltage.

```python
from robot_hat import ADC

battery_adc = ADC("A4")
raw_voltage = battery_adc.read_voltage()
battery_voltage = raw_voltage * 3  # Compensate for voltage divider
print(f"Battery: {battery_voltage:.1f}V")

if battery_voltage < 7.0:
    print("Warning: Battery low! Please charge.")
elif battery_voltage > 7.6:
    print("Battery level: Good")
```

Or use the built-in utility:

```python
from robot_hat.utils import get_battery_voltage

voltage = get_battery_voltage()
print(f"Battery: {voltage:.1f}V")
```

### Important Note: Channel Reversal

Internally, the ADC channels are **reversed** — when you specify `ADC("A0")`, the library actually reads MCU channel 7. This is handled automatically by the library, so you always use the printed label (A0–A7) and the mapping is taken care of.

### Example: Read a Sensor Continuously

```python
from robot_hat import ADC
import time

sensor = ADC("A0")

while True:
    value = sensor.read()
    voltage = sensor.read_voltage()
    print(f"Raw: {value:4d}  Voltage: {voltage:.2f}V")
    time.sleep(0.5)
```

---

## 6. PWM Output

The `PWM` class controls the 20 PWM output channels (P0–P19) on the Robot HAT's MCU. PWM is used for servo control, motor speed control, LED dimming, and buzzer tones.

### Concepts: How PWM Works

Imagine you have a light switch and you flick it on and off very rapidly — say, 1000 times per second. If you keep it on for 50% of each cycle and off for 50%, the light appears to be at half brightness. That's PWM in a nutshell:

- **Frequency** — How many on/off cycles happen per second (measured in Hz). For servos, this is typically 50 Hz (50 cycles per second). For motors, it's often higher.
- **Duty cycle** — The percentage of each cycle that the signal is HIGH. 0% = always off, 50% = half power, 100% = always on.
- **Period** — The total length of one cycle, measured in timer "ticks." The Robot HAT uses a 72 MHz clock, so the period and prescaler together determine the frequency.

**The math:** `frequency = 72,000,000 / prescaler / period`

### Basic Usage

```python
from robot_hat import PWM

# Create a PWM object on channel P0
pwm = PWM("P0")

# Set frequency (Hz)
pwm.freq(1000)

# Set duty cycle as a percentage (0–100)
pwm.pulse_width_percent(50)  # 50% duty cycle

# Or set raw pulse width (0–period)
pwm.pulse_width(2048)
```

### Timer Groups

PWM channels that share the same timer **share the same frequency** but can have different duty cycles:

| Timer | Channels | Typical Use |
|-------|----------|-------------|
| Timer 0 | P0–P3 | Servos (50 Hz) |
| Timer 1 | P4–P7 | Servos (50 Hz) |
| Timer 2 | P8–P11 | Servos (50 Hz) |
| Timer 3 | P12–P13 | Motors |
| Timer 4 | P16–P17 | Extended (v5) |
| Timer 5 | P18 | Extended (v5) |
| Timer 6 | P19 | Extended (v5) |

**Important:** If you set P0 to 50 Hz and then set P1 to 100 Hz, P0 will also change to 100 Hz because they share Timer 0. Plan your channel assignments accordingly.

### Low-Level Control

For advanced use, you can set the prescaler and period directly:

```python
from robot_hat import PWM

pwm = PWM("P0")

# Set prescaler and period manually
pwm.prescaler(10)      # Clock divider
pwm.period(4095)       # Timer counts from 0 to this value

# The resulting frequency is:
# 72,000,000 / 10 / 4095 ≈ 17,582 Hz
```

### Example: Fade an LED

```python
from robot_hat import PWM
import time

led = PWM("P0")
led.freq(1000)

try:
    while True:
        # Fade up
        for brightness in range(0, 101, 2):
            led.pulse_width_percent(brightness)
            time.sleep(0.02)
        # Fade down
        for brightness in range(100, -1, -2):
            led.pulse_width_percent(brightness)
            time.sleep(0.02)
except KeyboardInterrupt:
    led.pulse_width_percent(0)
```

---

## 7. Servo Motors

The `Servo` class provides a high-level interface for controlling servo motors. It builds on top of the `PWM` class, automatically configuring the correct frequency (50 Hz) and converting angles to pulse widths.

### Concepts: How Servos Work

A servo motor contains a DC motor, a **potentiometer** (a variable resistor that measures the shaft's position), and a **control circuit**. When you send it a pulse:

1. The control circuit reads the pulse width to determine the desired position
2. It checks the potentiometer to see where the shaft actually is
3. It drives the motor to move the shaft to the correct position
4. This **feedback loop** runs continuously, so the servo holds its position even under load

The standard protocol uses a **50 Hz signal** (one pulse every 20ms):
- **500 μs** pulse → -90 degrees
- **1500 μs** pulse → 0 degrees (center)
- **2500 μs** pulse → +90 degrees

### Basic Usage

```python
from robot_hat import Servo

servo = Servo("P0")

# Move to a specific angle (-90 to +90)
servo.angle(0)      # Center position
servo.angle(45)     # 45 degrees clockwise
servo.angle(-45)    # 45 degrees counter-clockwise

# Or set pulse width directly (500–2500 μs)
servo.pulse_width_time(1500)  # Center (same as angle(0))
```

The `angle()` method automatically converts angles to pulse widths using this mapping:

```
pulse_width = mapping(angle, -90, 90, 500, 2500)
```

So angle -90 → 500μs, angle 0 → 1500μs, angle 90 → 2500μs.

### Staggering Multiple Servos

When initializing multiple servos, **stagger them** with a short delay (150ms) between each one. This prevents a sudden current spike from multiple servos moving at once, which could brown out the power supply:

```python
from robot_hat import Servo
import time

servos = []
for channel in ["P0", "P1", "P2"]:
    s = Servo(channel)
    s.angle(0)
    servos.append(s)
    time.sleep(0.15)  # 150ms delay between initializations
```

### Example: Sweep a Servo

```python
from robot_hat import Servo
import time

servo = Servo("P0")

try:
    while True:
        # Sweep from -90 to +90
        for angle in range(-90, 91, 5):
            servo.angle(angle)
            time.sleep(0.05)
        # Sweep back
        for angle in range(90, -91, -5):
            servo.angle(angle)
            time.sleep(0.05)
except KeyboardInterrupt:
    servo.angle(0)
```

---

## 8. DC Motors

The `Motor` class controls DC motors through the Robot HAT's motor driver. The driver chip determines how speed and direction are controlled.

### Concepts: H-Bridge Motor Control

An **H-bridge** is a circuit that lets you control both the speed and direction of a DC motor:
- To spin the motor forward, current flows one way through the motor
- To spin it backward, the H-bridge reverses the current direction
- Speed is controlled by PWM — pulsing the power on and off rapidly

The Robot HAT supports two motor driver chips:
- **TC1508S (v4.x boards, Mode 1):** Uses one PWM pin for speed and one GPIO pin for direction
- **TC618S (v5.x boards, Mode 2):** Uses two PWM pins — one controls forward speed, the other controls backward speed

### Basic Motor Usage

The library auto-detects the board version, so you can usually use the same code on either board:

**Mode 1 (v4.x — TC1508S):**
```python
from robot_hat import Motor, PWM, Pin

motor = Motor(PWM("P13"), Pin("D4"))  # PWM + GPIO direction

motor.speed(50)     # Forward at 50% speed
motor.speed(-50)    # Backward at 50% speed
motor.speed(0)      # Stop
```

**Mode 2 (v5.x — TC618S):**
```python
from robot_hat import Motor, PWM

motor = Motor(PWM("P12"), PWM("P13"), mode=2)  # Dual PWM

motor.speed(50)     # Forward at 50% speed
motor.speed(-50)    # Backward at 50% speed
motor.speed(0)      # Stop
```

### Speed Range

Speed is specified as a percentage from **-100 to +100**:
- Positive values = forward
- Negative values = backward
- 0 = stop

### Reversing Motor Direction

If a motor spins the wrong way, you can reverse it in software:

```python
motor.set_is_reverse(True)
```

### Always Use try/finally

**This is critical:** DC motors will keep spinning if your program crashes. Always wrap motor code in `try/finally` to ensure motors stop:

```python
from robot_hat import Motor, PWM, Pin

motor = Motor(PWM("P13"), Pin("D4"))

try:
    motor.speed(50)
    import time
    time.sleep(2)
finally:
    motor.speed(0)  # Always stop the motor!
```

### The Motors Convenience Class

The `Motors` class manages a pair of motors (left and right) with convenience methods:

```python
from robot_hat import Motors

motors = Motors()
motors.set_left_id(1)    # Motor 1 is the left motor
motors.set_right_id(2)   # Motor 2 is the right motor

try:
    motors.forward(50)       # Both motors forward
    motors.backward(50)      # Both motors backward
    motors.turn_left(50)     # Left backward, right forward
    motors.turn_right(50)    # Left forward, right backward
    motors.speed(30, 60)     # Set left and right speeds independently
finally:
    motors.stop()
```

### Example: Motor Control with Direction Reversal

```python
from robot_hat import Motor, PWM, Pin
import time

motor = Motor(PWM("P13"), Pin("D4"))

try:
    print("Forward...")
    motor.speed(60)
    time.sleep(2)

    print("Backward...")
    motor.speed(-60)
    time.sleep(2)

    print("Reversing polarity...")
    motor.set_is_reverse(True)
    motor.speed(60)   # Now "forward" spins the opposite way
    time.sleep(2)
finally:
    motor.speed(0)
    print("Stopped.")
```

---

## 9. Sensor Modules

The `robot_hat` library includes drivers for several common sensor modules.

### Ultrasonic Distance Sensor

An ultrasonic sensor measures distance by sending out a pulse of high-frequency sound and timing how long it takes for the echo to return. Since we know the speed of sound (343.3 m/s), we can calculate the distance.

```python
from robot_hat import Pin, Ultrasonic

sonar = Ultrasonic(
    trig=Pin("D2"),
    echo=Pin("D3", mode=Pin.IN, pull=Pin.PULL_DOWN)
)

distance = sonar.read()  # Returns distance in cm, or -1 if out of range
print(f"Distance: {distance} cm")
```

**How `.read()` works:** It tries up to 10 measurements and returns the first valid one. If all attempts fail (object too far away or no echo detected within the 20ms timeout), it returns `-1`.

**Example: Continuous distance reading**

```python
from robot_hat import Pin, Ultrasonic
import time

sonar = Ultrasonic(Pin("D2"), Pin("D3", mode=Pin.IN, pull=Pin.PULL_DOWN))

while True:
    dist = sonar.read()
    if dist == -1:
        print("Out of range")
    else:
        print(f"Distance: {dist:.1f} cm")
    time.sleep(0.1)
```

### Grayscale Module (Line Follower / Cliff Detector)

The grayscale module has 3 sensors that measure surface reflectance. Dark surfaces (like a black line on white paper) reflect less light and give lower ADC readings; light surfaces give higher readings.

```python
from robot_hat import ADC, Grayscale_Module

# Create 3 ADC channels for the grayscale sensors
gs = Grayscale_Module(ADC("A0"), ADC("A1"), ADC("A2"))

# Read raw values (list of 3 integers, 0–4095)
values = gs.read()
print(f"Left: {values[0]}, Middle: {values[1]}, Right: {values[2]}")

# Set a reference threshold for line detection
gs.reference([1000, 1000, 1000])

# Read status: 0 = above reference (light/background), 1 = below (dark/line)
status = gs.read_status()
print(f"Status: {status}")  # e.g., [0, 1, 0] means middle sensor sees the line
```

**Channel constants:**
- `Grayscale_Module.LEFT` = 0
- `Grayscale_Module.MIDDLE` = 1
- `Grayscale_Module.RIGHT` = 2

**Example: Detecting a line**

```python
from robot_hat import ADC, Grayscale_Module
import time

gs = Grayscale_Module(ADC("A0"), ADC("A1"), ADC("A2"))
gs.reference([1400, 1400, 1400])  # Adjust based on your surface

while True:
    values = gs.read()
    status = gs.read_status()
    print(f"Values: {values} | Status: {status}")

    if status == [0, 1, 0]:
        print("  → Line is centered")
    elif status == [1, 0, 0] or status == [1, 1, 0]:
        print("  → Line is to the left")
    elif status == [0, 0, 1] or status == [0, 1, 1]:
        print("  → Line is to the right")
    elif status == [0, 0, 0]:
        print("  → No line detected (all light)")

    time.sleep(0.2)
```

### ADXL345 Accelerometer

The ADXL345 is a 3-axis accelerometer that measures acceleration in the X, Y, and Z directions. When stationary, it reads approximately 1g on the axis pointing toward the ground (due to gravity).

```python
from robot_hat import ADXL345

accel = ADXL345()

# Read all 3 axes (returns [x, y, z] in g units)
data = accel.read()
print(f"X: {data[0]:.2f}g, Y: {data[1]:.2f}g, Z: {data[2]:.2f}g")

# Read a single axis
x = accel.read(ADXL345.X)
y = accel.read(ADXL345.Y)
z = accel.read(ADXL345.Z)
```

### RGB LED

Controls a 3-pin RGB LED using PWM:

```python
from robot_hat import PWM, RGB_LED

# Connect to 3 PWM channels
rgb = RGB_LED(
    r_pin=PWM("P0"),
    g_pin=PWM("P1"),
    b_pin=PWM("P2"),
    common=RGB_LED.ANODE    # or RGB_LED.CATHODE
)

# Set color using hex string
rgb.color("#FF0000")    # Red
rgb.color("#00FF00")    # Green
rgb.color("#0000FF")    # Blue

# Set color using RGB tuple
rgb.color((255, 128, 0))   # Orange

# Set color using 24-bit integer
rgb.color(0xFF00FF)     # Purple
```

### Buzzer

Controls a passive buzzer (frequency-controllable) or active buzzer (on/off only):

```python
from robot_hat import PWM, Buzzer

# Passive buzzer (PWM — can control frequency)
buzz = Buzzer(PWM("P0"))

# Play a tone at a specific frequency for a duration
buzz.play(440, 0.5)    # A4 note for 0.5 seconds

# Turn on/off manually
buzz.freq(880)          # Set frequency to 880 Hz (A5)
buzz.on()               # Start buzzing
# ... later ...
buzz.off()              # Stop buzzing
```

**Note:** The `play()` method splits the duration in half — half with sound on, half with silence — to create distinct notes.

---

## 10. Audio — Music & TTS

### Music Class

The `Music` class handles audio playback using `pygame.mixer` and tone generation using `pyaudio`:

```python
from robot_hat import Music

music = Music()
```

**Play a sound effect (blocking — waits until finished):**
```python
music.sound_play("/path/to/sound.wav")
music.sound_play("/path/to/sound.wav", volume=80)  # 0–100
```

**Play a sound in the background:**
```python
music.sound_play_threading("/path/to/sound.wav")
```

**Play music (supports loops):**
```python
music.music_play("/path/to/song.mp3")
music.music_play("/path/to/song.mp3", loops=0)    # Loop forever
music.music_play("/path/to/song.mp3", loops=2)    # Play twice
music.music_set_volume(50)                          # Volume 0–100
music.music_pause()
music.music_resume()
music.music_stop()
```

**Generate tones:**
```python
# Play a specific frequency for a duration (seconds)
music.play_tone_for(440, 1.0)   # A4 for 1 second
```

**Note system (MIDI-compatible):**
```python
# Get the frequency of a named note
freq = music.note("C4")    # Middle C → 261.6 Hz
freq = music.note("A4")    # Concert A → 440 Hz
freq = music.note("G#5")   # G-sharp in octave 5

# Set tempo (beats per minute)
music.tempo(120)

# Calculate beat duration in seconds
duration = music.beat(1/4)  # Quarter note at current tempo
```

**Example: Play a simple melody**

```python
from robot_hat import Music
import time

music = Music()
music.tempo(120)

melody = ["C4", "D4", "E4", "F4", "G4", "A4", "B4", "C5"]

for note_name in melody:
    freq = music.note(note_name)
    duration = music.beat(1/4)  # Quarter notes
    music.play_tone_for(freq, duration)
```

### TTS (Text-to-Speech)

The `TTS` class converts text to spoken audio:

```python
from robot_hat import TTS

tts = TTS()  # Default engine: pico2wave

tts.say("Hello, I am a robot!")
tts.say("The distance is 30 centimeters.")
```

**Set language:**
```python
tts.lang("en-US")     # American English (default)
tts.lang("en-GB")     # British English
tts.lang("de-DE")     # German
tts.lang("fr-FR")     # French
tts.lang("es-ES")     # Spanish
tts.lang("it-IT")     # Italian
```

**Alternative TTS engines:**
```python
tts_espeak = TTS(engine=TTS.ESPEAK)       # espeak
tts_espeak_ng = TTS(engine=TTS.ESPEAK_NG) # espeak-ng (more voices)
```

**Espeak parameters (espeak/espeak-ng only):**
```python
tts_espeak.espeak_params(
    amp=100,     # Amplitude (0–200)
    speed=175,   # Words per minute (80–260)
    gap=5,       # Word gap
    pitch=50     # Pitch (0–99)
)
```

### Volume Control

Set the system-wide audio volume:

```python
from robot_hat.utils import set_volume

set_volume(80)  # 0–100
```

**Note:** Audio features require `sudo` to enable the speaker GPIO pin. The `Music` class automatically enables the speaker when initialized.

---

## 11. Configuration & Calibration

### The fileDB Class

The `fileDB` class provides a simple key-value store that persists to a text file. It's used by `robot_hat` and `picarx` to save calibration values.

```python
from robot_hat import fileDB

# Open (or create) a config file
db = fileDB("/path/to/config.conf")

# Set a value
db.set("my_setting", "42")

# Get a value (with optional default)
value = db.get("my_setting", default_value="0")
print(value)  # "42"

# Values are always stored and returned as strings
```

### Config File Locations

| Library | Config Path | Contents |
|---------|-------------|----------|
| `robot_hat` | `~/.config/robot-hat/robot-hat.conf` | Servo offsets for Robot class |
| `picarx` | `/opt/picar-x/picar-x.conf` | Servo offsets, motor direction, sensor references |

### What Gets Stored

The PiCar-X config file (`/opt/picar-x/picar-x.conf`) stores:

| Key | Purpose | Example Value |
|-----|---------|---------------|
| `picarx_dir_servo` | Steering servo offset | `2` |
| `picarx_cam_pan_servo` | Camera pan servo offset | `-1` |
| `picarx_cam_tilt_servo` | Camera tilt servo offset | `0` |
| `picarx_dir_motor` | Motor direction calibration | `[1, 1]` |
| `line_reference` | Grayscale reference for line following | `[1400, 1400, 1400]` |
| `cliff_reference` | Grayscale reference for cliff detection | `[500, 500, 500]` |

### Calibration Workflow

1. **Steering servo:** Place wheels straight, adjust offset until the car drives straight
2. **Camera servos:** Adjust offsets so the camera faces forward at angle 0
3. **Motor direction:** If a motor spins backward, flip its calibration value to `-1`
4. **Grayscale references:** Place the sensor on your specific surface and record the threshold between line and background

See Chapter 13 for the PiCar-X calibration methods.

---

## 12. Robot Class — Multi-Servo Framework

The `Robot` class provides a framework for building multi-servo robots with smooth, coordinated movements. It's used by SunFounder's PiSloth, PiArm, PiCrawler, and other kits.

### Basic Usage

```python
from robot_hat import Robot

# Create a 4-servo robot using PWM channels 0–3
robot = Robot(
    pin_list=[0, 1, 2, 3],     # PWM channel numbers
    name="my_robot",            # Used for config file keys
    init_angles=[0, 0, 0, 0]   # Starting angles for each servo
)
```

During initialization, servos are moved one at a time with a **150ms delay** between each to prevent current spikes.

### Smooth Servo Movement

The `servo_move()` method interpolates smoothly from the current position to a target position:

```python
# Move all servos to target angles
robot.servo_move([45, -30, 0, 60], speed=50)
```

**Speed parameter (0–100):**
- 100 = fastest (about 10ms total)
- 50 = moderate (about 505ms total)
- 0 = slowest (about 1000ms total)

The method calculates 10ms steps and limits maximum speed to **428 degrees/second** (the physical limit of typical servos at 4.8V).

### Preset Actions

You can define and play back named action sequences:

```python
# Define a wave action (list of target angle lists)
robot.move_list["wave"] = [
    [0, 0, 0, 45],     # Step 1
    [0, 0, 0, -45],    # Step 2
    [0, 0, 0, 45],     # Step 3
    [0, 0, 0, 0],      # Step 4: return to center
]

# Play the action
robot.do_action("wave", step=2, speed=60)  # Repeat 2 times at speed 60
```

### Calibration and Offsets

```python
# Set servo offsets (clamped to -20 to +20 degrees)
robot.set_offset([2, -1, 0, 3])

# Move all servos to their calibration position
robot.calibration()

# Reset all servos to zero
robot.reset()
```

Offsets are saved to the config file automatically and loaded on next initialization.

### Example: Four-Servo Robot

```python
from robot_hat import Robot
import time

robot = Robot(
    pin_list=[0, 1, 2, 3],
    name="test_robot",
    init_angles=[0, 0, 0, 0]
)

try:
    # Move each servo individually
    robot.servo_move([45, 0, 0, 0], speed=50)
    time.sleep(0.5)
    robot.servo_move([0, 45, 0, 0], speed=50)
    time.sleep(0.5)
    robot.servo_move([0, 0, 45, 0], speed=50)
    time.sleep(0.5)
    robot.servo_move([0, 0, 0, 45], speed=50)
    time.sleep(0.5)

    # Return to center
    robot.servo_move([0, 0, 0, 0], speed=30)
finally:
    robot.reset()
```

---

## 13. PiCar-X — High-Level Car Control

The `Picarx` class wraps all `robot_hat` hardware into a simple interface for the PiCar-X smart car.

### Initialization

```python
from picarx import Picarx

px = Picarx()
```

This single line:
1. Resets the MCU and waits 200ms
2. Loads calibration from `/opt/picar-x/picar-x.conf`
3. Initializes 3 servos (camera pan P0, camera tilt P1, steering P2)
4. Initializes 2 DC motors (left: D4/P13, right: D5/P12)
5. Initializes the grayscale sensor (A0, A1, A2)
6. Initializes the ultrasonic sensor (D2, D3)

### Driving

```python
px.forward(50)       # Drive forward at speed 50 (0–100)
px.backward(50)      # Drive backward at speed 50
px.stop()            # Stop both motors
```

**How motor indexing works:** The PiCar-X motors face opposite directions:
- Motor 1 (left): positive speed = forward
- Motor 2 (right): negative speed = forward (motor is mounted backward)

The `forward()` and `backward()` methods handle this automatically.

**Set individual motor speed:**
```python
px.set_motor_speed(1, 50)    # Left motor, speed 50
px.set_motor_speed(2, -50)   # Right motor, speed -50 (forward for right side)
```

**Differential drive:** When the steering is turned, the inner wheel automatically slows down to create a smoother turn. The slowdown factor is proportional to the steering angle:

```
power_scale = (100 - abs(steering_angle)) / 100
```

### Steering

```python
px.set_dir_servo_angle(0)     # Straight ahead
px.set_dir_servo_angle(30)    # Turn right (max)
px.set_dir_servo_angle(-30)   # Turn left (max)
```

Steering angle is constrained to **-30 to +30 degrees**.

### Camera Control

```python
# Pan (horizontal): -90 to +90 degrees
px.set_cam_pan_angle(0)       # Center
px.set_cam_pan_angle(45)      # Look right
px.set_cam_pan_angle(-45)     # Look left

# Tilt (vertical): -35 to +65 degrees
px.set_cam_tilt_angle(0)      # Level
px.set_cam_tilt_angle(30)     # Look up
px.set_cam_tilt_angle(-35)    # Look down
```

### Sensors

**Ultrasonic distance:**
```python
distance = px.get_distance()  # Returns cm, or -1 if out of range
```

**Grayscale sensor:**
```python
# Get raw sensor values (list of 3 integers)
data = px.get_grayscale_data()
print(f"Left: {data[0]}, Middle: {data[1]}, Right: {data[2]}")

# Get line status (requires reference to be set)
status = px.get_line_status(data)
# Returns [0, 0, 0] through [1, 1, 1]
# 0 = above reference (light/background), 1 = below (dark/line)

# Get cliff detection
is_cliff = px.get_cliff_status(data)
# Returns True if any sensor reads below cliff_reference (edge detected)
```

### Calibration

```python
# Calibrate steering servo offset
px.dir_servo_calibrate(2)     # Add 2-degree offset

# Calibrate camera servos
px.cam_pan_servo_calibrate(-1)
px.cam_tilt_servo_calibrate(0)

# Calibrate motor direction (1 = normal, -1 = reversed)
px.motor_direction_calibrate(1, 1)   # Left motor normal
px.motor_direction_calibrate(2, -1)  # Right motor reversed

# Set sensor references
px.set_line_reference([1400, 1400, 1400])
px.set_cliff_reference([500, 500, 500])
```

All calibration values are saved to `/opt/picar-x/picar-x.conf` and loaded automatically on next initialization.

### Reset

```python
px.reset()  # Stops motors, centers all servos
```

### Example: Drive and Steer

```python
from picarx import Picarx
import time

px = Picarx()

try:
    # Drive straight
    px.set_dir_servo_angle(0)
    px.forward(50)
    time.sleep(2)

    # Turn right
    px.set_dir_servo_angle(30)
    time.sleep(2)

    # Turn left
    px.set_dir_servo_angle(-30)
    time.sleep(2)

    # Straighten and stop
    px.set_dir_servo_angle(0)
    px.stop()
finally:
    px.stop()
```

### Example: Camera Look-Around

```python
from picarx import Picarx
import time

px = Picarx()

try:
    # Scan left to right
    for angle in range(-90, 91, 10):
        px.set_cam_pan_angle(angle)
        time.sleep(0.1)

    # Return to center
    px.set_cam_pan_angle(0)
    time.sleep(0.5)

    # Tilt up and down
    for angle in range(-35, 66, 10):
        px.set_cam_tilt_angle(angle)
        time.sleep(0.1)

    px.set_cam_tilt_angle(0)
finally:
    px.reset()
```

---

## 14. Autonomous Behaviors

This chapter covers common autonomous behavior patterns: obstacle avoidance, line following, and cliff detection. All of these follow the same fundamental pattern:

```
while True:
    sense   →  Read sensor data
    think   →  Decide what to do
    act     →  Control motors and servos
```

**Always wrap autonomous code in `try/finally` with `px.stop()`** — if the program crashes without stopping the motors, the car will keep driving!

### Obstacle Avoidance

Use the ultrasonic sensor to detect objects ahead and steer around them:

```python
from picarx import Picarx
import time

POWER = 50
SAFE_DISTANCE = 40       # cm — all clear, drive straight
DANGER_DISTANCE = 20     # cm — too close, back up

def main():
    try:
        px = Picarx()

        while True:
            distance = round(px.ultrasonic.read(), 2)
            print(f"Distance: {distance} cm")

            if distance >= SAFE_DISTANCE:
                # All clear — drive straight
                px.set_dir_servo_angle(0)
                px.forward(POWER)
            elif distance >= DANGER_DISTANCE:
                # Getting close — turn right
                px.set_dir_servo_angle(30)
                px.forward(POWER)
                time.sleep(0.1)
            else:
                # Too close — back up and turn left
                px.set_dir_servo_angle(-30)
                px.backward(POWER)
                time.sleep(0.5)

    finally:
        px.forward(0)

if __name__ == "__main__":
    main()
```

### Line Following

Use the grayscale sensor to track a dark line on a light surface:

```python
from picarx import Picarx
from time import sleep

px = Picarx()

# Set reference values — adjust these for your surface!
# The reference should be halfway between the line value and background value.
# px.set_line_reference([1400, 1400, 1400])

px_power = 10           # Low speed for better control
offset = 20             # Steering angle for corrections
last_state = "stop"     # Remember last direction for recovery

def get_status(val_list):
    """Convert grayscale readings to a direction."""
    _state = px.get_line_status(val_list)
    # _state: [left, middle, right]
    # 0 = light (background), 1 = dark (line)
    if _state == [0, 0, 0]:
        return "stop"           # Lost the line
    elif _state[1] == 1:
        return "forward"        # Line is centered
    elif _state[0] == 1:
        return "right"          # Line is to the left → steer right
    elif _state[2] == 1:
        return "left"           # Line is to the right → steer left

def out_handle():
    """Recovery when the line is lost: back up in the last known direction."""
    global last_state
    if last_state == "left":
        px.set_dir_servo_angle(-30)
        px.backward(10)
    elif last_state == "right":
        px.set_dir_servo_angle(30)
        px.backward(10)
    while True:
        gm_val_list = px.get_grayscale_data()
        gm_state = get_status(gm_val_list)
        if gm_state != last_state:
            break
    sleep(0.001)

if __name__ == "__main__":
    try:
        while True:
            gm_val_list = px.get_grayscale_data()
            gm_state = get_status(gm_val_list)
            print(f"Values: {gm_val_list}, State: {gm_state}")

            if gm_state != "stop":
                last_state = gm_state

            if gm_state == "forward":
                px.set_dir_servo_angle(0)
                px.forward(px_power)
            elif gm_state == "left":
                px.set_dir_servo_angle(offset)
                px.forward(px_power)
            elif gm_state == "right":
                px.set_dir_servo_angle(-offset)
                px.forward(px_power)
            else:
                out_handle()    # Lost the line — try to recover
    finally:
        px.stop()
        print("Stopped.")
```

**Key concepts:**
- `last_state` provides **hysteresis** — when the line is lost, the car remembers which direction it was last turning and backs up that way to find the line again.
- Low speed (`px_power = 10`) gives the sensors more time to react.
- The steering `offset` controls how aggressively the car corrects.

### Cliff Detection

Use the grayscale sensor to detect edges (like a table edge). When a sensor reads below the cliff reference, the surface has disappeared:

```python
from picarx import Picarx
import time

px = Picarx()
# px.set_cliff_reference([500, 500, 500])  # Adjust for your surface

try:
    px.forward(30)
    while True:
        data = px.get_grayscale_data()
        is_cliff = px.get_cliff_status(data)

        if is_cliff:
            print(f"Cliff detected! Values: {data}")
            px.backward(30)
            time.sleep(0.5)
            px.set_dir_servo_angle(30)
            px.forward(30)
            time.sleep(1)
            px.set_dir_servo_angle(0)

        time.sleep(0.05)
finally:
    px.stop()
```

**How cliff detection works:** `get_cliff_status()` returns `True` if **any** of the three sensor readings falls at or below its corresponding cliff reference value. Low readings indicate the sensor is seeing air (no surface to reflect light from) rather than a surface.

---

## 15. Utilities & Troubleshooting

### Utility Functions

These functions are available from `robot_hat.utils` (and also imported at the top level of `robot_hat`):

**`reset_mcu()`** — Reset the onboard MCU
```python
from robot_hat.utils import reset_mcu
import time

reset_mcu()
time.sleep(0.2)  # Wait for MCU to reboot
```

**`get_battery_voltage()`** — Read battery voltage
```python
from robot_hat.utils import get_battery_voltage

voltage = get_battery_voltage()
print(f"Battery: {voltage:.1f}V")
```

**`mapping(x, in_min, in_max, out_min, out_max)`** — Map a value from one range to another
```python
from robot_hat.utils import mapping

# Convert an angle to a pulse width
pulse = mapping(45, -90, 90, 500, 2500)  # → 1500
```

**`get_ip(ifaces=['wlan0', 'eth0'])`** — Get the Pi's IP address
```python
from robot_hat.utils import get_ip

ip = get_ip()
print(f"IP address: {ip}")  # e.g., "192.168.1.42" or False
```

**`set_volume(value)`** — Set system audio volume (0–100)
```python
from robot_hat.utils import set_volume

set_volume(80)
```

### Debug Levels

Every `robot_hat` class that inherits from `_Basic_class` supports debug logging. Pass `debug_level` to the constructor to see what's happening at the I2C level:

```python
from robot_hat import PWM

# See all I2C traffic for this PWM channel
pwm = PWM("P0", debug_level='debug')
```

**Debug levels (from most to least verbose):**

| Level | Name | What it shows |
|-------|------|---------------|
| 4 | `'debug'` | Everything including raw I2C reads/writes |
| 3 | `'info'` | Initialization and state changes |
| 2 | `'warning'` | Potential issues (default) |
| 1 | `'error'` | Errors only |
| 0 | `'critical'` | Critical failures only |

### I2C Retry Mechanism

All I2C operations are wrapped in a `@_retry_wrapper` decorator that retries up to **5 times** on `OSError`. This handles transient I2C bus errors that can happen with hardware communication:

```
Attempt 1: OSError → retry
Attempt 2: OSError → retry
Attempt 3: Success → return result

# or after 5 failures:
Attempt 5: OSError → return False
```

### Common Errors and Solutions

| Error | Cause | Solution |
|-------|-------|----------|
| `IOError` / `OSError` on PWM or ADC | MCU stuck in I2C transfer | Call `reset_mcu()` then `time.sleep(0.2)` |
| `ValueError: Pin should be in...` | Wrong pin name | Check pin name: use `"D0"` not `"0"`, `"P0"` not `"PWM0"`, `"A0"` not `"ADC0"` |
| No audio output | Speaker not enabled | Run with `sudo`; or call `enable_speaker()` manually |
| Motors not moving | Motor direction flipped | Call `motor_direction_calibrate(motor, -1)` or check wiring |
| Servo jitters / doesn't hold position | Insufficient power | Check battery charge; don't move too many servos simultaneously |
| `ModuleNotFoundError: No module named 'smbus2'` | Missing dependency | Run `pip3 install smbus2` or re-run `install.py` |
| `i2cdetect` shows no devices | I2C not enabled | Run `sudo raspi-config` → Interface Options → I2C → Enable, then reboot |
| `FileNotFoundError` on config | Config directory missing | The `fileDB` class creates it automatically; ensure you have write permissions |

---

## 16. API Quick Reference

### Pin

```python
Pin(pin, mode=None, pull=None, active_state=None)
```

| Method | Description | Parameters | Returns |
|--------|-------------|------------|---------|
| `value(val)` | Set/get pin value | `val`: `0`, `1`, or `None` to read | `int` (0 or 1) |
| `on()` | Set pin HIGH | — | `1` |
| `off()` | Set pin LOW | — | `0` |
| `high()` | Alias for `on()` | — | `1` |
| `low()` | Alias for `off()` | — | `0` |
| `irq(handler, trigger, bouncetime, pull)` | Set interrupt | `handler`: callback, `trigger`: `IRQ_FALLING`/`IRQ_RISING`/`IRQ_RISING_FALLING`, `bouncetime`: ms, `pull`: `PULL_UP`/`PULL_DOWN`/`PULL_NONE` | — |
| `close()` | Release the GPIO pin | — | — |
| `name()` | Get GPIO name | — | `str` (e.g., `"GPIO17"`) |

**Constants:** `Pin.OUT`, `Pin.IN`, `Pin.PULL_UP`, `Pin.PULL_DOWN`, `Pin.PULL_NONE`, `Pin.IRQ_FALLING`, `Pin.IRQ_RISING`, `Pin.IRQ_RISING_FALLING`

---

### ADC

```python
ADC(chn, address=None)
```

| Method | Description | Parameters | Returns |
|--------|-------------|------------|---------|
| `read()` | Read raw ADC value | — | `int` (0–4095) |
| `read_voltage()` | Read as voltage | — | `float` (0.0–3.3V) |

---

### PWM

```python
PWM(channel, address=None)
```

| Method | Description | Parameters | Returns |
|--------|-------------|------------|---------|
| `freq(freq)` | Set/get frequency | `freq`: Hz or `None` to get | `float` |
| `prescaler(psc)` | Set/get prescaler | `psc`: `int` (0–65535) or `None` | `int` |
| `period(arr)` | Set/get period | `arr`: `int` (0–65535) or `None` | `int` |
| `pulse_width(pw)` | Set/get raw pulse width | `pw`: `int` (0–65535) or `None` | `int` |
| `pulse_width_percent(pct)` | Set/get duty cycle % | `pct`: `float` (0–100) or `None` | `float` |

**Constants:** `PWM.CLOCK = 72000000.0`, `PWM.ADDR = [0x14, 0x15, 0x16]`

---

### Servo

```python
Servo(channel, address=None)
```

| Method | Description | Parameters | Returns |
|--------|-------------|------------|---------|
| `angle(angle)` | Set servo angle | `angle`: `float` (-90 to 90) | — |
| `pulse_width_time(pwt)` | Set pulse width | `pwt`: `float` (500–2500 μs) | — |

**Constants:** `Servo.MAX_PW = 2500`, `Servo.MIN_PW = 500`, `Servo.FREQ = 50`, `Servo.PERIOD = 4095`

---

### Motor

```python
Motor(pwm, dir, is_reversed=False, mode=None, freq=100)
```

| Method | Description | Parameters | Returns |
|--------|-------------|------------|---------|
| `speed(speed)` | Set/get motor speed | `speed`: `float` (-100 to 100) or `None` | `float` or `None` |
| `set_is_reverse(val)` | Reverse motor direction | `val`: `bool` | — |

---

### Motors

```python
Motors(db=config_file)
```

| Method | Description | Parameters | Returns |
|--------|-------------|------------|---------|
| `forward(speed)` | Both motors forward | `speed`: `float` (0–100) | — |
| `backward(speed)` | Both motors backward | `speed`: `float` (0–100) | — |
| `turn_left(speed)` | Pivot left | `speed`: `float` | — |
| `turn_right(speed)` | Pivot right | `speed`: `float` | — |
| `speed(left, right)` | Set both speeds | `left`, `right`: `float` (-100–100) | — |
| `stop()` | Stop all motors | — | — |
| `set_left_id(id)` | Set left motor (1 or 2) | `id`: `int` | — |
| `set_right_id(id)` | Set right motor (1 or 2) | `id`: `int` | — |
| `set_left_reverse()` | Toggle left motor reverse | — | `bool` |
| `set_right_reverse()` | Toggle right motor reverse | — | `bool` |

---

### Ultrasonic

```python
Ultrasonic(trig, echo, timeout=0.02)
```

| Method | Description | Parameters | Returns |
|--------|-------------|------------|---------|
| `read(times)` | Read distance | `times`: retry count (default 10) | `float` (cm) or `-1` |

---

### Grayscale_Module

```python
Grayscale_Module(pin0, pin1, pin2, reference=None)
```

| Method | Description | Parameters | Returns |
|--------|-------------|------------|---------|
| `read(channel)` | Read sensor(s) | `channel`: `int` or `None` for all | `list` or `int` |
| `read_status(datas)` | Get line status | `datas`: `list` or `None` to read | `list` of 0/1 |
| `reference(ref)` | Set/get reference | `ref`: `list` of 3 ints or `None` | `list` |

**Constants:** `Grayscale_Module.LEFT = 0`, `Grayscale_Module.MIDDLE = 1`, `Grayscale_Module.RIGHT = 2`

---

### ADXL345

```python
ADXL345(address=0x53, bus=1)
```

| Method | Description | Parameters | Returns |
|--------|-------------|------------|---------|
| `read(axis)` | Read acceleration | `axis`: `ADXL345.X`/`.Y`/`.Z` or `None` for all | `float` or `list` (in g) |

---

### RGB_LED

```python
RGB_LED(r_pin, g_pin, b_pin, common=RGB_LED.ANODE)
```

| Method | Description | Parameters | Returns |
|--------|-------------|------------|---------|
| `color(color)` | Set LED color | `color`: `str` (`"#FF0000"`), `tuple` (`(255,0,0)`), `list`, or `int` | — |

---

### Buzzer

```python
Buzzer(buzzer)
```

| Method | Description | Parameters | Returns |
|--------|-------------|------------|---------|
| `on()` | Turn on buzzer | — | — |
| `off()` | Turn off buzzer | — | — |
| `freq(freq)` | Set frequency (PWM buzzer only) | `freq`: `float` (Hz) | — |
| `play(freq, duration)` | Play tone | `freq`: `float`, `duration`: `float` (seconds) or `None` | — |

---

### Music

```python
Music()
```

| Method | Description | Parameters | Returns |
|--------|-------------|------------|---------|
| `sound_play(filename, volume)` | Play sound (blocking) | `filename`: `str`, `volume`: `int` (0–100) | — |
| `sound_play_threading(filename, volume)` | Play sound (background) | Same as above | — |
| `music_play(filename, loops, start, volume)` | Play music file | `filename`: `str`, `loops`: `int` (0=forever), `start`: `float` (s), `volume`: `int` | — |
| `music_set_volume(value)` | Set music volume | `value`: `int` (0–100) | — |
| `music_stop()` | Stop music | — | — |
| `music_pause()` | Pause music | — | — |
| `music_resume()` | Resume music | — | — |
| `play_tone_for(freq, duration)` | Play tone | `freq`: `float` (Hz), `duration`: `float` (s) | — |
| `note(note, natural)` | Get note frequency | `note`: `str` (e.g., `"C4"`), `natural`: `bool` | `float` (Hz) |
| `beat(beat)` | Get beat duration | `beat`: `float` (e.g., `1/4`) | `float` (seconds) |
| `tempo(tempo, note_value)` | Set/get tempo | `tempo`: `int` (BPM), `note_value`: `float` | `tuple` |

---

### TTS

```python
TTS(engine=TTS.PICO2WAVE, lang=None)
```

| Method | Description | Parameters | Returns |
|--------|-------------|------------|---------|
| `say(words)` | Speak text | `words`: `str` | — |
| `lang(*value)` | Set/get language | `value`: `str` (e.g., `"en-US"`) or empty to get | `str` |
| `supported_lang()` | Get supported languages | — | `list` |
| `espeak_params(amp, speed, gap, pitch)` | Set espeak params | `amp`: 0–200, `speed`: 80–260, `gap`: int, `pitch`: 0–99 | — |

---

### fileDB

```python
fileDB(db, mode=None, owner=None)
```

| Method | Description | Parameters | Returns |
|--------|-------------|------------|---------|
| `get(name, default_value)` | Get value | `name`: `str`, `default_value`: `str` | `str` |
| `set(name, value)` | Set value | `name`: `str`, `value`: `str` | — |

---

### Robot

```python
Robot(pin_list, db=config_file, name=None, init_angles=None, init_order=None)
```

| Method | Description | Parameters | Returns |
|--------|-------------|------------|---------|
| `servo_move(targets, speed, bpm)` | Move servos smoothly | `targets`: `list`, `speed`: 0–100, `bpm`: `float` | — |
| `do_action(motion_name, step, speed)` | Play preset action | `motion_name`: `str`, `step`: `int`, `speed`: 0–100 | — |
| `set_offset(offset_list)` | Set servo offsets | `offset_list`: `list` (clamped -20 to 20) | — |
| `calibration()` | Move to home position | — | — |
| `reset(list)` | Reset to origin or given list | `list`: `list` or `None` | — |

---

### Picarx

```python
Picarx(servo_pins=['P0','P1','P2'], motor_pins=['D4','D5','P13','P12'],
       grayscale_pins=['A0','A1','A2'], ultrasonic_pins=['D2','D3'],
       config='/opt/picar-x/picar-x.conf')
```

| Method | Description | Parameters | Returns |
|--------|-------------|------------|---------|
| `forward(speed)` | Drive forward | `speed`: `int` (0–100) | — |
| `backward(speed)` | Drive backward | `speed`: `int` (0–100) | — |
| `stop()` | Stop motors | — | — |
| `set_motor_speed(motor, speed)` | Set one motor | `motor`: 1 or 2, `speed`: -100 to 100 | — |
| `set_dir_servo_angle(value)` | Set steering angle | `value`: `int` (-30 to 30) | — |
| `set_cam_pan_angle(value)` | Set camera pan | `value`: `int` (-90 to 90) | — |
| `set_cam_tilt_angle(value)` | Set camera tilt | `value`: `int` (-35 to 65) | — |
| `get_distance()` | Read ultrasonic | — | `float` (cm) or `-1` |
| `get_grayscale_data()` | Read grayscale | — | `list` of 3 ints |
| `get_line_status(gm_val_list)` | Get line status | `gm_val_list`: `list` | `list` of 0/1 |
| `get_cliff_status(gm_val_list)` | Check for cliff | `gm_val_list`: `list` | `bool` |
| `set_line_reference(value)` | Set line ref | `value`: `list` of 3 | — |
| `set_cliff_reference(value)` | Set cliff ref | `value`: `list` of 3 | — |
| `dir_servo_calibrate(value)` | Set steering offset | `value`: `float` | — |
| `cam_pan_servo_calibrate(value)` | Set pan offset | `value`: `float` | — |
| `cam_tilt_servo_calibrate(value)` | Set tilt offset | `value`: `float` | — |
| `motor_direction_calibrate(motor, value)` | Set motor dir | `motor`: 1 or 2, `value`: 1 or -1 | — |
| `reset()` | Stop & center all | — | — |

---

### Utility Functions

```python
from robot_hat.utils import reset_mcu, get_battery_voltage, mapping, get_ip, set_volume
```

| Function | Description | Parameters | Returns |
|----------|-------------|------------|---------|
| `reset_mcu()` | Reset onboard MCU | — | — |
| `get_battery_voltage()` | Read battery voltage | — | `float` (V) |
| `mapping(x, in_min, in_max, out_min, out_max)` | Map value between ranges | all `float/int` | `float` |
| `get_ip(ifaces)` | Get IP address | `ifaces`: `list` of interface names | `str` or `False` |
| `set_volume(value)` | Set audio volume | `value`: `int` (0–100) | — |
| `enable_speaker()` | Enable speaker GPIO | — | — |
| `disable_speaker()` | Disable speaker GPIO | — | — |

---

## 17. Pin Map & Wiring Appendix

### D-Pin to GPIO Mapping

| Board Pin | Raspberry Pi GPIO | Notes |
|-----------|-------------------|-------|
| D0 | GPIO17 | |
| D1 | GPIO4 | |
| D2 | GPIO27 | PiCar-X: ultrasonic trigger |
| D3 | GPIO22 | PiCar-X: ultrasonic echo |
| D4 | GPIO23 | PiCar-X: left motor direction |
| D5 | GPIO24 | PiCar-X: right motor direction |
| D6 | GPIO25 | Shared with SW/USER button |
| D7 | GPIO4 | Shared with D1 |
| D8 | GPIO5 | Shared with MCURST |
| D9 | GPIO6 | |
| D10 | GPIO12 | Shared with BOARD_TYPE |
| D11 | GPIO13 | Shared with BLEINT |
| D12 | GPIO19 | |
| D13 | GPIO16 | Shared with RST |
| D14 | GPIO26 | Shared with LED |
| D15 | GPIO20 | Shared with BLERST |
| D16 | GPIO21 | |

### Special Pin Aliases

| Alias | GPIO | Purpose |
|-------|------|---------|
| LED | GPIO26 | Onboard programmable LED |
| SW / USER | GPIO25 | Onboard user button |
| MCURST | GPIO5 | MCU reset control |
| RST | GPIO16 | Reset pin |
| BLEINT | GPIO13 | Bluetooth interrupt |
| BLERST | GPIO20 | Bluetooth reset |
| BOARD_TYPE | GPIO12 | Board type detection |
| CE | GPIO8 | SPI chip enable |

### PWM Channel to Timer Group

| Timer | Channels | Shared Frequency | Typical Use |
|-------|----------|-------------------|-------------|
| Timer 0 | P0, P1, P2, P3 | Yes | Servos (50 Hz) |
| Timer 1 | P4, P5, P6, P7 | Yes | Servos (50 Hz) |
| Timer 2 | P8, P9, P10, P11 | Yes | Servos (50 Hz) |
| Timer 3 | P12, P13 | Yes | Motors |
| Timer 4 | P16, P17 | Yes | Extended (v5 only) |
| Timer 5 | P18 | — | Extended (v5 only) |
| Timer 6 | P19 | — | Extended (v5 only) |

### ADC Channel Assignments

| User Channel | MCU Channel (internal) | Purpose |
|--------------|------------------------|---------|
| A0 | 7 | PiCar-X: grayscale left |
| A1 | 6 | PiCar-X: grayscale middle |
| A2 | 5 | PiCar-X: grayscale right |
| A3 | 4 | General purpose |
| A4 | 3 | Battery voltage (÷3 divider) |
| A5 | 2 | General purpose |
| A6 | 1 | General purpose |
| A7 | 0 | General purpose |

**Note:** The internal reversal (`chn = 7 - chn`) is handled automatically by the `ADC` class. Always use the printed label (A0–A7).

### PiCar-X Default Wiring

| Component | Pin | Type | Notes |
|-----------|-----|------|-------|
| Camera pan servo | P0 | PWM/Servo | Timer 0, range -90 to +90 |
| Camera tilt servo | P1 | PWM/Servo | Timer 0, range -35 to +65 |
| Steering servo | P2 | PWM/Servo | Timer 0, range -30 to +30 |
| Left motor direction | D4 | GPIO (out) | GPIO23 |
| Right motor direction | D5 | GPIO (out) | GPIO24 |
| Left motor PWM | P13 | PWM | Timer 3 |
| Right motor PWM | P12 | PWM | Timer 3 |
| Grayscale left | A0 | ADC | MCU channel 7 |
| Grayscale middle | A1 | ADC | MCU channel 6 |
| Grayscale right | A2 | ADC | MCU channel 5 |
| Ultrasonic trigger | D2 | GPIO (out) | GPIO27 |
| Ultrasonic echo | D3 | GPIO (in) | GPIO22, pull-down |

### I2C Register Map Summary

| Register Range | Purpose | Format |
|----------------|---------|--------|
| `0x05` | Firmware version | 3 bytes: major.minor.patch |
| `0x10–0x17` | ADC channels (with `\|0x10` prefix) | Write channel, read 2 bytes (MSB, LSB) |
| `0x20–0x33` | PWM pulse width (channels 0–19) | Write: `[reg, MSB, LSB]` |
| `0x40–0x43` | Timer 0–3 prescaler | Write: `[reg, MSB, LSB]` |
| `0x44–0x47` | Timer 0–3 period | Write: `[reg, MSB, LSB]` |
| `0x50–0x52` | Timer 4–6 prescaler (v5) | Write: `[reg, MSB, LSB]` |
| `0x54–0x56` | Timer 4–6 period (v5) | Write: `[reg, MSB, LSB]` |

### Battery Voltage Thresholds

| Voltage | Status | LED Indicators |
|---------|--------|----------------|
| > 8.0V | Fully charged | Both LEDs on |
| 7.6–8.0V | Good | Both LEDs on |
| 7.15–7.6V | Medium | 1 LED on |
| < 7.15V | Low — charge soon | Both LEDs off |
| < 6.5V | Critical — stop using | Both LEDs off |

### Config File Key Names

**PiCar-X** (`/opt/picar-x/picar-x.conf`):

| Key | Type | Default | Description |
|-----|------|---------|-------------|
| `picarx_dir_servo` | float | `0` | Steering servo offset (degrees) |
| `picarx_cam_pan_servo` | float | `0` | Camera pan servo offset (degrees) |
| `picarx_cam_tilt_servo` | float | `0` | Camera tilt servo offset (degrees) |
| `picarx_dir_motor` | list | `[1, 1]` | Motor direction calibration [left, right] |
| `line_reference` | list | `[1000, 1000, 1000]` | Grayscale threshold for line following |
| `cliff_reference` | list | `[500, 500, 500]` | Grayscale threshold for cliff detection |

**Robot HAT** (`~/.config/robot-hat/robot-hat.conf`):

| Key | Type | Default | Description |
|-----|------|---------|-------------|
| `{name}_servo_offset_list` | list | `[0, 0, ...]` | Servo offset values for Robot class |
