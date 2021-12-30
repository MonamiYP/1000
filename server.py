# Import required modules
import socket
import threading
import time
from random import shuffle

SERVER = "127.0.0.1"
PORT = 5050
LISTENER_LIMIT = 2
clients = []  # Contains (username, user)
game_state = 'false'
game = None


# Send messages to all connected clients
def broadcast_messages_all(message):
    for client in clients:
        broadcast_messages_client(client[1], message)


# Send messages to one single user
def broadcast_messages_client(client, message):
    client.sendall(message.encode('utf-8'))


# Listens for upcoming messages from a user
def listen_for_messages(client, username):
    global game_state
    connected = True
    while connected:
        message = client.recv(1024).decode('utf-8')
        if message != '':
            if message == '!DISCONNECT':
                broadcast_messages_all(f"SERVER~{username} has disconnected")
                connected = False
            elif message[0] == '/':
                # If the message starts with / then check to see what command it is
                check_command(username, message)
            else:
                # What is being sent to everyone
                final_message = username + '~' + message
                broadcast_messages_all(final_message)
        else:
            # Message received from user is empty
            pass

    print("Client disconnecting")
    game_state = 'false'
    clients.remove((f'{username}', client))
    client.close()


# Runs for each user, it handles the messages
def handle_client(client, address):
    global playerA
    global playerB
    connected = True
    while connected:
        # Get username from user
        username = client.recv(1024).decode('utf-8')
        if username != '':
            clients.append((username, client))
            prompt_message = "SERVER~" + f"{username} added to the chat"
            broadcast_messages_all(prompt_message)
            print(f"[NEW CONNECTION] {address} connected.")

            # Create a new instance of the Persons class
            if clients[0][0] == username:
                playerA = Player(username)
                playerA.dealer = True
            else:
                playerB = Player(username)
                playerB.dealer = False

            # Create new thread  to listen for messages separate from the thread in main
            # which creates a thread for each user
            thread = threading.Thread(target=listen_for_messages, args=(client, username))
            thread.start()
            break  # If username acquired, move on (to create new thread)
        else:
            # Client username is empty
            pass


def check_command(username, command):
    global game_state
    global game
    # Command to start game, only works if the game_state is false
    if command == "/1000" and game_state == 'false':
        # Start game
        game_state = 'bid'
        game = Game()
        game.deal()

    # Type this command to bid a number
    elif command[:4] == "/bid" and game_state == 'bid':
        game.bid(username, int(command[5:]))

    # Type this command to let a player pass the bid
    elif command == "/pass" and game_state == 'bid':
        game_state = 'exchange'
        game.fold(username)

    # Type this command to let the player who wom the bid pick two cards
    elif command[:5] == "/pick" and game_state == 'exchange':
        number = int(command[6:])
        if number == 1 or number == 2:
            game_state = "give"
            game.pick(username, number)
        else:
            send_to = clients[0][1]
            if clients[0][0] != username:
                send_to = clients[1][1]
            broadcast_messages_client(send_to, 'ERROR~' + f'Not a valid choice, please pick 1 or 2')

    # Type this command to let the player who won the bid discard a card and give to the other player
    elif command[:8] == "/discard" and game_state == 'give':
        pass

    # Type this command to play a card
    elif command[:5] == "/play":
        pass


def sort_deck(deck):
    s_deck = []
    c_deck = []
    d_deck = []
    h_deck = []
    new_deck = sorted(deck, key=lambda data: data[2])
    for i in range(len(deck)):
        if new_deck[i][1] == 'Spades':
            s_deck.append(new_deck[i])
        elif new_deck[i][1] == 'Clubs':
            c_deck.append(new_deck[i])
        elif new_deck[i][1] == 'Diamonds':
            d_deck.append(new_deck[i])
        elif new_deck[i][1] == 'Hearts':
            h_deck.append(new_deck[i])
    new_deck = s_deck + c_deck + d_deck + h_deck
    return new_deck


class Deck:
    suits = ["Spades", "Clubs", "Diamonds", "Hearts"]
    values = ["9", "J", "Q", "K", "10", "A"]
    points = [0, 2, 3, 4, 10, 11]

    def __init__(self):
        self.cards = []
        self.deckA = []
        self.deckB = []
        self.deck1 = []
        self.deck2 = []
        for i in range(6):
            for j in range(4):
                self.cards.append((self.values[i], self.suits[j], self.points[i]))
                shuffle(self.cards)

    # Function that deals the cards (10 for each player, 4 aside)
    def deal(self):
        # Create the decks
        deck = self.cards
        for i in range(10):
            self.deckA.append(deck[i])
            self.deckB.append(deck[i + 10])
        for i in range(2):
            self.deck1.append(deck[-i - 1])
        for i in range(2):
            self.deck2.append(deck[-i - 3])

        return sort_deck(self.deckA), sort_deck(self.deckB), self.deck1, self.deck2


# A player class to keep track of scores, who the dealer is and decks
class Player:
    def __init__(self, username):
        self.player_name = username
        self.score = 0
        self.wins = 0
        self.dealer = False
        self.deck = []

    def change_dealer(self):
        if self.dealer:
            self.dealer = False
        else:
            self.dealer = True


class Game:
    global playerA, playerB

    def __init__(self):
        self.deck = []
        self.deck1 = []
        self.deck2 = []
        self.current_bid = 100
        self.current_bidder = None
        if playerA.dealer:
            self.current_dealer = clients[0][0]
        else:
            self.current_dealer = clients[1][0]

    def deal(self):
        self.deck = Deck()
        playerA.deck, playerB.deck, self.deck1, self.deck2 = self.deck.deal()

        # Send messages to show all clients
        name = 'GAME~'
        message = f"1000 game starting between {clients[0][0]} and {clients[1][0]}"
        broadcast_messages_all(name + message)
        time.sleep(0.1)
        broadcast_messages_all(name + "Dealing...")
        time.sleep(1)

        # Send a different message to each client
        broadcast_messages_client(clients[0][1], name + f"Your cards are: {playerA.deck}")
        broadcast_messages_client(clients[1][1], name + f"Your cards are: {playerB.deck}")
        time.sleep(1)
        broadcast_messages_all(name + "Bidding begins. Please bid using /bid _number_ and pass using /pass")
        time.sleep(0.1)
        self.current_bidder = clients[0][0]

        broadcast_messages_all(name + f"{self.current_dealer} is the dealer")

    def bid(self, username, bid):
        broadcast_messages_all(username + '~' + f' bid {bid}')
        time.sleep(0.1)

        # Call a function to check validity of bid
        if self.bid_valid(bid):
            self.current_bid = bid
            self.current_bidder = username
        else:
            broadcast_messages_all('ERROR~Not a valid bid')
            time.sleep(0.1)

        broadcast_messages_all('GAME~' + f'Current bid: {self.current_bid}, bidder: {self.current_bidder}')

    # Function to check if the bid is valid
    def bid_valid(self, bid):
        try:
            if (bid % 5 == 0) and bid > self.current_bid:
                return True
        except:
            return False

    # Function called when a player passes
    def fold(self, username):
        broadcast_messages_all("GAME" + '~' + f'{username} passed. {self.current_bidder} starts the game')
        time.sleep(0.1)
        broadcast_messages_all("GAME" + '~' + f'{self.current_bidder} please choose pile 1 or 2 with /pick _number_')
        time.sleep(0.1)

    # Function called when a player is picking two cards from the pile of 4
    def pick(self, username, number):
        # Check to see which player is the one who is exchanging cards
        if playerA.player_name == username:
            playerA.deck += self.deck1
            playerA.deck = sort_deck(playerB.deck)
        else:
            playerB.deck += self.deck1
            playerB.deck = sort_deck(playerB.deck)

        broadcast_messages_all(username + "~" + f"pick pile number {number}")
        time.sleep(0.1)
        broadcast_messages_client(clients[0][1], "GAME~" + f"Your cards are: {playerA.deck}")
        broadcast_messages_client(clients[1][1], "GAME~" + f"Your cards are: {playerB.deck}")
        time.sleep(0.1)


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
        print(f"[ACTIVE CONNECTIONS] {threading.active_count() - 1}")


if __name__ == '__main__':
    main()
