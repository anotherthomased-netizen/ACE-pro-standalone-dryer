"""
ACE Pro standalone dryer control script.

Talks directly to the ACE Pro over the USB-serial connection you wired up,
using the same request framing and command names as the community Klipper
driver (BunnyAce), but without needing Klipper installed at all.

Setup (Windows):
    1. pip install pyserial
    2. Open Device Manager, find the COM port for your ACE Pro
       (e.g. "COM5") and put it below in PORT, or pass it with --port.
    3. Run: python ace_dryer_control.py --port COM5 --temp 55 --duration 240
       (add --stop to send a stop command instead)

If it can't open the port or times out waiting for a reply, that points
back to the USB wiring/enumeration, not this script.
"""

import argparse
import json
import struct
import sys
import time

import serial

HEADER = bytes([0xFF, 0xAA])
FOOTER = bytes([0xFE])


def calc_crc(buffer: bytes) -> int:
    """Same checksum used by the ACE Pro's firmware (from the BunnyAce driver)."""
    crc = 0xFFFF
    for byte in buffer:
        data = byte
        data ^= crc & 0xFF
        data ^= (data & 0x0F) << 4
        crc = ((data << 8) | (crc >> 8)) ^ (data >> 4) ^ (data << 3)
        crc &= 0xFFFF
    return crc


def build_request(method: str, params: dict | None, request_id: int) -> bytes:
    payload_dict = {"id": request_id, "method": method}
    if params is not None:
        payload_dict["params"] = params
    payload = json.dumps(payload_dict).encode("utf-8")

    frame = HEADER
    frame += struct.pack("<H", len(payload))  # length, little-endian
    frame += payload
    frame += struct.pack("<H", calc_crc(payload))  # CRC of payload only
    frame += FOOTER
    return frame


def read_response(ser: serial.Serial, timeout_s: float = 5.0):
    """Reads bytes until it finds a full frame ending in 0xFE, then parses it."""
    deadline = time.time() + timeout_s
    buffer = bytearray()

    while time.time() < deadline:
        chunk = ser.read(4096)
        if chunk:
            buffer += chunk
            if 0xFE in buffer:
                break
        else:
            time.sleep(0.05)

    if 0xFE not in buffer:
        raise TimeoutError("No response received before timeout")

    if buffer[0:2] != HEADER:
        raise ValueError(f"Bad header in response: {buffer[0:6]!r}")

    payload_len = struct.unpack("<H", buffer[2:4])[0]
    payload = buffer[4:4 + payload_len]
    crc_received = buffer[4 + payload_len: 4 + payload_len + 2]
    crc_expected = struct.pack("<H", calc_crc(payload))

    if crc_received != crc_expected:
        print("Warning: CRC mismatch on response, data may be corrupt", file=sys.stderr)

    return json.loads(payload.decode("utf-8"))


def send_and_wait(ser: serial.Serial, method: str, params: dict | None = None, request_id: int = 1):
    request = build_request(method, params, request_id)
    ser.write(request)
    return read_response(ser)


def main():
    parser = argparse.ArgumentParser(description="Control an ACE Pro's dryer over USB serial")
    parser.add_argument("--port", required=True, help="COM port, e.g. COM5 (check Device Manager)")
    parser.add_argument("--baud", type=int, default=115200)
    parser.add_argument("--temp", type=int, help="Target temperature in Celsius")
    parser.add_argument("--duration", type=int, default=240, help="Duration in minutes (default 240)")
    parser.add_argument("--stop", action="store_true", help="Send stop-drying instead of start")
    parser.add_argument("--status", action="store_true", help="Just query status and exit")
    args = parser.parse_args()

    try:
        ser = serial.Serial(port=args.port, baudrate=args.baud, timeout=0)
    except serial.SerialException as e:
        print(f"Could not open {args.port}: {e}", file=sys.stderr)
        sys.exit(1)

    try:
        if args.status:
            print("Querying status...")
            response = send_and_wait(ser, "get_status")
            print(json.dumps(response, indent=2))
            return

        if args.stop:
            print("Sending stop-drying command...")
            response = send_and_wait(ser, "drying_stop")
            print(json.dumps(response, indent=2))
            return

        if args.temp is None:
            parser.error("--temp is required unless using --stop or --status")

        max_temp = 55  # matches the default safety limit used by the original Klipper driver
        if args.temp <= 0 or args.temp > max_temp:
            print(f"Refusing: {args.temp}C is outside the safe range (1-{max_temp}C).", file=sys.stderr)
            print("If you're sure you need a higher limit, edit max_temp in this script deliberately.", file=sys.stderr)
            sys.exit(1)

        print(f"Starting dryer: {args.temp}C for {args.duration} minutes...")
        response = send_and_wait(
            ser,
            "drying",
            {"temp": args.temp, "fan_speed": 7000, "duration": args.duration},
        )
        print(json.dumps(response, indent=2))

        if response.get("code", 0) != 0:
            print(f"ACE Pro reported an error: {response.get('msg')}", file=sys.stderr)
            sys.exit(1)
        else:
            print("Drying started successfully.")

    except TimeoutError as e:
        print(f"Timed out waiting for a reply: {e}", file=sys.stderr)
        print("This usually means the USB connection isn't enumerating/communicating correctly.", file=sys.stderr)
        sys.exit(1)
    finally:
        ser.close()


if __name__ == "__main__":
    main()
