import tkinter as tk
import socket
import threading

# Global variables
server_thread = None
server_socket = None
clients = []  # {"socket": socket, "address": address, "thread": thread, "username": username}
channel_names = ["IF 100", "SPS 101"]
channels_subscribers = [set() for _ in range(len(channel_names))]
number_of_channels = len(channel_names)

# Helper function to find the index of a client by its socket
def find_client_index(client_socket):
    for index, c in enumerate(clients):
        if c["socket"] == client_socket:
            return index

# Helper function to check if a username is already taken
def is_username_taken(username):
    for c in clients:
        if "username" in c and c["username"] == username:
            return True
    return False

# Server log function
def log_server_action(message):
    log_text.config(state=tk.NORMAL)
    log_text.insert(tk.END, f"{message}\n")
    log_text.config(state=tk.DISABLED)

# Update connected clients list on GUI
def update_connected_clients_box():
    connected_clients_text.config(state=tk.NORMAL)
    connected_clients_text.delete(1.0, tk.END)
    for c in clients:
        if "username" in c:
            connected_clients_text.insert(tk.END, f"{c['username']}\n")
    connected_clients_text.config(state=tk.DISABLED)

# Update channel subscribers lists on GUI
def update_channel_subscribers_boxes():
    for i in range(len(channel_names)):
        channel_texts[i].config(state=tk.NORMAL)
        channel_texts[i].delete(1.0, tk.END)
        for username in channels_subscribers[i]:
            channel_texts[i].insert(tk.END, f"{username}\n")
        channel_texts[i].config(state=tk.DISABLED)

# Start the server function
def start_server():
    global server_socket, server_thread

    if not port_entry.get().isdigit():
        log_server_action("Please enter a valid port number")
        return

    try:
        port = int(port_entry.get())
        server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        server_socket.bind(('0.0.0.0', port))
        server_socket.listen(5)

        log_server_action(f"Server started on port {port}")

        port_entry.config(state=tk.DISABLED)

        server_thread = threading.Thread(target=accept_connections, daemon=True)
        server_thread.start()

        start_stop_button["text"] = "Close Server"
        start_stop_button["command"] = close_server

    except socket.error as e:
        log_server_action(f"Could not start the server on port {port}; Error: {e}")

# Close the server function
def close_server():
    global server_socket, clients, channels_subscribers, server_thread
    log_server_action("Server closed")

    port_entry.config(state=tk.NORMAL)

    # send "close" message to all clients that the server is closing
    for client in clients:
        try:
            client["socket"].send("closed".encode())
        except socket.error as e:
            log_server_action(f"Could not send <closed> message to {client['address']}; Error: {e}")

    for client in clients:
        client["socket"].close()

    clients = []
    channels_subscribers = [set() for _ in range(len(channel_names))]
    update_connected_clients_box()
    update_channel_subscribers_boxes()

    if server_socket:
        server_socket.close()

    start_stop_button["text"] = "Start Server"
    start_stop_button["command"] = start_server

# Accept connections function (server main loop)
def accept_connections():
    global server_socket, clients
    while True:
        try:
            client_socket, client_address = server_socket.accept()

            log_server_action(f"Connection from {client_address}")

            new_client = {"socket": client_socket, "address": client_address}
            clients.append(new_client)

            receive_thread = threading.Thread(target=receive_messages, args=(client_socket,))
            receive_thread.start()

            clients[-1]["thread"] = receive_thread
        except socket.error as e:
            log_server_action("Connection closed")
            break

# Receive messages from a client
def receive_messages(client_socket):
    global clients
    while client_socket in [c["socket"] for c in clients]:
        try:
            message = client_socket.recv(1024).decode()
            if not message:
                break

            log_server_action(f"\nReceived: {message}\n")

            handle_message(client_socket, message)
        except socket.error as e:
            log_server_action("Connection Closed")
            break
        except Exception as e:
            log_server_action(f"Error: {e}")
            break

# Handle different types of messages from clients
def handle_message(client_socket, message):
    global channels_subscribers

    words = message.split()
    command = words[0]
    client_index = find_client_index(client_socket)
    the_client = clients[client_index]

    if command == "identify":
        try:
            username = words[1]
            if is_username_taken(username):
                client_socket.send("failed username taken".encode())
                clients[client_index]["socket"].close()
                del clients[client_index]
                log_server_action(f"Could not identify the username; Error: Username is taken")
                raise Exception("Username is taken")

            clients[client_index]["username"] = username
            log_server_action(f"{username} identified")
            update_connected_clients_box()
        except socket.error as e:
            log_server_action(f"Could not identify the username; Error: {e}")

    elif command == "subscribe":
        try:
            channel_index = int(words[1])
            username = the_client["username"]
            channels_subscribers[channel_index].add(username)
            log_server_action(f"{username} subscribed to {channel_names[channel_index]}")
            update_channel_subscribers_boxes()
        except Exception as e:
            log_server_action(f"Could not subscribe to the channel {channel_index}; Error: {e}")

    elif command == "unsubscribe":
        try:
            channel_index = int(words[1])
            username = the_client["username"]
            channels_subscribers[channel_index].remove(username)
            log_server_action(f"{username} unsubscribed from {channel_names[channel_index]}")
            update_channel_subscribers_boxes()
        except Exception as e:
            log_server_action(f"Could not unsubscribe from the channel {channel_index}; Error: {e}")

    elif command == "message":
        try:
            channel_index = int(words[1])
            username = the_client["username"]
            message_text = " ".join(words[2:])
            if username in channels_subscribers[channel_index]:
                send_message_to_channel(username, channel_index, message_text)

            log_server_action(f"{username} sent '{message_text}' to {channel_names[channel_index]}")

        except socket.error as e:
            log_server_action(f"Could not send the message to the channel {channel_index}; Error: {e}")

    elif command == "disconnect":
        try:
            if "username" in the_client:
                username = the_client["username"]

                for i in range(len(channel_names)):
                    if username in channels_subscribers[i]:
                        channels_subscribers[i].remove(username)
                        log_server_action(f"unsubscribed {username} from {channel_names[i]}")

                del clients[client_index]

                log_server_action(f"{username} disconnected")
            update_channel_subscribers_boxes()
            update_connected_clients_box()

        except socket.error as e:
            log_server_action(f"Could not disconnect the client; Error: {e}")

# Send a message to all subscribers of a channel
def send_message_to_channel(username, channel_index, message):
    global clients
    for client in clients:
        try:
            if "username" not in client:
                continue
            if client["username"] in channels_subscribers[channel_index]:
                client["socket"].send(f"message {username} {channel_index} {message}".encode())
        except socket.error as e:
            log_server_action(f"Error sending {username} message to channel {channel_index}: {e}")

# Close the server on GUI exit
def on_exit():
    close_server()
    root.quit()

# Create the main window
root = tk.Tk()
root.title("Chat Server")

# Server frame
server_frame = tk.LabelFrame(root, text="Start/Stop Server", padx=10, pady=10)
server_frame.grid(row=0, column=0, columnspan=2, sticky="nsew", padx=10, pady=10)
server_frame.grid_columnconfigure(1, weight=1)

port_label = tk.Label(server_frame, text="Port:")
port_label.grid(row=0, column=0)
port_entry = tk.Entry(server_frame)
port_entry.grid(row=0, column=1, padx=10, pady=10, sticky="ew")
port_entry.insert(0, "1234")

start_stop_button = tk.Button(server_frame, text="Start Server", command=start_server)
start_stop_button.grid(row=0, column=2, sticky="e")

# Server Actions
logs_frame = tk.LabelFrame(root, text="Logs", padx=10, pady=10)
logs_frame.grid(row=1, column=0, rowspan=3, sticky="nsew", padx=10, pady=10)
log_text = tk.Text(logs_frame, state=tk.DISABLED, wrap=tk.WORD, width=40, height=10 * (number_of_channels + 1))
log_text.pack(fill=tk.BOTH, expand=True)

# Connected Clients
connected_clients_frame = tk.LabelFrame(root, text="Connected Clients", padx=10, pady=10)
connected_clients_frame.grid(row=1, column=1, sticky="nsew", padx=10, pady=10)
connected_clients_text = tk.Text(connected_clients_frame, state=tk.DISABLED, wrap=tk.WORD, width=20, height=10)
connected_clients_text.pack()

# Channel frames and text boxes
channel_frames = []
channel_texts = []
for i, channel in enumerate(channel_names):
    # Create a frame for the channel
    channel_frame = tk.LabelFrame(root, text=channel, padx=10, pady=10)
    channel_frame.grid(row=i + 2, column=1, sticky="nsew", padx=10, pady=10)
    channel_frames.append(channel_frame)

    # Create a text box for the channel
    channel_text = tk.Text(channel_frame, state=tk.DISABLED, wrap=tk.WORD, width=20, height=10)
    channel_text.pack()
    channel_texts.append(channel_text)

# GUI exit handling
root.protocol("WM_DELETE_WINDOW", on_exit)
root.mainloop()
