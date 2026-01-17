#!/usr/bin/env python3
"""
GenSlave Hardware Test Script

Tests Automation Hat Mini relay and LCD display.
Run with: /opt/genslave/venv/bin/python test_hardware.py
"""

import sys
import time


def test_relay():
    """Test the relay by cycling it on and off."""
    print("\n=== Relay Test ===")
    print("Listen for clicking sounds from the relay.\n")

    try:
        import automationhat

        print("Turning relay OFF (initial state)...")
        automationhat.relay.one.off()
        time.sleep(0.5)

        print("Turning relay ON...")
        automationhat.relay.one.on()
        time.sleep(1)

        print("Turning relay OFF...")
        automationhat.relay.one.off()
        time.sleep(0.5)

        print("\nCycling 3 times rapidly...")
        for i in range(3):
            print(f"  Cycle {i+1}: ON")
            automationhat.relay.one.on()
            time.sleep(0.3)
            print(f"  Cycle {i+1}: OFF")
            automationhat.relay.one.off()
            time.sleep(0.3)

        print("\n[OK] Relay test complete!")
        print("If you heard clicks, the relay is working correctly.")
        return True

    except ImportError as e:
        print(f"[ERROR] automationhat module not found: {e}")
        print("Install with: pip install automationhat")
        return False
    except Exception as e:
        print(f"[ERROR] Relay test failed: {e}")
        return False


def test_lcd():
    """Test the LCD display."""
    print("\n=== LCD Display Test ===")
    print("Watch the LCD screen on the Automation Hat Mini.\n")

    try:
        from PIL import Image, ImageDraw, ImageFont
        from ST7735 import ST7735

        print("Initializing display...")
        display = ST7735(
            port=0,
            cs=1,
            dc=9,
            backlight=13,
            rotation=270,
            spi_speed_hz=10000000
        )

        display.set_backlight(1)

        # Test 1: Red screen
        print("Showing RED screen...")
        image = Image.new('RGB', (160, 80), (255, 0, 0))
        display.display(image)
        time.sleep(1)

        # Test 2: Green screen
        print("Showing GREEN screen...")
        image = Image.new('RGB', (160, 80), (0, 255, 0))
        display.display(image)
        time.sleep(1)

        # Test 3: Blue screen
        print("Showing BLUE screen...")
        image = Image.new('RGB', (160, 80), (0, 0, 255))
        display.display(image)
        time.sleep(1)

        # Test 4: Text display
        print("Showing text...")
        image = Image.new('RGB', (160, 80), (17, 24, 39))
        draw = ImageDraw.Draw(image)

        # Try to use a nice font, fall back to default
        try:
            font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 14)
        except:
            font = ImageFont.load_default()

        draw.text((80, 20), "GenSlave", fill=(34, 197, 94), font=font, anchor="mm")
        draw.text((80, 45), "Hardware Test", fill=(255, 255, 255), font=font, anchor="mm")
        draw.text((80, 65), "OK!", fill=(100, 100, 100), anchor="mm")

        display.display(image)

        print("\n[OK] LCD test complete!")
        print("You should see 'GenSlave Hardware Test OK!' on the display.")
        return True

    except ImportError as e:
        print(f"[ERROR] Required module not found: {e}")
        print("Install with: pip install Pillow ST7735")
        return False
    except Exception as e:
        print(f"[ERROR] LCD test failed: {e}")
        return False


def show_menu():
    """Show the test menu."""
    print("\n" + "=" * 50)
    print("       GenSlave Hardware Test Menu")
    print("=" * 50)
    print("\n  1. Test Relay only")
    print("  2. Test LCD Display only")
    print("  3. Test Both")
    print("  4. Exit")
    print()


def main():
    print("\nGenSlave Hardware Test Script")
    print("Automation Hat Mini - Relay and LCD Display")

    while True:
        show_menu()

        try:
            choice = input("Select option (1-4): ").strip()
        except (KeyboardInterrupt, EOFError):
            print("\n\nExiting...")
            sys.exit(0)

        if choice == "1":
            test_relay()
        elif choice == "2":
            test_lcd()
        elif choice == "3":
            relay_ok = test_relay()
            lcd_ok = test_lcd()
            print("\n" + "=" * 50)
            print("Summary:")
            print(f"  Relay: {'PASS' if relay_ok else 'FAIL'}")
            print(f"  LCD:   {'PASS' if lcd_ok else 'FAIL'}")
            print("=" * 50)
        elif choice == "4":
            print("\nExiting...")
            sys.exit(0)
        else:
            print("\nInvalid option. Please enter 1, 2, 3, or 4.")


if __name__ == "__main__":
    main()
