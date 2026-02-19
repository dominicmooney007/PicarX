# Robot Hat V2 Spec Sheet

## What Is It?

The Robot HAT is a multifunctional Raspberry Pi expansion board that turns a Pi into a robot controller. It sits on top of the Pi's GPIO header and adds an **onboard MCU**, **motor driver**, **Bluetooth**, **I2S audio with speaker**, and expanded I/O — all communicating over I2C.

It's the foundation board for SunFounder's PiCar-X, PiDog, PiSloth, PiArm, and PiCrawler kits.

---

## Onboard MCU

| Spec | Detail |
|------|--------|
| Chip | **Artery AT32F413CBT7** |
| Core | ARM Cortex-M4 |
| Clock | 200 MHz |
| Flash | 128 KB |
| SRAM | 32 KB |
| I2C Address | **0x14** (primary), 0x15, 0x16 (fallback) |
| Firmware version | Readable from register `0x05` (3 bytes: major.minor.patch) |

The MCU handles all PWM generation and ADC sampling, offloading this from the Pi. The Pi communicates with it entirely over **I2C bus 1** with a 5-retry error recovery mechanism.

---

## I/O Capabilities

### PWM Outputs (20 channels: P0–P19)
- **72 MHz** clock source on the MCU
- 4 timer groups (channels sharing a timer share frequency):
  - Timer 0: P0–P3
  - Timer 1: P4–P7
  - Timer 2: P8–P11
  - Timer 3: P12–P13 (motor channels)
- 16-bit pulse width resolution (0–65535)
- Configurable prescaler and period per timer
- **Typical use**: P0–P11 for servos (50 Hz), P12–P13 for motors

### ADC Inputs (8 channels: A0–A7)
- **12-bit** resolution (0–4095)
- Voltage range: **0–3.3V**
- A4 is dedicated to **battery voltage** measurement (with 20K/10K voltage divider → reads up to ~9.9V)
- Note: internally reversed mapping (A0 = MCU channel 7)

### Digital GPIO (D0–D16)
- Exposed via **gpiozero** library
- Support for INPUT, OUTPUT, PULL_UP, PULL_DOWN
- **Interrupt support**: rising edge, falling edge, both edges
- Key mappings:

| Pin | RPi GPIO | Pin | RPi GPIO |
|-----|----------|-----|----------|
| D0 | GPIO17 | D4 | GPIO23 (Motor 1 dir) |
| D1 | GPIO4 | D5 | GPIO24 (Motor 2 dir) |
| D2 | GPIO27 | D6 | GPIO25 |
| D3 | GPIO22 | D9 | GPIO6 |

Special pins: LED (GPIO26), USR/SW (GPIO25), RST (GPIO16), MCURST (GPIO5)

---

## Motor Driver

| Feature | Detail |
|---------|--------|
| Channels | **2 DC motor ports** (XH2.54 connectors) |
| Motor 1 | PWM: P13, Direction: D4 (GPIO23) |
| Motor 2 | PWM: P12, Direction: D5 (GPIO24) |
| Speed range | -100 to +100 (signed percentage) |
| Driver modes | **Mode 1** (TC1508S): PWM + GPIO direction — used on **v4.x** boards |
| | **Mode 2** (TC618S): Dual PWM — used on **v5.x** boards (supports 4 motors) |

The board auto-detects v4 vs v5 hardware via the device tree UUID and selects the correct mode.

---

## Servo Control

- Up to **12 servos** on P0–P11 (v4), or **16+** on v5
- Frequency: **50 Hz**
- Pulse width: **500–2500 μs**
- Angle range: **-90° to +90°**
- Max servo speed: **428 degrees/second**
- Initialization staggers servos by 150ms to manage current draw
- Calibration offsets are stored persistently via `fileDB`

---

## Communication Interfaces

| Interface | Pins | Details |
|-----------|------|---------|
| **I2C** | GPIO2 (SDA), GPIO3 (SCL) | 2 connectors: 2.54mm 4-pin + SH1.0 (QWIIC/STEMMA QT compatible), 10K pull-ups |
| **SPI** | GPIO8 (CS), GPIO9 (MISO), GPIO10 (MOSI), GPIO11 (SCLK) | 7-pin 2.54mm header, includes GPIO6 (BSY) |
| **UART** | GPIO14 (TX), GPIO15 (RX) | 4-pin 2.54mm header |

---

## Audio System

| Feature | Detail |
|---------|--------|
| Output | **I2S** mono speaker (2030 audio chamber) |
| I2S pins | GPIO18 (BCLK), GPIO19 (LRCLK), GPIO21 (SDATA) |
| Speaker enable | GPIO20 (v4) / GPIO12 (v5) |
| Sample rate | 44100 Hz, 16-bit signed PCM, mono |
| Capabilities | Tone generation (sine waves), music playback, sound effects |
| **TTS engines** | pico2wave (default, 6 languages), espeak, espeak-ng |
| Languages | en-US, en-GB, de-DE, es-ES, fr-FR, it-IT |

---

## Power System

| Spec | Detail |
|------|--------|
| Input voltage | **6.0–8.4V** (XH2.54 3-pin) |
| Battery | 2x 18650 lithium cells (included with kits) |
| Charging | USB Type-C |
| DC-DC output | 5V/3A to Raspberry Pi |
| Battery monitoring | ADC channel A4 with 20K/10K voltage divider |
| LED indicators | 2 battery LEDs: >7.6V = both on, 7.15–7.6V = 1 on, <7.15V = off |

---

## Additional Onboard Modules

- **Bluetooth module** for wireless control (used with SunFounder Ezblock app)
- **User LED** (GPIO26) — programmable
- **User button** (GPIO25) — customizable with interrupt callbacks
- **Reset button** — resets the MCU

---

## Supported Sensor Modules (via library)

The `robot_hat` library includes drivers for:
- **Ultrasonic** distance sensor (speed of sound: 343.3 m/s, 20ms timeout)
- **ADXL345** 3-axis accelerometer (I2C address 0x53, 2g range)
- **Grayscale_Module** — 3-channel line follower/cliff detector
- **RGB_LED** — 3-pin PWM-controlled LED (common anode or cathode)
- **Buzzer** — PWM or digital buzzer

---

## MCU I2C Register Map

| Register | Purpose |
|----------|---------|
| `0x05` | Firmware version (3 bytes) |
| `0x13` | Battery ADC (A4) |
| `0x14–0x17` | ADC channels 0–3 |
| `0x20–0x2B` | PWM pulse width, channels 0–11 |
| `0x2C` | Motor 2 speed |
| `0x2D` | Motor 1 speed |
| `0x40–0x43` | Timer 0–3 prescaler |
| `0x44–0x47` | Timer 0–3 period |
| `0x50–0x57` | Extended timer prescaler/period (v5) |

Protocol: Write `[register, MSB, LSB]`, read 2 bytes back as `(MSB << 8) | LSB`.

---

## v4 vs v5 Differences

| Feature | v4.x | v5.x |
|---------|------|------|
| Motor driver | TC1508S (PWM+GPIO) | TC618S (dual PWM) |
| Motor count | 2 | Up to 4 |
| Speaker GPIO | GPIO20 | GPIO12 |
| Detection | Default/fallback | UUID in device tree |
| Extended PWM | P0–P13 | P0–P19 |

---

## Compatibility

- Raspberry Pi 5, 4, 3B+, 3B, Zero W, Zero
- Python 3.7+
- Dependencies: smbus2, gpiozero, pyaudio, pygame (>=2.1.2), spidev, pyserial, pillow

---

## Sources

- [SunFounder Robot HAT Product Page](https://www.sunfounder.com/products/sunfounder-robot-hat-expansion-board-designed-for-raspberry-pi)
- [SunFounder Robot HAT Documentation (v2.0)](https://docs.sunfounder.com/projects/robot-hat/en/latest/)
- [SunFounder Robot HAT Series Documentation](https://docs.sunfounder.com/projects/robot-hat-v4/en/latest/)
- [Robot HAT v2.0 PDF](https://docs.sunfounder.com/_/downloads/robot-hat/en/v2.0/pdf/)
- [PiCar-X Robot HAT Hardware Reference](https://docs.sunfounder.com/projects/picar-x-v20/en/latest/hardware/cpn_robot_hat.html)
- [Amazon Product Listing](https://www.amazon.com/SunFounder-Expansion-Raspberry-Inclulded-Rechargeable/dp/B0CKTD7QJB)
- [Peppe8o Robot HAT Tutorial](https://peppe8o.com/raspberry-pi-robot-hat-sunfounder/)
- [GitHub: sunfounder/robot-hat](https://github.com/sunfounder/robot-hat)
