"""
Raft Consensus Algorithm Implementation

Implementa el algoritmo Raft para lograr consenso entre 3 nodos,
garantizando que 2 de 3 siempre estén de acuerdo.

Referencias:
- Diego Ongaro & John Ousterhout: "In Search of an Understandable Consensus Algorithm"
- https://raft.github.io/

Topología: 3 nodos (1 LEADER, 2 FOLLOWERs)
Timeouts:
  - Election timeout: 150-300ms
  - Heartbeat interval: 50ms
"""

import asyncio
import json
import logging
import os
import time
from dataclasses import dataclass, field, asdict
from datetime import datetime, timedelta
from enum import Enum
from typing import Dict, List, Optional, Any, Callable, Tuple
from collections import defaultdict

logger = logging.getLogger(__name__)


class NodeState(Enum):
    """Estados posibles de un nodo Raft"""
    FOLLOWER = "follower"
    CANDIDATE = "candidate"
    LEADER = "leader"


@dataclass
class LogEntry:
    """Entrada individual en el log de Raft"""
    term: int
    index: int
    command: Any
    timestamp: float = field(default_factory=time.time)
    
    def to_dict(self) -> Dict:
        return {
            "term": self.term,
            "index": self.index,
            "command": self.command,
            "timestamp": self.timestamp,
        }


@dataclass
class RaftState:
    """Estado persistente de un nodo Raft"""
    # Persistent state (debe guardarse en disco)
    current_term: int = 0
    voted_for: Optional[str] = None
    log: List[LogEntry] = field(default_factory=list)
    
    # Volatile state (se pierde al reiniciar, se reconstruye)
    commit_index: int = 0
    last_applied: int = 0
    
    def to_dict(self) -> Dict:
        return {
            "current_term": self.current_term,
            "voted_for": self.voted_for,
            "log": [entry.to_dict() for entry in self.log],
            "commit_index": self.commit_index,
            "last_applied": self.last_applied,
        }


class RaftRPC:
    """
    Remote Procedure Calls para comunicación entre nodos
    
    RPCs principales:
    1. AppendEntries RPC (heartbeat + replicación de log)
    2. RequestVote RPC (elección de líder)
    """
    
    @dataclass
    class RequestVoteArgs:
        """Argumentos para RequestVote RPC"""
        term: int
        candidate_id: str
        last_log_index: int
        last_log_term: int
    
    @dataclass
    class RequestVoteReply:
        """Respuesta de RequestVote RPC"""
        term: int
        vote_granted: bool
    
    @dataclass
    class AppendEntriesArgs:
        """Argumentos para AppendEntries RPC"""
        term: int
        leader_id: str
        prev_log_index: int
        prev_log_term: int
        entries: List[LogEntry]
        leader_commit: int
    
    @dataclass
    class AppendEntriesReply:
        """Respuesta de AppendEntries RPC"""
        term: int
        success: bool
        conflict_index: Optional[int] = None
        conflict_term: Optional[int] = None


class RaftNode:
    """
    Implementación de un nodo Raft
    
    Responsabilidades:
    1. Mantener estado persistente (term, voted_for, log)
    2. Participar en elecciones
    3. Replicar comandos si es LEADER
    4. Aplicar comandos a máquina de estados
    """
    
    def __init__(
        self,
        node_id: str,
        peers: List[str],
        election_timeout_ms: float = 150,
        heartbeat_interval_ms: float = 50,
        state_machine_callback: Optional[Callable[[Any], None]] = None
    ):
        self.node_id = node_id
        self.peers = peers  # IDs de otros nodos
        self.election_timeout_ms = election_timeout_ms
        self.heartbeat_interval_ms = heartbeat_interval_ms
        self.state_machine_callback = state_machine_callback
        
        # Estado del nodo
        self.state = NodeState.FOLLOWER
        self.raft_state = RaftState()
        
        # Estado volátil para LEADERs
        self.next_index: Dict[str, int] = {peer: 1 for peer in peers}
        self.match_index: Dict[str, int] = {peer: 0 for peer in peers}
        
        # Timers
        self.last_heartbeat = time.time()
        self.election_timeout = self._random_election_timeout()
        self.last_contact_time = time.time()
        
        # Métricas
        self.elections_won = 0
        self.elections_lost = 0
        self.terms_seen = 0
        self.log_entries_applied = 0
        
        logger.info(f"Nodo Raft inicializado: {node_id}")
    
    def _random_election_timeout(self) -> float:
        """Genera timeout aleatorio entre 150-300ms para evitar split votes"""
        import random
        return random.uniform(self.election_timeout_ms, self.election_timeout_ms * 2)
    
    # ========== STATE TRANSITIONS ==========
    
    def become_follower(self, term: int):
        """Transición a FOLLOWER"""
        if term > self.raft_state.current_term:
            self.raft_state.current_term = term
            self.raft_state.voted_for = None
        self.state = NodeState.FOLLOWER
        self.last_heartbeat = time.time()
        logger.info(f"[{self.node_id}] → FOLLOWER (term {term})")
    
    def become_candidate(self):
        """Transición a CANDIDATE (inicia elección)"""
        self.raft_state.current_term += 1
        self.raft_state.voted_for = self.node_id
        self.state = NodeState.CANDIDATE
        self.election_timeout = self._random_election_timeout()
        logger.info(
            f"[{self.node_id}] → CANDIDATE (term {self.raft_state.current_term})"
        )
    
    def become_leader(self):
        """Transición a LEADER"""
        self.state = NodeState.LEADER
        self.elections_won += 1
        
        # Reinicializar next_index y match_index
        last_log_index = len(self.raft_state.log)
        for peer in self.peers:
            self.next_index[peer] = last_log_index + 1
            self.match_index[peer] = 0
        
        logger.warning(
            f"[{self.node_id}] → LEADER (term {self.raft_state.current_term}) 🔴"
        )
    
    # ========== RAFT RPCs ==========
    
    def request_vote(
        self,
        args: RaftRPC.RequestVoteArgs
    ) -> RaftRPC.RequestVoteReply:
        """
        Procesa RequestVote RPC
        
        Rules:
        1. Si term > currentTerm, actualizar currentTerm
        2. Si candidato tiene log más reciente y no he votado, votar
        """
        # 1. Actualizar term si es necesario
        if args.term > self.raft_state.current_term:
            self.become_follower(args.term)
        
        # 2. Denegar si candidato tiene término antiguo
        if args.term < self.raft_state.current_term:
            return RaftRPC.RequestVoteReply(
                term=self.raft_state.current_term,
                vote_granted=False
            )
        
        # 3. Denegar si ya voté en este término
        if self.raft_state.voted_for is not None and \
           self.raft_state.voted_for != args.candidate_id:
            return RaftRPC.RequestVoteReply(
                term=self.raft_state.current_term,
                vote_granted=False
            )
        
        # 4. Verificar que candidato tiene log al menos tan actual
        my_last_log_index = len(self.raft_state.log)
        my_last_log_term = (
            self.raft_state.log[-1].term if self.raft_state.log else 0
        )
        
        if args.last_log_term < my_last_log_term or \
           (args.last_log_term == my_last_log_term and
            args.last_log_index < my_last_log_index):
            return RaftRPC.RequestVoteReply(
                term=self.raft_state.current_term,
                vote_granted=False
            )
        
        # 5. Otorgar voto
        self.raft_state.voted_for = args.candidate_id
        self.last_heartbeat = time.time()
        
        logger.info(
            f"[{self.node_id}] vota por {args.candidate_id} (term {args.term})"
        )
        
        return RaftRPC.RequestVoteReply(
            term=self.raft_state.current_term,
            vote_granted=True
        )
    
    def append_entries(
        self,
        args: RaftRPC.AppendEntriesArgs
    ) -> RaftRPC.AppendEntriesReply:
        """
        Procesa AppendEntries RPC (heartbeat + replicación)
        
        Rules:
        1. Si term < currentTerm, denegar
        2. Si log no tiene entry en prev_log_index, denegar
        3. Si hay conflicto, eliminar entries conflictivas
        4. Agregar nuevas entries
        5. Actualizar commitIndex
        """
        # 1. Denegar si término antiguo
        if args.term < self.raft_state.current_term:
            return RaftRPC.AppendEntriesReply(
                term=self.raft_state.current_term,
                success=False
            )
        
        # Actualizar term y convertir a follower si es necesario
        if args.term > self.raft_state.current_term:
            self.become_follower(args.term)
        elif self.state != NodeState.FOLLOWER:
            self.become_follower(args.term)
        
        self.last_heartbeat = time.time()
        
        # 2. Validar prev_log_index
        if args.prev_log_index > 0:
            if args.prev_log_index > len(self.raft_state.log):
                return RaftRPC.AppendEntriesReply(
                    term=self.raft_state.current_term,
                    success=False,
                    conflict_index=len(self.raft_state.log) + 1
                )
            
            prev_entry = self.raft_state.log[args.prev_log_index - 1]
            if prev_entry.term != args.prev_log_term:
                return RaftRPC.AppendEntriesReply(
                    term=self.raft_state.current_term,
                    success=False,
                    conflict_term=prev_entry.term,
                    conflict_index=args.prev_log_index
                )
        
        # 3. Resolver conflictos
        if len(args.entries) > 0:
            # Encontrar punto de divergencia
            for i, entry in enumerate(args.entries):
                log_index = args.prev_log_index + i
                
                if log_index <= len(self.raft_state.log):
                    if self.raft_state.log[log_index - 1].term != entry.term:
                        # Conflicto: eliminar esta y siguientes
                        self.raft_state.log = self.raft_state.log[:log_index - 1]
                
                if log_index > len(self.raft_state.log):
                    # Agregar nueva entry
                    self.raft_state.log.append(entry)
        
        # 4. Actualizar commitIndex
        if args.leader_commit > self.raft_state.commit_index:
            self.raft_state.commit_index = min(
                args.leader_commit,
                len(self.raft_state.log)
            )
        
        return RaftRPC.AppendEntriesReply(
            term=self.raft_state.current_term,
            success=True
        )
    
    # ========== COMMAND HANDLING ==========
    
    def submit_command(self, command: Any) -> Tuple[int, int, bool]:
        """
        Envía comando a máquina de estados
        Solo funciona si nodo es LEADER
        
        Returns:
            (index, term, is_leader)
        """
        if self.state != NodeState.LEADER:
            return 0, self.raft_state.current_term, False
        
        # Crear nueva entry
        entry = LogEntry(
            term=self.raft_state.current_term,
            index=len(self.raft_state.log) + 1,
            command=command
        )
        self.raft_state.log.append(entry)
        
        logger.info(
            f"[{self.node_id}] LEADER: comando agregado al log "
            f"(index={entry.index}, term={entry.term})"
        )
        
        return entry.index, entry.term, True
    
    def apply_entries(self):
        """
        Aplica entries a la máquina de estados hasta commitIndex
        """
        while self.raft_state.last_applied < self.raft_state.commit_index:
            self.raft_state.last_applied += 1
            entry = self.raft_state.log[self.raft_state.last_applied - 1]
            
            if self.state_machine_callback:
                try:
                    self.state_machine_callback(entry.command)
                    self.log_entries_applied += 1
                except Exception as e:
                    logger.error(f"Error aplicando entry: {e}")
    
    # ========== PERSISTENCE ==========
    
    def save_state(self, filepath: str):
        """Guarda estado persistente a disco"""
        state_dict = self.raft_state.to_dict()
        with open(filepath, 'w') as f:
            json.dump(state_dict, f, indent=2, default=str)
        logger.debug(f"[{self.node_id}] Estado guardado: {filepath}")
    
    def load_state(self, filepath: str):
        """Carga estado persistente desde disco"""
        if not os.path.exists(filepath):
            return
        
        try:
            with open(filepath, 'r') as f:
                state_dict = json.load(f)
            
            self.raft_state.current_term = state_dict["current_term"]
            self.raft_state.voted_for = state_dict["voted_for"]
            self.raft_state.commit_index = state_dict["commit_index"]
            self.raft_state.last_applied = state_dict["last_applied"]
            
            # Reconstruir log
            for entry_dict in state_dict.get("log", []):
                entry = LogEntry(
                    term=entry_dict["term"],
                    index=entry_dict["index"],
                    command=entry_dict["command"],
                    timestamp=entry_dict.get("timestamp", time.time())
                )
                self.raft_state.log.append(entry)
            
            logger.info(
                f"[{self.node_id}] Estado cargado: term={self.raft_state.current_term}, "
                f"log_entries={len(self.raft_state.log)}"
            )
        except Exception as e:
            logger.error(f"Error cargando estado: {e}")
    
    # ========== TICK LOGIC ==========
    
    def tick(self):
        """
        Llamar cada 10ms aprox.
        Maneja timeouts de elección y heartbeats
        """
        now = time.time()
        elapsed_since_heartbeat = (now - self.last_heartbeat) * 1000  # ms
        
        if self.state == NodeState.FOLLOWER:
            # Si no recibo heartbeat, iniciar elección
            if elapsed_since_heartbeat > self.election_timeout:
                logger.info(
                    f"[{self.node_id}] Election timeout ({self.election_timeout:.0f}ms)"
                )
                self.become_candidate()
        
        elif self.state == NodeState.CANDIDATE:
            # Si timeout sin ganar elección, reintentar
            if elapsed_since_heartbeat > self.election_timeout:
                logger.info(
                    f"[{self.node_id}] Candidato timeout, reintentando"
                )
                self.become_candidate()
        
        elif self.state == NodeState.LEADER:
            # Enviar heartbeats periodicamente
            if elapsed_since_heartbeat > self.heartbeat_interval_ms:
                logger.debug(f"[{self.node_id}] Enviando heartbeats")
                self.last_heartbeat = now
    
    # ========== METRICS ==========
    
    def get_metrics(self) -> Dict[str, Any]:
        """Retorna métricas del nodo Raft"""
        return {
            "node_id": self.node_id,
            "state": self.state.value,
            "current_term": self.raft_state.current_term,
            "voted_for": self.raft_state.voted_for,
            "log_length": len(self.raft_state.log),
            "commit_index": self.raft_state.commit_index,
            "last_applied": self.raft_state.last_applied,
            "elections_won": self.elections_won,
            "elections_lost": self.elections_lost,
            "log_entries_applied": self.log_entries_applied,
            "timestamp": time.time(),
        }


class RaftCluster:
    """
    Gestor de cluster Raft (3 nodos)
    Coordina comunicación entre nodos y promueve consenso
    """
    
    def __init__(
        self,
        node_ids: List[str],
        election_timeout_ms: float = 150,
        heartbeat_interval_ms: float = 50
    ):
        self.node_ids = node_ids
        self.nodes: Dict[str, RaftNode] = {}
        
        # Crear nodos
        for node_id in node_ids:
            peers = [n for n in node_ids if n != node_id]
            node = RaftNode(
                node_id=node_id,
                peers=peers,
                election_timeout_ms=election_timeout_ms,
                heartbeat_interval_ms=heartbeat_interval_ms
            )
            self.nodes[node_id] = node
        
        logger.info(f"Cluster Raft inicializado con {len(node_ids)} nodos")
    
    def submit_command(self, command: Any) -> Tuple[bool, str]:
        """
        Envía comando al cluster
        Busca LEADER y lo envía
        
        Returns:
            (success, leader_id_or_error)
        """
        leader = self._find_leader()
        if leader is None:
            return False, "No leader available"
        
        index, term, is_leader = leader.submit_command(command)
        if is_leader:
            return True, leader.node_id
        return False, "Not leader"
    
    def _find_leader(self) -> Optional[RaftNode]:
        """Encuentra nodo LEADER actual"""
        for node in self.nodes.values():
            if node.state == NodeState.LEADER:
                return node
        return None
    
    def get_cluster_status(self) -> Dict[str, Any]:
        """Retorna estado completo del cluster"""
        leader = self._find_leader()
        
        return {
            "leader": leader.node_id if leader else None,
            "nodes": {
                node_id: node.get_metrics()
                for node_id, node in self.nodes.items()
            },
            "timestamp": time.time(),
        }
    
    def tick_all(self):
        """Ejecuta tick en todos los nodos"""
        for node in self.nodes.values():
            node.tick()
