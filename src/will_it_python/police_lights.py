#!/usr/bin/env python3
"""
Police Lights Simulator
Simulates two over-cab police lights alternating in the terminal.
"""

import sys
import time
import argparse


# ANSI color codes
RED_BG = "\033[41m"
BLUE_BG = "\033[44m"
RESET = "\033[0m"
CLEAR_LINE = "\033[K"
HIDE_CURSOR = "\033[?25l"
SHOW_CURSOR = "\033[?25h"


def draw_light(color: str, is_on: bool) -> str:
    """Draw a single light (on or off)."""
    if is_on:
        bg = color
        # Create a filled light
        light = f"{bg}          {RESET}"
    else:
        # Dimmed/off light
        light = "   ....   "
    
    return light


def draw_lights(left_on: bool, right_on: bool, mode: str = "emergency") -> str:
    """Draw both police lights."""
    left = draw_light(RED_BG, left_on)
    right = draw_light(BLUE_BG, right_on)
    
    # Create the display with spacing
    spacing = "     "
    top_bracket = "╔══════════╗" + spacing + "╔══════════╗"
    light_line = f"║{left}║{spacing}║{right}║"
    bottom_bracket = "╚══════════╝" + spacing + "╚══════════╝"
    label_line = "    RED    " + spacing + "   BLUE    "
    mode_label = f"  Mode: {mode.upper()}  "
    
    return f"\n{top_bracket}\n{light_line}\n{bottom_bracket}\n{label_line}\n{mode_label}\n"


def clear_previous_frame():
    """Clear the previous frame by moving cursor up and clearing lines."""
    # Move cursor up 6 lines and clear them (added mode label)
    for _ in range(6):
        sys.stdout.write("\033[A" + CLEAR_LINE)
    sys.stdout.flush()


def get_pattern(mode: str, frame: int) -> tuple[bool, bool]:
    """Get the light states for a given mode and frame number.
    
    Returns:
        Tuple of (left_on, right_on)
    """
    match mode:
        case "emergency":
            # Fast alternating - standard emergency response
            return (frame % 2 == 0, frame % 2 == 1)
        case "traffic-stop":
            # Slower, steady alternating - routine traffic stop
            return (frame % 2 == 0, frame % 2 == 1)
        case "pursuit":
            # Both lights flash together rapidly
            return (True, True) if frame % 2 == 0 else (False, False)
        case "code-3":
            # Rapid alternating with double-flash pattern
            # Pattern: L, R, L, R, LL, RR
            cycle = frame % 6
            match cycle:
                case 4:
                    return (True, False)  # LL
                case 0 | 1 | 2 | 3:
                    return (cycle % 2 == 0, cycle % 2 == 1)  # L, R, L, R
                case _:
                    return (False, True)  # RR
        case "cruise":
            # Slow, calm alternating - just cruising
            return (frame % 2 == 0, frame % 2 == 1)
        case _:
            # Default to emergency
            return (frame % 2 == 0, frame % 2 == 1)


def get_mode_speed(mode: str) -> float:
    """Get the default speed for a given mode."""
    speeds = {
        "emergency": 0.35,
        "traffic-stop": 0.6,
        "pursuit": 0.2,
        "code-3": 0.25,
        "cruise": 0.8,
    }
    return speeds.get(mode, 0.5)


def simulate_lights(duration: float = 10.0, speed: float | None = None, mode: str = "emergency") -> None:
    """
    Simulate alternating police lights.
    
    Args:
        duration: Total duration to run the simulation (seconds)
        speed: Time between alternations (seconds), None for mode default
        mode: Light pattern mode
    """
    # Use mode default speed if not specified
    if speed is None:
        speed = get_mode_speed(mode)
    
    print(HIDE_CURSOR, end="")
    
    try:
        start_time = time.time()
        frame = 0
        first_frame = True
        
        while time.time() - start_time < duration:
            # Clear previous frame (except for first frame)
            if not first_frame:
                clear_previous_frame()
            else:
                first_frame = False
            
            # Get light states based on mode and frame
            left_on, right_on = get_pattern(mode, frame)
            
            # Draw the current state
            display = draw_lights(left_on, right_on, mode)
            sys.stdout.write(display)
            sys.stdout.flush()
            
            # Wait and increment frame
            time.sleep(speed)
            frame += 1
            
    except KeyboardInterrupt:
        pass
    finally:
        print(SHOW_CURSOR)
        print("\nSimulation stopped.")


def main() -> int:
    """Main entry point for the police lights simulator."""
    modes = ["emergency", "traffic-stop", "pursuit", "code-3", "cruise"]
    
    parser = argparse.ArgumentParser(
        description="Simulate two over-cab police lights in the terminal",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""Modes:
  emergency     - Fast alternating (default)
  traffic-stop  - Slower, steady alternating for routine stops
  pursuit       - Both lights flash together rapidly
  code-3        - Rapid alternating with double-flash pattern
  cruise        - Slow, calm alternating while on patrol
"""
    )
    parser.add_argument(
        "-m", "--mode",
        type=str,
        choices=modes,
        default="emergency",
        help="Light pattern mode (default: emergency)"
    )
    parser.add_argument(
        "-d", "--duration",
        type=float,
        default=10.0,
        help="Duration to run the simulation in seconds (default: 10.0)"
    )
    parser.add_argument(
        "-s", "--speed",
        type=float,
        default=None,
        help="Time between light changes in seconds (default: mode-specific)"
    )
    
    args = parser.parse_args()
    
    # Validate arguments
    if args.duration <= 0:
        print("Error: duration must be positive", file=sys.stderr)
        return 1
    
    if args.speed is not None and args.speed <= 0:
        print("Error: speed must be positive", file=sys.stderr)
        return 1
    
    simulate_lights(duration=args.duration, speed=args.speed, mode=args.mode)
    return 0


def emgy() -> int:
    """Entry point for emergency mode."""
    sys.argv = [sys.argv[0], "-m", "emergency"] + sys.argv[1:]
    return main()


def code3() -> int:
    """Entry point for code-3 mode."""
    sys.argv = [sys.argv[0], "-m", "code-3"] + sys.argv[1:]
    return main()


def pursuit() -> int:
    """Entry point for pursuit mode."""
    sys.argv = [sys.argv[0], "-m", "pursuit"] + sys.argv[1:]
    return main()


def traffic_stop() -> int:
    """Entry point for traffic-stop mode."""
    sys.argv = [sys.argv[0], "-m", "traffic-stop"] + sys.argv[1:]
    return main()


def cruise() -> int:
    """Entry point for cruise mode."""
    sys.argv = [sys.argv[0], "-m", "cruise"] + sys.argv[1:]
    return main()


if __name__ == "__main__":
    sys.exit(main())
