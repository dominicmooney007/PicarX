# AT32F413 MCU Reference — Robot HAT Co-Processor

## Overview

The MCU on the Robot HAT is an **Artery AT32F413CBT7**, made by Artery Technology (a Chinese semiconductor company). It's essentially a **faster, cheaper clone of the STM32F103** (the famous "Blue Pill" chip), pin-compatible with STM32F103C8T6 but significantly more powerful.

On the Robot HAT, it acts as a **peripheral co-processor** — a slave I2C device that the Raspberry Pi sends commands to. It handles PWM generation and ADC sampling. You don't program it directly; it runs SunFounder's firmware.

---

## Full AT32F413 Specs

| Spec | Detail |
|------|--------|
| Core | ARM Cortex-M4 with **FPU** + **DSP** |
| Clock | **200 MHz** max |
| Flash | 64–256 KB (Robot HAT uses 128 KB variant) |
| SRAM | Up to 64 KB (Robot HAT variant: 32 KB) |
| ADC | 2x 12-bit SAR ADCs, up to **16 channels**, 0.5 μs conversion |
| Timers | 2x 32-bit + 5x 16-bit general purpose + 2x 16-bit motor control PWM (advanced) + 2x watchdogs |
| DMA | 14 channels |
| CAN | **2x CAN 2.0B** |
| USB | USB 2.0 full-speed device (crystal-less) |
| SPI | 2x SPI (36 Mbit/s), with I2S multiplexing |
| I2C | 2x I2C (SMBus/PMBus compatible) |
| UART | 3x USART + 2x UART (with IrDA, LIN, ISO7816) |
| SDIO | 1x SDIO (4-bit mode) |
| GPIO | Up to 55 fast I/O, almost all **5V-tolerant** |
| External Flash | Up to 16 MB SPI Flash extension with encryption |
| Supply | 2.6–3.6V |
| Temp range | -40°C to +105°C |
| Package | LQFP48 (7x7mm) on Robot HAT |

---

## Comparison: AT32F413 vs ESP32-S3 vs RP2350 (Pico 2)

| Feature | **AT32F413** (Robot HAT) | **ESP32-S3** | **RP2350** (Pico 2) |
|---------|--------------------------|--------------|----------------------|
| **Core** | ARM Cortex-M4 | Dual Xtensa LX7 | Dual Cortex-M33 *or* RISC-V |
| **Cores** | **1** | **2** | **2** |
| **Clock** | **200 MHz** | **240 MHz** | **150 MHz** |
| **Flash** | 128 KB (on-chip) | Up to 16 MB (external) | 4 MB (external on Pico 2) |
| **SRAM** | 32 KB | 512 KB | 520 KB |
| **FPU** | Single-precision | Single-precision | Single-precision |
| **ADC** | 2x 12-bit, 16 ch | 2x 12-bit, 20 ch | 12-bit, 4–8 ch |
| **WiFi** | No | **802.11 b/g/n** | No |
| **Bluetooth** | No (separate module on HAT) | **BLE 5** | No |
| **USB** | USB 2.0 FS device | USB OTG | USB 1.1 host/device |
| **CAN bus** | **2x CAN 2.0B** | Via TWAI (1x) | No (PIO possible) |
| **DMA** | 14 channels | Yes | 12 channels |
| **PIO** | No | No | **3 blocks, 12 state machines** |
| **Timers** | 9 (incl. 2x 32-bit) | 4 general purpose | 2 (+ PIO) |
| **SPI** | 2x (36 Mbit/s) | 4x | 2x |
| **I2C** | 2x | 2x | 2x |
| **UART** | 5 (3 USART + 2 UART) | 3x | 2x |
| **GPIO** | Up to 55 (5V tolerant) | 45 | 30–48 |
| **Security** | Flash encryption | Flash encryption | **TrustZone, signed boot, OTP** |
| **Power modes** | Sleep/Deep/Standby | Ultra-low-power (ULP core) | Dormant/Sleep |
| **Price** | ~$1–2 | ~$3–4 | ~$1 (chip) / $5 (Pico 2) |
| **Pin compatible** | **STM32F103** drop-in | Espressif ecosystem | RP2040 footprint |

---

## Key Differences & Takeaways

### 1. It's a peripheral co-processor, not the main CPU
On the Robot HAT, the AT32F413 acts as a slave I2C device. The Raspberry Pi sends commands to it, and it handles PWM generation and ADC sampling. You don't program it directly — it runs SunFounder's firmware. The ESP32 and Pico 2 are typically the *main* processor you program yourself.

### 2. It's an STM32 clone
The AT32F413 is pin-compatible with the STM32F103 (the ubiquitous "Blue Pill"). It uses the same ARM Cortex-M4 ecosystem, same toolchain (Keil, GCC ARM, STM32CubeIDE with modifications). Artery provides migration guides from STM32.

### 3. No wireless
Unlike ESP32 (WiFi + BLE built in), the AT32F413 has no wireless capability. The Robot HAT adds Bluetooth via a separate module.

### 4. Strong on motor/industrial control
With 2x CAN bus, 2x advanced motor PWM timers, and 200 MHz clock, the AT32F413 excels at real-time motor control — which is exactly why SunFounder chose it for a robotics board.

### 5. Tiny memory footprint
At 32 KB SRAM and 128 KB Flash, it has far less memory than an ESP32 (512 KB SRAM) or Pico 2 (520 KB SRAM). But for its dedicated role generating PWM signals and reading ADC values, it's more than sufficient.

---

## Role on the Robot HAT

The AT32F413 is a dedicated real-time I/O engine. The Pi communicates with it over **I2C bus 1** at address **0x14** (fallbacks: 0x15, 0x16). The protocol uses a 5-retry error recovery mechanism.

### I2C Register Map

| Register | Purpose |
|----------|---------|
| `0x05` | Firmware version (3 bytes: major.minor.patch) |
| `0x13` | Battery ADC (A4) |
| `0x14–0x17` | ADC channels 0–3 |
| `0x20–0x2B` | PWM pulse width, channels 0–11 |
| `0x2C` | Motor 2 speed |
| `0x2D` | Motor 1 speed |
| `0x40–0x43` | Timer 0–3 prescaler |
| `0x44–0x47` | Timer 0–3 period |
| `0x50–0x57` | Extended timer prescaler/period (v5) |

**Protocol:** Write `[register, MSB, LSB]`, read 2 bytes back as `(MSB << 8) | LSB`.

---

## Sources

- [Artery AT32F413 Product Page](https://www.arterychip.com/en/product/AT32F413.jsp)
- [AT32F413 Datasheet (PDF)](https://www.arterychip.com/download/DS/DS_AT32F413_V2.02_EN.pdf)
- [AT32F413 Reference Manual](https://www.manualslib.com/manual/2884293/Artery-At32f413-Series.html)
- [STM32F103 to AT32F413 Migration Guide](https://www.arterychip.com/download/MG/MG0003_Migrating_from_SXX32F103_to_AT32F413_EN_V2.0.1.pdf)
- [ESP32-S3 Product Page](https://www.espressif.com/en/products/socs/esp32-s3)
- [RP2350 Wikipedia](https://en.wikipedia.org/wiki/RP2350)
- [RP2350 Technical Comparison (SparkFun)](https://news.sparkfun.com/11692)
- [Pico 2 Overview (Jeff Geerling)](https://www.jeffgeerling.com/blog/2024/raspberry-pi-pico-2-rp2350-adds-more-pio-risc-v-cores/)
