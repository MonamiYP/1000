# Import required modules
import socket
import threading
import time
from random import shuffle

################
# SERVER = IP address here
PORT = 5050
LISTENER_LIMIT = 2
clients = []  # Contains (username, user)
game_state = 'false'
game = None

value_points = {'9': 0, 'J': 2, 'Q': 3, 'K': 4, '10': 10, 'A': 11}
suit_points = {'Spades': 40, 'Clubs': 60, 'Diamonds': 80, 'Hearts': 100}


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
                check_command(client, username, message)
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


def check_command(client, username, command):
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
        game.bid(client, username, int(command[5:]))

    elif command[:6] == "/raise" and game_state == 'final_bid':
        game.bid(client, username, int(command[7:]))

    # Type this command to let a player pass the bid
    elif command == "/pass" and (game_state == 'bid' or game_state == 'final_bid'):
        game.fold(client, username)

    # Type this command to let the player who wom the bid pick two cards
    elif command[:5] == "/pick" and game_state == 'exchange':
        number = int(command[6:])
        if number == 1 or number == 2:
            game.pick(username, number)
        else:
            send_to = clients[0][1]
            if clients[0][0] != username:
                send_to = clients[1][1]
            broadcast_messages_client(send_to, 'ERROR~' + f'Not a valid choice, please pick 1 or 2')

    # Type this command to let the player who won the bid discard a card and give to the other player
    elif command[:8] == "/discard" and game_state == 'give':
        if command[9:11] == '10':
            value = '10'
            suit = command[12:]
        else:
            value = command[9:10]
            suit = command[11:]
        game.discard(username, value, suit)

    # Type this command to play a card
    elif command[:5] == "/play" and game_state == 'play':
        if command[6:8] == '10':
            value = '10'
            suit = command[9:]
        else:
            value = command[6:7]
            suit = command[8:]
        game.play(username, value, suit)

    else:
        broadcast_messages_client(client, "ERROR~Not a valid command")


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


def simplify_deck(deck):
    simplified_deck = []
    for item in deck:
        simplified_tuple = item[:2]
        simplified_deck.append(simplified_tuple)
    return simplified_deck


class Deck:
    suits = ["Spades", "Clubs", "Diamonds", "Hearts"]
    values = ["9", "J", "Q", "K", "10", "A"]
    value_point = [0, 2, 3, 4, 10, 11]

    def __init__(self):
        self.cards = []
        self.deckA = []
        self.deckB = []
        self.deck1 = []
        self.deck2 = []
        for i in range(6):
            for j in range(4):
                self.cards.append((self.values[i], self.suits[j], self.value_point[i]))
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
        self.game_board = []
        self.trump = None
        self.turn = None
        self.current_bid = 100
        self.current_bidder = None
        self.current_turn = None
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
        broadcast_messages_client(clients[0][1], name + f"Your cards are: {simplify_deck(playerA.deck)}")
        broadcast_messages_client(clients[1][1], name + f"Your cards are: {simplify_deck(playerB.deck)}")
        time.sleep(5)
        broadcast_messages_all(name + "Bidding begins. Please bid using /bid _number_ and pass using /pass"
                                      "\n e.g. /bid 115")
        self.current_bidder = clients[0][0]
        time.sleep(0.1)

        broadcast_messages_all(name + f"{self.current_dealer} is the dealer, holding a bid of 100")

    def bid(self, client, username, bid):
        global game_state
        if game_state == 'bid':
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
        else:  # Runs if it's the final bid i.e. when the player who won the bid is making their final raises
            # Check if the player making the raise is the one who won the bid previously
            if username == self.current_bidder and self.bid_valid(bid):
                self.current_bid = bid
                broadcast_messages_all(username + '~' + f' raised to {self.current_bid}')
                time.sleep(0.1)
                broadcast_messages_all("GAME~" + "Ready to start game")
                time.sleep(0.1)
                broadcast_messages_all(
                    "GAME~" + f"Place cards with /play _number_ _suit_. {self.current_bidder} starts"
                              f"\n e.g. /play A Hearts")
                game_state = 'play'
            else:
                broadcast_messages_client(client, "ERROR~Raise value was not valid or it's not your turn to raise")

    # Function to check if the bid is valid
    def bid_valid(self, bid):
        try:
            if (bid % 5 == 0) and bid > self.current_bid:
                return True
        except:
            return False

    # Function called when a player passes
    def fold(self, client, username):
        global game_state
        if game_state == 'bid':
            if username != self.current_bidder:
                game_state = 'exchange'
                broadcast_messages_all("GAME" + '~' + f'{username} passed. {self.current_bidder} starts the game')
                time.sleep(0.1)
                broadcast_messages_all(
                    "GAME" + '~' + f'{self.current_bidder} please choose pile 1 or 2 with /pick _number_ '
                                   f'\n e.g. /pick 1')
                time.sleep(0.1)
            else:
                if playerA.player_name == username:
                    broadcast_messages_client(clients[0][1], "ERROR~You are the current bidder, you cannot pass now")
                if playerB.player_name == username:
                    broadcast_messages_client(clients[1][1], "ERROR~You are the current bidder, you cannot pass now")
        else:  # Runs if it's the final bid i.e. when the player who won the bid is making their final raises
            # Check if the player making the raise is the one who won the bid previously
            if username == self.current_bidder:
                broadcast_messages_all(username + '~' + f'Did not raise.')
                time.sleep(0.1)
                broadcast_messages_all("GAME~" + "Ready to start game")
                time.sleep(0.1)
                broadcast_messages_all(
                    "GAME~" + f"Place cards with /play _number_ _suit_. {self.current_bidder} starts"
                              f"\n e.g. /play A Hearts")
                game_state = 'play'
            else:
                broadcast_messages_client(client, "ERROR~Raise value was not valid or it's not your turn to raise")

    # Function called when a player is picking two cards from the pile of 4
    def pick(self, username, number):
        global game_state
        broadcast_messages_all(username + "~" + f"pick pile number {number}")
        time.sleep(0.1)
        exchanging = True
        while exchanging:
            # Check to see which player is the one who is exchanging cards
            if playerA.player_name == username and username == self.current_bidder:
                playerA.deck += self.deck1
                playerA.deck = sort_deck(playerA.deck)
                game_state = "give"
            elif playerB.player_name == username and username == self.current_bidder:
                playerB.deck += self.deck1
                playerB.deck = sort_deck(playerB.deck)
                game_state = "give"
            else:
                broadcast_messages_all(f"[ERROR]~It's not your turn {username}, you dipshit")
                break

            broadcast_messages_client(clients[0][1], "GAME~" + f"Your cards are: {simplify_deck(playerA.deck)}")
            broadcast_messages_client(clients[1][1], "GAME~" + f"Your cards are: {simplify_deck(playerB.deck)}")
            time.sleep(0.1)
            broadcast_messages_all("GAME~" + f"{self.current_bidder} please choose a card to give to"
                                             f" the other player with /discard _number_ _suit_"
                                             f"\n e.g. /discard 9 Hearts")
            time.sleep(0.1)
            exchanging = False

    # Function called when a player wants to discard a card
    def discard(self, username, value, suit):
        global game_state
        discarding = True
        while discarding:
            # Check which player the username belongs to
            if playerA.player_name == username and username == self.current_bidder:
                # Check if a card the player wants to discard is valid
                if (value, suit) in simplify_deck(playerA.deck):
                    playerA.deck.remove((value, suit, value_points[value]))
                    playerB.deck.append((value, suit, value_points[value]))
                    playerB.deck = sort_deck(playerB.deck)
                else:
                    # The card player wanted to discard was not in their cards
                    broadcast_messages_client(clients[0][1], "ERROR~" + f"Was not able to discard the card"
                                                                        f" ({value}, {suit}). Please try again.")
                    break
            elif playerB.player_name == username and username == self.current_bidder:
                # Check if a card the player wants to discard is valid
                if (value, suit) in simplify_deck(playerB.deck):
                    playerB.deck.remove((value, suit, value_points[value]))
                    playerA.deck.append((value, suit, value_points[value]))
                    playerA.deck = sort_deck(playerA.deck)
                else:
                    # The card player wanted to discard was not in their cards
                    broadcast_messages_client(clients[1][1], "ERROR~" + f"Was not able to discard the card"
                                                                        f" ({value}, {suit}). Please try again.")
                    break
            else:
                break
            broadcast_messages_all(username + "~" + f"discarded a card")
            time.sleep(0.5)
            broadcast_messages_client(clients[0][1], "GAME~" + f"Your cards are: {simplify_deck(playerA.deck)}")
            broadcast_messages_client(clients[1][1], "GAME~" + f"Your cards are: {simplify_deck(playerB.deck)}")
            time.sleep(0.5)
            broadcast_messages_all("GAME~" + f"{self.current_bidder} please state your final bid using /raise _number_"
                                             f" or pass using /pass")
            game_state = "final_bid"
            self.current_turn = username
            discarding = False

    # Function called when player wants to put down a card to play the game
    def play(self, username, value, suit):
        # Check if it's supposed to be the players turn
        if self.current_turn == username and playerA.player_name == username:
            # Check if a card the player wants to discard is valid
            if self.play_valid_card(value, suit, playerA):
                broadcast_messages_all(username + f"~{value} of {suit}")
                time.sleep(0.1)
                self.place_card(value, suit, playerA)
            else:
                # The card player wanted to discard was not valid
                broadcast_messages_client(clients[0][1], "ERROR~" + f"The card ({value}, {suit}) is not a "
                                                                    f"valid option. Please try again.")
        elif self.current_turn == username and playerB.player_name == username:
            # Check if a card the player wants to discard is valid
            if self.play_valid_card(value, suit, playerB):
                broadcast_messages_all(username + f"~{value} of {suit}")
                time.sleep(0.1)
                self.place_card(value, suit, playerB)
            else:
                # The card player wanted to discard was not valid
                broadcast_messages_client(clients[1][1], "ERROR~" + f"The card ({value}, {suit}) is not a "
                                                                    f"valid option. Please try again.")
        else:  # If it's not supposed to be the username's turn, then send them an error message
            if playerA.player_name == username:
                broadcast_messages_client(clients[0][1], "ERROR~" + f"It ain't your turn yet you impatient lil bitch")
            else:
                broadcast_messages_client(clients[1][1], "ERROR~" + f"It ain't your turn yet you impatient lil bitch")

    def play_valid_card(self, value, suit, player):
        valid = True
        # Check if the card that wants to be played is n the players deck
        if (value, suit) not in simplify_deck(player.deck):
            valid = False
        # Check that if there is already a card on the table, you are responding properly to it
        if self.game_board:
            if self.game_board[0][1] != suit and \
                    [(self.game_board[0][1] in simplify_deck(player.deck)[i][0])
                     for i in range(len(simplify_deck(player.deck)))]:
                valid = False
        return valid

    def place_card(self, value, suit, player):
        player.deck.remove((value, suit, value_points[value]))
        # If there is already a card on the board, then check who is the winner
        if self.game_board:
            # compare_cards returns true if the player wins
            if self.compare_cards(value, suit):
                player.score += value_points[value]
                broadcast_messages_all(f"GAME~{player.player_name} wins the round. It's {player.player_name}'s turn")
            else:
                if player == playerA:
                    self.current_turn = playerB.player_name
                    playerB.score += value_points[self.game_board[0][0]]
                    broadcast_messages_all(f"GAME~{playerB.player_name} wins the round. "
                                           f"It's {playerB.player_name}'s turn")
                else:
                    self.current_turn = playerA.player_name
                    playerA.score += value_points[self.game_board[0][0]]
                    broadcast_messages_all(f"GAME~{playerA.player_name} wins the round. "
                                           f"It's {playerA.player_name}'s turn")
            self.game_board = []
            time.sleep(0.1)
            broadcast_messages_client(clients[0][1], "GAME~" + f"Your cards are: {simplify_deck(playerA.deck)}")
            broadcast_messages_client(clients[1][1], "GAME~" + f"Your cards are: {simplify_deck(playerB.deck)}")
        else:  # Player is the first one to place card down
            self.game_board.append((value, suit))
            if player == playerA:
                self.current_turn = playerB
            else:
                self.current_turn = playerA
            # If the player has a pair
            if value == "Q" and ("K", suit) in simplify_deck(player.deck):
                player.score += suit_points[suit]
                self.trump = suit
                broadcast_messages_all(player.player_name + '~' + f"{suit_points[suit]}")

    def compare_cards(self, value, suit):
        win = True
        # Check if the card put down is a trump, and if opponents is too
        if self.trump == suit and self.trump == self.game_board[0][1] \
                or self.trump != suit and self.trump != self.game_board[0][1]:
            # Check if the suits are the same
            if self.game_board[0][1] != suit:
                win = False
            elif value_points[self.game_board[0][0]] > value_points[value]:
                win = False
        elif self.trump != suit and self.trump == self.game_board[0][1]:
            win = False
        return win


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
