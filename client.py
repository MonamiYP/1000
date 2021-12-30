# Import required modules
import socket
import sys
import threading
import tkinter as tk
from tkinter import scrolledtext
from tkinter import messagebox

# Specify colours and fonts
DARK_GREY = "#121212"
MEDIUM_GREY = "#1F1824"
BLUE = "#2E4DA7"
LIGHT_BLUE = "#A2BAF5"
WHITE = "white"
FONT = ("Helvetica", 17)
SMALL_FONT = ("Helvetica", 13)
BUTTON_FONT = ("Helvetica", 15)

# Creating a socket object
client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
# Server and port numbers
SERVER = '127.0.0.1'
PORT = 5050


# Functions for GUI
def update_messages(message):
    message_box.config(state=tk.NORMAL)
    message_box.insert(tk.END, message + '\n')
    message_box.config(state=tk.DISABLED)


def connect():
    # Connect to the server
    try:
        client.connect((SERVER, PORT))
        update_messages("[SERVER] Successfully connected to server")
    except:
        messagebox.showerror("ERROR", "Unable to connect to server")

    # Send username to server
    username = username_textbox.get()
    if username != '':
        client.sendall(username.encode('utf-8'))
        # Start a thread where user is going to listen for messages from the server
        thread = threading.Thread(target=listen_for_messages, args=(client,))
        thread.start()

        # Disable username textbox and button
        username_textbox.config(state=tk.DISABLED)
        username_button.config(state=tk.DISABLED)
    else:
        messagebox.showerror("ERROR", "Username cannot be empty")
        exit(0)


def send_message():
    message = message_textbox.get()
    if message != '':
        client.sendall(message.encode('utf-8'))
        message_textbox.delete(0, len(message))
    else:
        messagebox.showerror("ERROR", "Empty message")


window = tk.Tk()  # Create window
window.geometry('600x600')
window.title('1000')
window.resizable(False, False)

# Create grid
window.grid_rowconfigure(0, weight=1)
window.grid_rowconfigure(1, weight=4)
window.grid_rowconfigure(2, weight=1)

# Sections (frames) within windows
top_frame = tk.Frame(window, width=600, height=100, bg=DARK_GREY)
top_frame.grid(row=0, column=0, sticky=tk.NSEW)
middle_frame = tk.Frame(window, width=600, height=400, bg=MEDIUM_GREY)
middle_frame.grid(row=1, column=0, sticky=tk.NSEW)
bottom_frame = tk.Frame(window, width=600, height=100, bg=DARK_GREY)
bottom_frame.grid(row=2, column=0, sticky=tk.NSEW)

# Widgets
username_label = tk.Label(top_frame, text="Enter username:", font=FONT, bg=DARK_GREY, fg=WHITE)
username_label.pack(side=tk.LEFT, padx=10)
username_textbox = tk.Entry(top_frame, font=FONT, bg=BLUE, fg=WHITE, width=23)
username_textbox.pack(side=tk.LEFT)
username_button = tk.Button(top_frame, text="Join", font=BUTTON_FONT, fg=DARK_GREY, command=connect)
username_button.pack(side=tk.LEFT, padx=8)

message_textbox = tk.Entry(bottom_frame, font=FONT, bg=MEDIUM_GREY, fg=WHITE, width=30)
message_textbox.pack(side=tk.LEFT, padx=10)
message_button = tk.Button(bottom_frame, text="Send", font=BUTTON_FONT, fg=DARK_GREY, command=send_message)
message_button.pack(side=tk.LEFT)

message_box = scrolledtext.ScrolledText(middle_frame, font=SMALL_FONT, bg=MEDIUM_GREY, fg=WHITE, width=74, height=32)
message_box.pack(fill=tk.X)
message_box.config(state=tk.DISABLED)


# Listen for messages from server
def listen_for_messages(client):
    while True:
        message = client.recv(1024).decode('utf-8')
        if message != '':
            username = message.split("~")[0]
            content = message.split("~")[1]

            update_messages(f"[{username}] {content}")
        else:
            pass


def on_closing():
    try:
        message = "!DISCONNECT"
        client.sendall(message.encode('utf-8'))
        print("Disconnecting from server")
    except:
        print("Was not connected to server")
    window.destroy()


def main():
    window.protocol("WM_DELETE_WINDOW", on_closing)
    window.mainloop()  # Start tkinter loop to update window


if __name__ == '__main__':
    main()
