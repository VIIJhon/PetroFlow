import time
import threading
import random

class RaftNode:
    """
    Simulates a Raft Distributed Consensus Node for High-Availability (HA).
    If the Leader dies, Followers instantly hold a cryptographic election to promote a new Leader.
    """
    def __init__(self, node_id: str):
        self.node_id = node_id
        self.state = "FOLLOWER" # States: FOLLOWER, CANDIDATE, LEADER
        self.term = 0
        self.leader_id = None
        self.last_heartbeat = time.time()
        self.election_timeout = random.uniform(0.150, 0.300) # 150ms to 300ms
        
    def receive_heartbeat(self, leader_id: str, term: int):
        """Called when the current Leader broadcasts a heartbeat."""
        if term >= self.term:
            self.term = term
            self.leader_id = leader_id
            self.state = "FOLLOWER"
            self.last_heartbeat = time.time()
            
    def check_election_timeout(self) -> bool:
        """Returns True if the Leader has died and an election must start."""
        if self.state == "LEADER":
            return False
            
        elapsed = time.time() - self.last_heartbeat
        if elapsed > self.election_timeout:
            return True
        return False
        
    def start_election(self) -> dict:
        """Converts to CANDIDATE and requests votes from the cluster."""
        self.state = "CANDIDATE"
        self.term += 1
        self.last_heartbeat = time.time() # Reset timer
        return {
            "type": "REQUEST_VOTE",
            "candidate_id": self.node_id,
            "term": self.term
        }
        
    def process_vote_request(self, candidate_id: str, term: int) -> bool:
        """Decides whether to vote for a candidate."""
        if term > self.term:
            self.term = term
            self.state = "FOLLOWER"
            return True # Grant vote
        return False # Reject vote
        
    def become_leader(self):
        """Promotes self to Leader and prepares to broadcast heartbeats."""
        self.state = "LEADER"
        self.leader_id = self.node_id
        
class HAClusterSimulator:
    """Simulates a 3-node PetroFlow cluster preventing downtime."""
    def __init__(self):
        self.nodes = [RaftNode("Node-1"), RaftNode("Node-2"), RaftNode("Node-3")]
        
        # Node-1 starts as the hardcoded leader for simulation purposes
        self.nodes[0].become_leader()
        
    def simulate_leader_crash(self):
        """Kills Node-1, triggering a 150ms election where Node-2 or Node-3 takes over."""
        print("CRITICAL: Leader Node-1 has crashed due to hardware failure!")
        self.nodes.pop(0) # Remove Node-1 from the physical cluster
        
        time.sleep(0.350) # Wait for election timeouts to trigger
        
        # Simulate Election Process
        for node in self.nodes:
            if node.check_election_timeout():
                print(f"{node.node_id} detected Leader failure. Starting election for Term {node.term + 1}...")
                vote_request = node.start_election()
                
                # Ask the other node for a vote
                votes = 1 # Voted for self
                for peer in self.nodes:
                    if peer.node_id != node.node_id:
                        if peer.process_vote_request(vote_request["candidate_id"], vote_request["term"]):
                            votes += 1
                            
                # Requires Quorum (majority of remaining cluster)
                if votes > len(self.nodes) / 2:
                    node.become_leader()
                    print(f"SUCCESS: {node.node_id} achieved Quorum ({votes} votes). PetroFlow is back online!")
                    break
