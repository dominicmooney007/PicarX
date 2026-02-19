# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This repository contains two SunFounder robotics libraries for Raspberry Pi:

- **picar-x-2.0** (v2.0.5): High-level PiCar-X smart car control (steering, motors, camera, sensors)
- **robot-hat-2.0** (v2.3.5): Hardware abstraction layer (HAL) for the Robot HAT expansion board (GPIO, PWM, I2C, ADC, servos, motors, audio)

Target platform: Raspberry Pi with Robot HAT board. Requires Python 3.7+.

## Installation

Both packages require `sudo` and are installed on a Raspberry Pi:

```bash
# Robot HAT (install first — picar-x depends on it)
cd robot-hat-2.0
sudo python3 install.py              # Full install with apt/pip dependencies + I2C/SPI setup
sudo python3 install.py --no-dep     # Skip system dependencies
sudo python3 install.py --only-lib   # Library only, no deps or hardware config

# PiCar-X
cd picar-x-2.0
sudo python3 setup.py install
```

Robot HAT uses `pyproject.toml` (setuptools ≥61.0). PiCar-X uses traditional `setup.py`.

## Tests

Tests are in `robot-hat-2.0/tests/` and are manual hardware test scripts (not pytest). They must be run on a Raspberry Pi with hardware connected:

```bash
python3 robot-hat-2.0/tests/servo_test.py
python3 robot-hat-2.0/tests/motor_test.py
```

## Architecture

### Layer Diagram

```
Example Scripts (picar-x-2.0/example/)
        ↓
Picarx class (picar-x-2.0/picarx/picarx.py)
        ↓
robot_hat package (robot-hat-2.0/robot_hat/)
   Servo, Motor, PWM, ADC, Pin, I2C, Music, TTS, Robot, Ultrasonic, etc.
        ↓
Hardware: gpiozero (GPIO), smbus2 (I2C), pygame (audio)
        ↓
Raspberry Pi + Robot HAT board
```

### robot_hat Key Classes

- **`_Basic_class`** (`basic.py`): Base class providing logging at 5 levels
- **`I2C`** (`i2c.py`): I2C bus wrapper with 5-retry decorator (`@_retry_wrapper`); MCU addresses 0x14/0x15/0x16
- **`PWM`** (`pwm.py`): PWM output via I2C to onboard MCU (channels P0-P19, 72MHz clock)
- **`Pin`** (`pin.py`): GPIO abstraction via gpiozero (D0-D16)
- **`ADC`** (`adc.py`): Analog-to-digital via I2C (channels A0-A7, note: internally reversed — A0=channel 7)
- **`Servo`** (`servo.py`): Servo control (angle -90 to +90, pulse 500-2500μs, 50Hz)
- **`Motor`** (`motor.py`): DC motor with two chip modes (TC1508S: PWM+GPIO direction, TC618S: dual PWM)
- **`Robot`** (`robot.py`): Multi-servo robot framework with calibration/offset persistence
- **`fileDB`** (`filedb.py`): Simple INI-style file database for calibration values
- **`device.py`**: Auto-detects Robot HAT v4.x vs v5.x via `/proc/device-tree/`

### Picarx Class

Single class in `picar-x-2.0/picarx/picarx.py` that wires together:
- 3 servos: camera pan (P0), camera tilt (P1), steering (P2)
- 2 DC motors: left (D4/P13), right (D5/P12)
- Grayscale sensor: 3 ADC channels (A0-A2) for line following / cliff detection
- Ultrasonic sensor: distance measurement (D2/D3)
- Calibration loaded from `/opt/picar-x/picar-x.conf` via fileDB

Motor index convention: 1 = left, 2 = right. Speed range: -100 to 100. Steering angle: -30 to +30 degrees.

### Config/Calibration

- Robot HAT: `~/.config/robot-hat/robot-hat.conf`
- PiCar-X: `/opt/picar-x/picar-x.conf`
- Stored as key-value pairs via `fileDB`; includes servo offsets, motor direction calibration, line/cliff reference values

## Conventions

- Most classes inherit from `_Basic_class` for logging
- I2C operations use `@_retry_wrapper` (5 retries) for hardware robustness
- Pin naming: `D0-D16` (GPIO), `A0-A7` (ADC), `P0-P19` (PWM)
- Servo pulse width: min 500μs, max 2500μs at 50Hz
- Motor PWM: prescaler 10, period 4095
