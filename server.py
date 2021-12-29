# Import required modules
import socket
import threading

SERVER = "127.0.0.1"
PORT = 5050
LISTENER_LIMIT = 2
clients = []  # Contains (username, user)


# Send messages to all connected clients
def broadcast_messages_all(message):
    for client in clients:
        broadcast_messages_client(client[1], message)


# Send messages to one single user
def broadcast_messages_client(client, message):
    client.sendall(message.encode('utf-8'))


# Listens for upcoming messages from a user
def listen_for_messages(client, username):
    while True:
        message = client.recv(1024).decode('utf-8')
        if message != '':
            final_message = username + ':' + message
            broadcast_messages_all(final_message)
        else:
            # Message received from user is empty
            pass


# Runs for each user, it handles the messages
def handle_client(client, address):
    connected = True
    while connected:
        # Get username from user
        username = client.recv(1024).decode('utf-8')
        if username != '':
            clients.append((username, client))
            prompt_message = "SERVER:" + f"{username} added to the chat"
            broadcast_messages_all(prompt_message)
            print(f"[NEW CONNECTION] {address} connected.")
            break  # If username acquired, move on (to create new thread)
        else:
            # Client username is empty
            pass

    # Create new thread  to listen for messages separate from the thread in main
    # which creates a thread for each user
    thread = threading.Thread(target=listen_for_messages, args=(client, username))
    thread.start()


# Main function
def main():
    # Create the socket class object
    # AF_INET: using IPv4 address
    # SOCK_STREAM: we are using TCP package for communication
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

    try:
        # Provide server an address in the form of host IP and port
        server.bind((SERVER, PORT))
        print("Running the server")
    except:
        print(f"Unable to bind to host '{SERVER}' and port '{PORT}'")

    # Set server limit
    server.listen(LISTENER_LIMIT)

    # While loop to keep listening to user connections
    while True:
        client, address = server.accept()  # Address is a tuple
        print(f"Successfully connected with {str(address)}")

        # Create a new thread every time a new user is connected
        thread = threading.Thread(target=handle_client, args=(client, address))
        thread.start()


if __name__ == '__main__':
    main()

#
# # Receives and listens for messages
# def receive(server):
#     server.listen()
#     while True:
#         user.send('USERNAME'.encode('ascii'))
#         username = user.recv(1024).decode('ascii')
#         usernames.append(username)
#         clients.append(user)
#
#         print(f'Username of the user is {username}!')
#         broadcast(f'{username} joined the chat!'.encode('ascii'))
#         user.send('Connected to the server!'.encode('ascii'))
#

#         print(f"[ACTIVE CONNECTIONS] {threading.activeCount() - 1}")
