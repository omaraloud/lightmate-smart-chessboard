# LightMate: Smart Chessboard

LightMate is a smart, connected chessboard that combines the tactile experience of physical chess with real-time digital analysis and feedback.

## Overview

This system detects piece movement using Hall-effect sensors and provides visual feedback through addressable RGB LEDs. A Raspberry Pi processes the board state, validates moves, and enables future online gameplay integration.

## Features

- Real-time piece detection using Hall sensors  
- LED highlighting of legal moves  
- Raspberry Pi-based move validation (Python)  
- Expandable to online gameplay (Lichess API)  
- Touchscreen interface support  

---

## System Architecture

- Hall sensors connected to MCP23017 expanders (I2C)  
- Raspberry Pi processes board state  
- LEDs controlled via SPI through a level shifter  
- Touchscreen provides user interface  

---

## Hardware

- 64 × Hall-effect sensors (DRV5033)  
- 81 × SK9822 RGB LEDs  
- MCP23017 I/O expanders  
- SN74HCT125 level shifter  
- Raspberry Pi 4  
- Custom PCB  

---

## Software

The system runs a continuous loop:

1. Read sensor states  
2. Detect piece lift and placement  
3. Validate moves using `python-chess`  
4. Update LEDs for visual feedback  

---

## Demo

![Board](images/full_board.jpg)
![LED Highlighting](images/led_highlighting.jpg)

---

## Challenges

- High current draw from LEDs  
- Signal integrity across long SPI LED chains  
- Magnetic interference between pieces  
- Debugging power issues on the 3.3V rail  

---

## Engineering Constraints

- Power: LED current draw up to ~2–3A  
- Size: Components must fit under each square  
- Timing: Real-time response required (<30 ms)  
- Budget: Approximately $200–250  
- Manufacturing: Dense PCB routing and soldering complexity  

---

## Future Work

- Finalize stable PCB revision  
- Complete enclosure design and integration  
- Implement full Lichess online gameplay  
- Improve graphical user interface  
- Optimize LED performance and power usage  

---

## Documentation

- Final Report: docs/LightMate_Final_Report.pdf  

---

## Contributors

- Omar AlOud – Hardware Design, PCB, System Integration  
- Anas AlDarwashi – Software, Raspberry Pi Integration  
- James Bridges – PCB Layout, Hardware Integration  

---

## Acknowledgments

Special thanks to Dr. Brickley and Dr. Martin for their guidance and support.
