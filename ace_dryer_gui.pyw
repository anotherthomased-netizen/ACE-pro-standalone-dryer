"""
ACE Pro Dryer - simple point-and-click control window.

Double-click ace_dryer_gui.pyw (or run this with pythonw) to open a small
window with fields for COM port / temperature / duration, and buttons for
Start, Stop, and Status - no command line typing needed.

Requires: pip install pyserial   (one-time, from Command Prompt)
"""

import json
import struct
import sys
import threading
import time
import tkinter as tk
from tkinter import ttk, messagebox

import serial
import serial.tools.list_ports

HEADER = bytes([0xFF, 0xAA])
FOOTER = bytes([0xFE])


def calc_crc(buffer: bytes) -> int:
    crc = 0xFFFF
    for byte in buffer:
        data = byte
        data ^= crc & 0xFF
        data ^= (data & 0x0F) << 4
        crc = ((data << 8) | (crc >> 8)) ^ (data >> 4) ^ (data << 3)
        crc &= 0xFFFF
    return crc


def build_request(method, params, request_id):
    payload_dict = {"id": request_id, "method": method}
    if params is not None:
        payload_dict["params"] = params
    payload = json.dumps(payload_dict).encode("utf-8")

    frame = HEADER
    frame += struct.pack("<H", len(payload))
    frame += payload
    frame += struct.pack("<H", calc_crc(payload))
    frame += FOOTER
    return frame


def read_response(ser, timeout_s=6.0):
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
    return json.loads(payload.decode("utf-8"))


def send_and_wait(ser, method, params=None, request_id=1):
    ser.write(build_request(method, params, request_id))
    return read_response(ser)


class AceDryerApp:
    def __init__(self, root):
        self.root = root
        root.title("ACE Pro Dryer Control")
        root.geometry("420x420")
        root.resizable(False, False)

        pad = {"padx": 10, "pady": 6}

        # --- Port selector ---
        ttk.Label(root, text="COM Port:").grid(row=0, column=0, sticky="w", **pad)
        self.port_var = tk.StringVar()
        self.port_combo = ttk.Combobox(root, textvariable=self.port_var, width=15)
        self.port_combo.grid(row=0, column=1, sticky="w", **pad)
        ttk.Button(root, text="Refresh", command=self.refresh_ports).grid(row=0, column=2, **pad)

        # --- Temp / duration ---
        ttk.Label(root, text="Temperature (\u00b0C):").grid(row=1, column=0, sticky="w", **pad)
        self.temp_var = tk.StringVar(value="55")
        ttk.Entry(root, textvariable=self.temp_var, width=10).grid(row=1, column=1, sticky="w", **pad)

        ttk.Label(root, text="Duration (minutes):").grid(row=2, column=0, sticky="w", **pad)
        self.duration_var = tk.StringVar(value="240")
        ttk.Entry(root, textvariable=self.duration_var, width=10).grid(row=2, column=1, sticky="w", **pad)

        # --- Buttons ---
        btn_frame = ttk.Frame(root)
        btn_frame.grid(row=3, column=0, columnspan=3, pady=10)
        ttk.Button(btn_frame, text="Start Drying", command=self.start_drying).grid(row=0, column=0, padx=5)
        ttk.Button(btn_frame, text="Stop", command=self.stop_drying).grid(row=0, column=1, padx=5)
        ttk.Button(btn_frame, text="Check Status", command=self.check_status).grid(row=0, column=2, padx=5)

        # --- Output box ---
        ttk.Label(root, text="Output:").grid(row=4, column=0, sticky="w", padx=10)
        self.output = tk.Text(root, height=15, width=48, wrap="word")
        self.output.grid(row=5, column=0, columnspan=3, padx=10, pady=5)

        self.refresh_ports()

    def log(self, text):
        self.output.insert("end", text + "\n")
        self.output.see("end")

    def refresh_ports(self):
        ports = [p.device for p in serial.tools.list_ports.comports()]
        self.port_combo["values"] = ports
        if ports and not self.port_var.get():
            self.port_var.set(ports[0])
        self.log(f"Found ports: {ports if ports else 'none'}")

    def _run_in_thread(self, target):
        threading.Thread(target=target, daemon=True).start()

    def _do_request(self, method, params=None, success_msg="Done"):
        port = self.port_var.get().strip()
        if not port:
            messagebox.showerror("No port", "Please select a COM port first.")
            return
        try:
            ser = serial.Serial(port=port, baudrate=115200, timeout=0)
        except serial.SerialException as e:
            self.log(f"Could not open {port}: {e}")
            return
        try:
            response = send_and_wait(ser, method, params)
            self.log(json.dumps(response, indent=2))
            if response.get("code", 0) != 0:
                self.log(f"Error from ACE Pro: {response.get('msg')}")
            else:
                self.log(success_msg)
        except TimeoutError as e:
            self.log(f"Timed out waiting for a reply: {e}")
        except Exception as e:
            self.log(f"Error: {e}")
        finally:
            ser.close()

    MAX_TEMP = 55  # matches the default safety limit used by the original Klipper driver

    def start_drying(self):
        try:
            temp = int(self.temp_var.get())
            duration = int(self.duration_var.get())
        except ValueError:
            messagebox.showerror("Invalid input", "Temperature and duration must be numbers.")
            return
        if temp <= 0 or temp > self.MAX_TEMP:
            messagebox.showerror(
                "Temperature too high",
                f"{temp}\u00b0C is outside the safe range (1-{self.MAX_TEMP}\u00b0C)."
            )
            return
        self.log(f"Starting dryer: {temp}\u00b0C for {duration} minutes...")
        self._run_in_thread(lambda: self._do_request(
            "drying",
            {"temp": temp, "fan_speed": 7000, "duration": duration},
            success_msg="Drying started."
        ))

    def stop_drying(self):
        self.log("Sending stop command...")
        self._run_in_thread(lambda: self._do_request("drying_stop", success_msg="Stop command sent."))

    def check_status(self):
        self.log("Checking status...")
        self._run_in_thread(lambda: self._do_request("get_status", success_msg="Status retrieved."))


if __name__ == "__main__":
    root = tk.Tk()
    app = AceDryerApp(root)
    root.mainloop()
