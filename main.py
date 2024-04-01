import tkinter as tk
from tkinter import ttk, scrolledtext, StringVar, filedialog
import serial
import threading
from serial.tools import list_ports
from ttkthemes import ThemedTk, ThemedStyle

class SerialCommunicationApp:
    def __init__(self, master):
        self.master = master
        self.is_running = True
        self.refresh_interval = 5000
        self.theme_choice = StringVar(value="radiance")
        self.night_mode = StringVar(value=False)

        # Set the theme
        self.set_theme()

        self.master.title("CH340 Communication App")
        self.master.resizable(width=True, height=True)

        self.serial_port = None
        self.baud_rate_var = StringVar()
        self.com_port_var = StringVar()
        self.connection_status_var = StringVar()
        self.baud_rate_values = ["9600", "19200", "38400", "57600", "115200"]
        self.baud_rate_var.set(self.baud_rate_values[0])

        self.create_widgets()
        self.populate_com_ports()

        self.receive_data()
        self.start_auto_refresh()

    def set_theme(self):
        selected_theme = self.theme_choice.get()

        # Check if the selected theme is supported
        style = ThemedStyle(self.master)
        available_themes = style.theme_names()
        if selected_theme not in available_themes:
            print(f"Warning: Theme '{selected_theme}' not available. Using default theme.")
            selected_theme = "default"

        style.set_theme(selected_theme)
    def populate_com_ports(self):
        ports = [port.device for port in list_ports.comports()]
        self.com_ports_values = ports
        self.com_port_var.set("")  # Clear the current COM port selection
        self.com_port_dropdown["values"] = self.com_ports_values

    def create_widgets(self):
        self.input_entry = ttk.Entry(self.master, width=40)
        self.input_entry.grid(row=0, column=0, padx=10, pady=10)

        com_port_label = ttk.Label(self.master, text="COM Port:")
        com_port_label.grid(row=0, column=1, padx=10, pady=10)
        self.com_port_dropdown = ttk.Combobox(self.master, textvariable=self.com_port_var)
        self.com_port_dropdown.grid(row=0, column=2, padx=10, pady=10)

        baud_rate_label = ttk.Label(self.master, text="Baud Rate:")
        baud_rate_label.grid(row=0, column=3, padx=10, pady=10)
        self.baud_rate_dropdown = ttk.Combobox(self.master, textvariable=self.baud_rate_var, values=self.baud_rate_values)
        self.baud_rate_dropdown.grid(row=0, column=4, padx=10, pady=10)

        self.connect_button = ttk.Button(self.master, text="Connect", command=self.toggle_connection)
        self.connect_button.grid(row=0, column=5, padx=10, pady=10)

        self.connection_status_label = ttk.Label(self.master, textvariable=self.connection_status_var, anchor=tk.W)
        self.connection_status_label.grid(row=1, column=0, columnspan=6, sticky=tk.W, padx=10)
        self.connection_status_label.grid(row=1, column=0, columnspan=6, sticky=tk.W)

        self.send_button = ttk.Button(self.master, text="Send", command=self.send_data, state=tk.DISABLED)
        self.send_button.grid(row=2, column=0, padx=10, pady=10)

        self.console = scrolledtext.ScrolledText(self.master, wrap=tk.WORD, width=60, height=20)
        self.console.grid(row=3, column=0, columnspan=6, padx=10, pady=10)

        self.clear_button = ttk.Button(self.master, text="Clear Console", command=self.clear_console)
        self.clear_button.grid(row=4, column=0, padx=10, pady=10)

        self.save_button = ttk.Button(self.master, text="Save to File", command=self.save_to_file)
        self.save_button.grid(row=4, column=1, padx=10, pady=10)

        self.refresh_button = ttk.Button(self.master, text="Refresh", command=self.populate_com_ports)
        self.refresh_button.grid(row=4, column=2, padx=10, pady=10)

        self.settings_button = ttk.Button(self.master, text="Settings", command=self.open_settings)
        self.settings_button.grid(row=4, column=3, padx=10, pady=10)

    def configure_serial(self):
        try:
            baud_rate = int(self.baud_rate_var.get())
            com_port = self.com_port_var.get()
            if com_port:
                print(f"Connecting to {com_port} at {baud_rate} bps")
                self.serial_port = serial.Serial(com_port, baud_rate, timeout=0)  # Set timeout to 0 for non-blocking reads
                print("Serial port configured successfully")
                self.update_connection_status(f"Connected to {com_port}")
                self.send_button["state"] = tk.NORMAL
                self.connect_button["text"] = "Disconnect"
            else:
                print("Error: Please select a COM port")
                self.update_connection_status("Error: Please select a COM port")
                self.is_running = False
                self.send_button["state"] = tk.DISABLED
                self.connect_button["text"] = "Connect"
        except ValueError as ve:
            print(f"Error: Invalid Baud Rate - {ve}")
            self.update_connection_status("Error: Invalid Baud Rate")
        except serial.SerialException as e:
            print(f"Error: {e}")
            self.update_connection_status(f"Error: {e}")
            self.is_running = False
            self.send_button["state"] = tk.DISABLED
            self.connect_button["text"] = "Connect"

    def close_serial(self):
        if self.serial_port and self.serial_port.is_open:
            self.serial_port.close()
            self.update_connection_status("Disconnected")
            self.send_button["state"] = tk.DISABLED
            self.connect_button["text"] = "Connect"

    def send_data(self):
        data_to_send = self.input_entry.get().strip()
        if data_to_send:
            if self.serial_port and self.serial_port.is_open:
                print(f"Sending command: {data_to_send}")
                self.serial_port.write(data_to_send.encode())
                self.console.insert(tk.END, f"Sent: {data_to_send}\n")
                self.input_entry.delete(0, tk.END)
            else:
                print("Error: Serial port not open")
                self.console.insert(tk.END, "Error: Serial port not open\n")
        else:
            print("Error: Please enter valid data")
            self.console.insert(tk.END, "Error: Please enter valid data\n")

    def receive_data(self):
        threading.Thread(target=self._receive_data_thread).start()

    def _receive_data_thread(self):
        try:
            while self.is_running:
                if self.serial_port and self.serial_port.is_open:
                    received_data = self.serial_port.readline().decode()
                    if received_data:
                        print(f"Received: {received_data}")
                        self.console.insert(tk.END, f"Received: {received_data}\n")
                        self.console.see(tk.END)
                else:
                    self.is_running = False
        except UnicodeDecodeError:
            print("Error: Unable to decode received data")
            self.console.insert(tk.END, "Error: Unable to decode received data\n")

    def toggle_connection(self):
        if self.serial_port and self.serial_port.is_open:
            self.close_serial()
        else:
            self.configure_serial()

    def clear_console(self):
        self.console.delete(1.0, tk.END)

    def save_to_file(self):
        file_path = filedialog.asksaveasfilename(defaultextension=".txt", filetypes=[("Text files", "*.txt")])
        if file_path:
            with open(file_path, "w") as file:
                file.write(self.console.get(1.0, tk.END))

    def update_connection_status(self, status):
        self.connection_status_var.set(status)

    def start_auto_refresh(self):
        self.master.after(self.refresh_interval, self.auto_refresh)

    def auto_refresh(self):
        self.populate_com_ports()
        self.master.after(self.refresh_interval, self.auto_refresh)

    def open_settings(self):
        settings_window = tk.Toplevel(self.master)
        settings_window.title("Settings")
        settings_window.resizable(width=False, height=False)

        ttk.Label(settings_window, text="Theme:").grid(row=0, column=0, padx=10, pady=10)
        theme_dropdown = ttk.Combobox(settings_window, textvariable=self.theme_choice, values=["aqua", "radiance", "scidblue", "elegance"])
        theme_dropdown.grid(row=0, column=1, padx=10, pady=10)

        ttk.Label(settings_window, text="Night Mode:").grid(row=1, column=0, padx=10, pady=10)
        night_mode_checkbox = ttk.Checkbutton(settings_window, text="Enable", variable=self.night_mode, command=self.toggle_night_mode)
        night_mode_checkbox.grid(row=1, column=1, padx=10, pady=10)

        ttk.Button(settings_window, text="Apply", command=self.apply_settings).grid(row=2, column=0, columnspan=2, pady=10)

    def apply_settings(self):
        self.set_theme()
        self.master.update()

    def toggle_night_mode(self):
        if self.night_mode.get():
            self.master.configure(bg="#2E2E2E")
        else:
            self.master.configure(bg="SystemButtonFace")

if __name__ == "__main__":
    root = ThemedTk(theme="radiance")
    app = SerialCommunicationApp(root)
    root.protocol("WM_DELETE_WINDOW", app.close_serial)
    root.mainloop()