import os
import sys
sys.path.insert(0, os.getcwd())
from Ahc import ComponentModel, Event, ConnectorTypes, Topology, EventTypes
from Ahc import ComponentRegistry
from cryptography.fernet import Fernet
import json
from enum import Enum
from datetime import date, datetime
import time
from Channels.Channels import Channel
import networkx as nx
import matplotlib.pyplot as plt

registry = ComponentRegistry()
"""
    Overall model: (Top to bottom)
    SERVER
    ALICE
    BOB
"""

class AliceStates(Enum):
    INIT = 1
    SESSION_KEY_SENT = 2
    VERIFICATION_SENT = 3 # R_b - 1 is sent so that Bob verifies.
    SESSION_CONNECTED = 4

class BobStates(Enum):
    WAITING_SESSION_KEY = 1
    VERIFICATION_REQUEST_SENT = 2
    VERIFIED = 3 # Or SESSION_CONNECTED

# Trent/Server does not need states as it only receives one message from alice and sends back

Key_A = Fernet.generate_key()
Key_B = Fernet.generate_key()

alice_componentname = "Alice"
bob_componentname = "Bob"
A = alice_componentname[0].upper()
B = bob_componentname[0].upper()

class Trent(ComponentModel):

    alice_fernet = Fernet(Key_A)
    bob_fernet = Fernet(Key_B)

    """
    Trent receives a request from Alice to connect to Bob, (Step 1)
    Trent generates the message with session key and encrypted message to Bob which includes the session key aswell.
    Trent then encrypts this message with Alice's key and sends it to Alice (Step 2)
    """
    def on_message_from_bottom(self, eventobj: Event):
        print(f"I am {self.componentname}, received step 1, eventcontent={eventobj.eventcontent}\n")
        msg = eventobj.eventcontent
        session_key = Fernet.generate_key()
        message_to_bob = {"session_key": session_key.decode('utf-8'), "sender": msg["sender"]}
        message_to_alice = {
            "random_number": msg["random_number"], 
            "receiver": msg["receiver"],
            "session_key": session_key.decode('utf-8'),
            "encrypted_message": self.bob_fernet.encrypt(json.dumps(message_to_bob).encode('utf-8')).decode('utf-8'),
            }
        evt = Event(self, EventTypes.MFRT, self.alice_fernet.encrypt(json.dumps(message_to_alice).encode('utf-8')))
        self.send_down(evt)

    def on_message_from_top(self, eventobj: Event):
        print(f"I am {self.componentname}, BOTTOM eventcontent={eventobj.eventcontent}\n", flush=True)

class Alice(ComponentModel):
    alice_fernet = Fernet(Key_A)
    session_fernet = Fernet(Key_A)
    state = AliceStates.INIT
    random_number = 0

    """
    Alice on Topology start, sends a request to Trent to connect to Bob. (step 1)
    Alice sends name of sender, receiver and a random number to confirm later on in step 2.
    """
    def on_init(self, eventobj: Event):
        self.random_number = int.from_bytes(os.urandom(20), byteorder="big")
        msg = {
            "sender": self.componentname,
            "receiver": bob_componentname,
            "random_number": self.random_number
        }
        evt = Event(self, EventTypes.MFRT, msg)
        self.send_up(evt)

    def on_message_from_top(self, eventobj: Event):
        print(f"I am {self.componentname}, eventcontent={eventobj.eventcontent}\n")

    """
    Alice has 3 states to handle the steps.
    On INIT State Alice receives step 2 from Trent.
    Alice decrypts the message with the private key then sends the encrypted message that trent generated with Bob's private key to bob.
    Alice then sets its state to SESSION_KEY_SENT.

    On SESSION_KEY_SENT state Alice receives step 4 from Bob.
    Alice on this state receives Random number generated by bob encrypted with session key.
    Alice then sends R_b - 1 back to Bob so that Bob can verify the connection to prevent replay attacks.
    Alice sets its state to VERIFICATION_SENT.

    On VERIFICATION_SENT state if Alice is receiving messages from Bob, this means that connection is verified by Bob and Bob is sending legitimate messages.
    Alice can also send messages in this state to Bob.
    """
    def on_message_from_bottom(self, eventobj: Event):
        if self.state == AliceStates.INIT:
            print(f"I am {self.componentname}, received step 2, eventcontent={eventobj.eventcontent}\n")
            msg = json.loads(self.alice_fernet.decrypt(eventobj.eventcontent))
            if (self.random_number != msg["random_number"]):
                print(f"{self.componentname} - Random number cannot be verified. Random number generated: {self.random_number}, Random number received: {msg['random_number']}")
                return
            self.session_fernet = Fernet(msg["session_key"].encode("utf-8"))
            encrypted_msg = msg["encrypted_message"].encode('utf-8')
            evt = Event(self, EventTypes.MFRT, encrypted_msg)
            self.send_down(evt)
            self.state = AliceStates.SESSION_KEY_SENT
        elif self.state == AliceStates.SESSION_KEY_SENT:
            print(f"I am {self.componentname}, received step 4, eventcontent={eventobj.eventcontent}\n")
            msg = json.loads(self.session_fernet.decrypt(eventobj.eventcontent))
            msg["random_number"] -= 1
            evt = Event(self, EventTypes.MFRT, self.session_fernet.encrypt(json.dumps(msg).encode('utf-8')))
            self.send_down(evt)
            self.state = AliceStates.VERIFICATION_SENT
        elif self.state == AliceStates.VERIFICATION_SENT:
            print(f"I am {self.componentname}, eventcontent={eventobj.eventcontent}")
            msg = json.loads(self.session_fernet.decrypt(eventobj.eventcontent))
            print(f'{msg["message"]} received from {msg["sender"]}\n')
            # After receiving messages from bob send some to Bob.
            if (msg["message"] == 1):
                for i in range(0,2):
                    message = {
                        "message": i,
                        "sender": self.componentname
                    }
                    evt = Event(self, EventTypes.MFRT, self.session_fernet.encrypt(json.dumps(message).encode('utf-8')))
                    time.sleep(0.5)
                    self.send_down(evt)


class Bob(ComponentModel):
    bob_fernet = Fernet(Key_B)
    session_fernet = Fernet(Key_B)
    state = BobStates.WAITING_SESSION_KEY
    connected_to = ""
    random_number = 0

    """
    Bob also has 3 states to handle steps.
    On WAITING_SESSION_KEY state Bob receives step 3 from Alice.
    Bob decrypts the message and generates a random number R_b which is saved for verification later on.
    Bob then sends the random number R_b which is encrypted with the session key received from the message. Bob also saves this session key.

    On VERIFICATION_REQUEST_SENT state Bob receives step 5 from Alice.
    Bob decryptes the message and verifies that the message is R_b - 1 (step 6), otherwise just returns (which means that Topology has to be restarted to connect again.).
    After verifying Bob sets is state to VERIFIED which means that connection is established, and messages received in this state is legitimate messages.
    
    Bob sends some messages immidiately after establishing connection.
    """
    def on_message_from_bottom(self, eventobj: Event):
        if self.state == BobStates.WAITING_SESSION_KEY:
            print(f"I am {self.componentname}, received step 3, eventcontent={eventobj.eventcontent}\n")
            msg = json.loads(self.bob_fernet.decrypt(eventobj.eventcontent))
            self.session_fernet = Fernet(msg["session_key"].encode("utf-8"))
            self.connected_to = msg["sender"]
            self.random_number = int.from_bytes(os.urandom(20), byteorder="big")
            msg_to_send = {
                "random_number": self.random_number
            }
            evt = Event(self, EventTypes.MFRT, self.session_fernet.encrypt(json.dumps(msg_to_send).encode('utf-8')))
            self.send_up(evt)
            self.state = BobStates.VERIFICATION_REQUEST_SENT
        elif self.state == BobStates.VERIFICATION_REQUEST_SENT:
            print(f"I am {self.componentname}, received step 5, eventcontent={eventobj.eventcontent}\n")
            msg = json.loads(self.session_fernet.decrypt(eventobj.eventcontent))
            if (self.random_number - 1 != msg["random_number"]):
                print(f"{self.componentname} - Random number cannot be verified. Random number generated: {self.random_number}, Random number received: {msg['random_number']}")
                return
            self.state = BobStates.VERIFIED
            print(f"I am {self.componentname}, connected to {self.connected_to}, step 6, timestamp: {(time.time())}\n")
            # After connection send some messages to Alice.
            for i in range(0,2):
                message = {
                    "message": i,
                    "sender": self.componentname
                }
                evt = Event(self, EventTypes.MFRT, self.session_fernet.encrypt(json.dumps(message).encode('utf-8')))
                time.sleep(0.5)
                self.send_up(evt)
                
        elif self.state == BobStates.VERIFIED:
            print(f"I am {self.componentname}, eventcontent={eventobj.eventcontent}")
            msg = json.loads(self.session_fernet.decrypt(eventobj.eventcontent))
            print(f'{msg["message"]} received from {msg["sender"]}\n')
            
"""
Topology here is manually created instead of using already existing functions. This was done due to existing functions only accepting one ComponentModel type for nodes of the topology.
"""
def main():
    topo = Topology()

    topo.nodes["T"] = Trent("Trent", 0)
    topo.nodes[A] = Alice(alice_componentname, 1)
    topo.nodes[B] = Bob(bob_componentname, 2)
    
    topo.channels["T-" + A] = Channel("T-" + A, 3)
    topo.nodes["T"].connect_me_to_channel(ConnectorTypes.DOWN, topo.channels["T-" + A])
    topo.nodes[A].connect_me_to_channel(ConnectorTypes.UP, topo.channels["T-" + A])
    topo.channels[A + "-" + B] = Channel(A + "-" + B, 4)
    topo.nodes[A].connect_me_to_channel(ConnectorTypes.DOWN, topo.channels[A + "-" + B])
    topo.nodes[B].connect_me_to_channel(ConnectorTypes.UP, topo.channels[A + "-" + B])
    topo.G = nx.Graph()
    topo.G.add_node("T")
    topo.G.add_node(A)
    topo.G.add_node(B)
    topo.G.add_edge("T", A)
    topo.G.add_edge(A, B)

    nx.draw(topo.G, with_labels=True, font_weight='bold')
    plt.draw()
    
    print(f'Starting topology, timestamp: {time.time()}')
    topo.start()
    # while True: pass
    plt.show()
    

if __name__ == "__main__":
    main() 