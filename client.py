import tkinter as tk
import socket
import threading

# Initialize global variables
connected = False
terminating = False
client_socket = None

def insert_to_logs(message):
    # Function to insert a message into the logs Text widget
    logs.config(state=tk.NORMAL)
    logs.insert(tk.END, f"{message}\n")
    logs.config(state=tk.DISABLED)

def connect():
    # Function to handle the connection to the server
    global client_socket, connected, receive_thread
    ip = ip_entry.get()
    port_num = int(port_entry.get())

    username = username_entry.get()
    if username == "":
        insert_to_logs("Please enter a username")
        return
    
    if port_entry == "" or not port_entry.get().isdigit():
        insert_to_logs("Please enter a valid port number")
        return
    
    try:
        # Initialize and connect the client socket
        client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        client_socket.connect((ip, port_num))

        connected = True
        insert_to_logs(f"Connected to the server at {ip}:{port_num}\n")

        # Identify the username
        identify()
        insert_to_logs(f"Identifying the username as {username}")

        # Set buttons' states
        connect_button["text"] = "Disconnect"
        connect_button["command"] = disconnect
        
        for channel in channels:
            channel["subscribe_button"]["state"] = "normal"

        server_status_info.config(state=tk.NORMAL)
        server_status_info.delete(0, "end") 
        server_status_info.insert(0, "connected ✅") 
        server_status_info.config(state=tk.DISABLED)

        ip_entry.config(state=tk.DISABLED)
        port_entry.config(state=tk.DISABLED)
        username_entry.config(state=tk.DISABLED)

        # Start a thread to listen for incoming messages
        receive_thread = threading.Thread(target=receive_messages, daemon=True)
        receive_thread.start()

    except socket.error as e:
        connected = False
        server_status_info.config(state=tk.NORMAL)
        server_status_info.delete(0, "end")  
        server_status_info.insert(0, "Could not connect ❌")  
        server_status_info.config(state=tk.DISABLED)
        insert_to_logs(f"Could not connect to the server; Error: {e}")

def disconnect():
    # Function to handle the disconnection from the server
    global client_socket, connected, receive_thread
    if connected:
        connected = False
        client_socket.send(f"disconnect".encode())
        client_socket.close()
        insert_to_logs("Disconnected from the server\n")

    connect_button["text"] = "Connect"
    connect_button["command"] = connect

    ip_entry.config(state=tk.NORMAL)
    port_entry.config(state=tk.NORMAL)
    username_entry.config(state=tk.NORMAL)

    server_status_info.config(state=tk.NORMAL)
    server_status_info.delete(0, "end") 
    server_status_info.insert(0, "not connected") 
    server_status_info.config(state=tk.DISABLED)

    for channel_index in range(number_of_channels):
        channels[channel_index]["subscribe_button"]["text"] = "Subscribe"
        channels[channel_index]["subscribe_button"]["command"] = lambda channel_index=channel_index: subscribe(channel_index)
        channels[channel_index]["subscribe_button"].config(state=tk.DISABLED)

        channels[channel_index]["subscription_status"]["text"] = channels[channel_index]["subscription_status"]["text"].replace("(subscribed)", "(not subscribed)")

        channels[channel_index]["send_button"].config(state=tk.DISABLED)
        channels[channel_index]["message_entry"].config(state=tk.DISABLED)
        channels[channel_index]["messages"].config(state=tk.NORMAL)
        channels[channel_index]["messages"].delete("1.0", "end")
        channels[channel_index]["messages"].config(state=tk.DISABLED)

def identify():
    # Function to send the username for identification to the server
    global client_socket, connected
    username = username_entry.get()
    if connected:
        try:
            client_socket.send(f"identify {username}".encode())
        except:
            connected = False
            insert_to_logs("Failed to identify\n")
            raise Exception("Failed to identify")
    else:
        insert_to_logs("Not connected to the server\n")

def subscribe(channel_id):
    # Function to subscribe to a channel
    global client_socket, connected
    if connected:
        try:
            channels[channel_id]["subscribe_button"]["text"] = "Unsubscribe"
            channels[channel_id]["subscribe_button"]["command"] = lambda channel_id=channel_id: unsubscribe(channel_id)

            channels[channel_id]["subscription_status"]["text"] = channels[channel_id]["subscription_status"]["text"].replace("(not subscribed)", "(subscribed)")
            
            channels[channel_id]["send_button"].config(state=tk.NORMAL)
            channels[channel_id]["message_entry"].config(state=tk.NORMAL)
            
            channels[channel_id]["messages"].config(state=tk.DISABLED)

            client_socket.send(f"subscribe {channel_id}".encode())
            insert_to_logs(f"Subscribed to channel {channel_names[channel_id]}")
        except socket.error as e:
            insert_to_logs(f"Failed to subscribe to channel {channel_names[channel_id]}\n")
    else:
        insert_to_logs("Not connected to the server\n")

def unsubscribe(channel_id):
    # Function to unsubscribe from a channel
    global client_socket, connected
    if connected:
        try:
            channels[channel_id]["subscribe_button"]["text"] = "Subscribe"
            channels[channel_id]["subscribe_button"]["command"] = lambda channel_id=channel_id: subscribe(channel_id)

            channels[channel_id]["subscription_status"]["text"] = channels[channel_id]["subscription_status"]["text"].replace("(subscribed)", "(not subscribed)")

            channels[channel_id]["send_button"].config(state=tk.DISABLED)
            channels[channel_id]["message_entry"].config(state=tk.DISABLED)

            # Uncomment the following line if the previous messages in the channel are to be deleted
            # channels[channel_id]["messages"].config(state=tk.NORMAL)
            # channels[channel_id]["messages"].delete("1.0", "end")
            channels[channel_id]["messages"].config(state=tk.DISABLED)

            client_socket.send(f"unsubscribe {channel_id}".encode())
            insert_to_logs(f"Unsubscribed from channel {channel_names[channel_id]}")
        except socket.error as e:
            insert_to_logs(f"Failed to unsubscribe from channel {channel_names[channel_id]}\n")
    else:
        insert_to_logs("Not connected to the server\n")

def send_message(channel_index):
    # Function to send a message to a channel
    global client_socket, connected
    message = channels[channel_index]["message_entry"].get()
    if connected:
        try:
            client_socket.send(f"message {channel_index} {message}".encode())
            insert_to_logs(f"Sent '{message}' to channel {channel_names[channel_index]}")
            channels[channel_index]["message_entry"].delete(0, "end")  # Clear the message_entry after sending
        except socket.error as e:
            insert_to_logs(f"Could not send message to the server; Error: {e}")
    else:
        insert_to_logs("Not connected to the server\n")

def receive_messages():
    # Function to receive and handle incoming messages
    global client_socket, connected
    while connected:
        try:
            data = client_socket.recv(1024)
            if not data:
                insert_to_logs("Connection closed by the server")
                disconnect()
                break
            
            message = data.decode()
            insert_to_logs(f"\nReceived: {message}")
            handle_message(message)

        except socket.error as e:
            print(f"Connection closed")
            disconnect()
            break

def handle_message(message):
    # Function to handle different types of messages received from the server
    global connected
    words = message.split()
    command = words[0]
    
    if command == "message":
        username = words[1]
        channel_index = int(words[2])
        message_text = " ".join(words[3:])
        
        channels[channel_index]["messages"].config(state=tk.NORMAL)
        channels[channel_index]["messages"].insert("end", f"{username}: {message_text}\n")
        channels[channel_index]["messages"].config(state=tk.DISABLED)

    elif command == "failed":
        message_text = " ".join(words[1:])
        insert_to_logs(f"Could not connect to the server; {message_text}\n")
        connected = False
        disconnect()

    elif command == "closed":
        insert_to_logs("Connection closed by the server")
        disconnect()

def on_exit():
    # Function to handle the application exit
    global connected
    if connected:
        disconnect()
    root.quit()

# Define channel names and the number of channels
channel_names = ["IF 100", "SPS 101"]
number_of_channels = len(channel_names)

# Initialize the Tkinter root window
root = tk.Tk()
root.title("Chat Application")

# Configure grid columns for channels
for i in range(number_of_channels):
    root.grid_columnconfigure(i, weight=1)

# Create the server connection frame
server_connection_frame = tk.LabelFrame(root, text="Connect to Server", padx=10, pady=10)
server_connection_frame.grid(row=0, column=0, sticky="ew", padx=10, pady=10, columnspan=number_of_channels)

# Configure grid columns for the server connection frame
for i in range(4):
    server_connection_frame.grid_columnconfigure(i, weight=1)

# Create and place widgets in the server connection frame
ip_label = tk.Label(server_connection_frame, text="IP:")
ip_label.grid(row=0, column=0, sticky="w")
ip_entry = tk.Entry(server_connection_frame)
ip_entry.grid(row=0, column=1)

port_label = tk.Label(server_connection_frame, text="Port:")
port_label.grid(row=1, column=0, sticky="w")
port_entry = tk.Entry(server_connection_frame)
port_entry.grid(row=1, column=1)

server_status_label = tk.Label(server_connection_frame, text="Server Status:")
server_status_label.grid(row=1, column=2, sticky="w")
server_status_info = tk.Entry(server_connection_frame, state=tk.DISABLED)
server_status_info.grid(row=1, column=3)
server_status_info.insert(0, "not connected")

username_label = tk.Label(server_connection_frame, text="Username:")
username_label.grid(row=0, column=2, sticky="w")
username_entry = tk.Entry(server_connection_frame)
username_entry.grid(row=0, column=3, sticky="ew")

connect_button = tk.Button(server_connection_frame, text="Connect", command=connect)
connect_button.grid(row=2, column=0, columnspan=4, sticky="ew")

# Create a list to store channel information
channels = [{} for _ in range(number_of_channels)]

# Create and place widgets for each channel
for index, channel_name in enumerate(channel_names):
    channels[index]["frame"] = tk.LabelFrame(root, text=channel_name, padx=10, pady=10)
    channels[index]["frame"].grid(row=2, column=index, sticky="ew", padx=10, pady=10)
    channels[index]["frame"].columnconfigure(0, weight=1)
    channel_frame = channels[index]["frame"]

    channels[index]["subscription_status"] = tk.Label(channel_frame, text=f"Status: (not subscribed)")
    channels[index]["subscription_status"].grid(row=0, column=0, sticky="w")

    channels[index]["subscribe_button"] = tk.Button(channel_frame, text="Subscribe", state=tk.DISABLED)
    channels[index]["subscribe_button"].grid(row=0, column=1, sticky="e")
    channels[index]["subscribe_button"]["command"] = lambda index=index: subscribe(index)

    channels[index]["messages"] = tk.Text(channel_frame, width=40, state=tk.DISABLED)
    channels[index]["messages"].grid(row=1, column=0, columnspan=2, sticky="nsew", pady=10)

    channels[index]["message_label"] = tk.Label(channel_frame, text="Message:")
    channels[index]["message_label"].grid(row=2, column=0, sticky="w")
    channels[index]["message_entry"] = tk.Entry(channel_frame, state=tk.DISABLED)
    channels[index]["message_entry"].grid(row=3, column=0, sticky="ew", columnspan=3)

    channels[index]["send_button"] = tk.Button(channel_frame, text="Send", command=lambda index=index: send_message(index), state=tk.DISABLED)
    channels[index]["send_button"].grid(row=4, column=1, sticky="e")

# Create the logs frame
logs_frame = tk.LabelFrame(root, text="Logs", padx=10, pady=10)
logs_frame.grid(row=0, column=number_of_channels + 1, rowspan=3, sticky="nsew", padx=10, pady=10)
logs_frame.grid_rowconfigure(0, weight=1)

# Create and place the logs Text widget
logs = tk.Text(logs_frame, width=40, state=tk.DISABLED)
logs.grid(row=0, column=0, sticky="ns", padx=0, pady=0)

# Set default values for IP and port entries
ip_entry.insert(0, "127.0.0.1") 
port_entry.insert(0, "1234") 

# Set the function to be called on application exit
root.protocol("WM_DELETE_WINDOW", on_exit)

# Start the Tkinter main loop
root.mainloop()
