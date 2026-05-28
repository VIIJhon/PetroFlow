"""
Tests para Phase 15 - Validación de componentes aeroespaciales

Prueba:
1. ECDSA signature generation/verification
2. Raft consensus voting y failover
3. Ring buffer lock-free operations
4. PINN physics constraints satisfaction
5. Sistema integrado end-to-end
"""

import pytest
import json
import time
import numpy as np
from unittest.mock import Mock, patch

# Importar componentes Phase 15
from core.zero_trust_security import (
    PKIManager, ECDSASignatureEngine, ZeroTrustDataValidator,
    SecurityLevel, SignatureMetadata
)
from core.raft_consensus import RaftCluster, NodeState, RaftRPC
from core.shared_memory_ipc import RingBuffer, SensorSample
from core.pinn_engine import PINNConfig, PINNTrainer, PhysicsConstraint
from core.phase15_integration import Phase15System, create_3_node_cluster


class TestECDSASecurity:
    """Pruebas de seguridad ECDSA"""
    
    def test_certificate_generation(self):
        """Verifica generación de certificados"""
        pki = PKIManager(SecurityLevel.PRODUCTION)
        
        root_cert = pki.create_root_certificate("PetroFlow CA")
        assert root_cert is not None
        assert root_cert.level.value == "root"
        assert "PetroFlow CA" in root_cert.name
    
    def test_sensor_certificate_signing(self):
        """Verifica firma de certificados de sensor"""
        pki = PKIManager(SecurityLevel.PRODUCTION)
        pki.create_root_certificate("Root CA")
        
        sensor_cert = pki.create_sensor_certificate("sensor-001", "Root CA")
        assert sensor_cert is not None
        assert "sensor-001" in sensor_cert.name
    
    def test_ecdsa_signature_verification(self):
        """Verifica proceso de firma/verificación ECDSA"""
        pki = PKIManager(SecurityLevel.PRODUCTION)
        pki.create_root_certificate("Root CA")
        pki.create_sensor_certificate("sensor-001", "Root CA")
        
        ecdsa = ECDSASignatureEngine(pki)
        
        # Firmar datos
        data = {"pressure": 100, "velocity": 5.0}
        signature, metadata = ecdsa.sign_data(data, "sensor-001")
        
        # Verificar firma
        is_valid = ecdsa.verify_signature(data, signature, metadata, "sensor-001")
        assert is_valid is True
    
    def test_signature_rejection_on_tampered_data(self):
        """Verifica rechazo de datos modificados"""
        pki = PKIManager(SecurityLevel.PRODUCTION)
        pki.create_root_certificate("Root CA")
        pki.create_sensor_certificate("sensor-001", "Root CA")
        
        ecdsa = ECDSASignatureEngine(pki)
        
        data = {"pressure": 100}
        signature, metadata = ecdsa.sign_data(data, "sensor-001")
        
        # Modificar datos
        tampered_data = {"pressure": 200}
        is_valid = ecdsa.verify_signature(tampered_data, signature, metadata, "sensor-001")
        assert is_valid is False
    
    def test_rate_limiting(self):
        """Verifica rate limiting en validador"""
        pki = PKIManager(SecurityLevel.PRODUCTION)
        pki.create_root_certificate("Root CA")
        pki.create_sensor_certificate("sensor-001", "Root CA")
        
        ecdsa = ECDSASignatureEngine(pki)
        validator = ZeroTrustDataValidator(ecdsa, max_packets_per_second=10)
        
        # Firmar datos
        data = {"pressure": 100, "temperature": 25}
        signature, metadata = ecdsa.sign_data(data, "sensor-001")
        
        # Intentar enviar 15 paquetes en 1 segundo
        rejected_count = 0
        for _ in range(15):
            is_valid, reason = validator.validate_sensor_reading(
                data, "sensor-001", signature, metadata
            )
            if not is_valid:
                rejected_count += 1
        
        assert rejected_count > 0  # Al menos algunos rechazados por rate limit


class TestRaftConsensus:
    """Pruebas de consenso Raft"""
    
    def test_cluster_initialization(self):
        """Verifica inicialización del cluster"""
        cluster = RaftCluster(["node1", "node2", "node3"])
        assert len(cluster.nodes) == 3
        assert all(node.state == NodeState.FOLLOWER for node in cluster.nodes.values())
    
    def test_election_timeout_triggers_candidacy(self):
        """Verifica que timeout de elección inicia candidatura"""
        cluster = RaftCluster(["node1", "node2", "node3"])
        node = cluster.nodes["node1"]
        
        # Esperar a que election timeout se alcance
        node.election_timeout = 0.001  # 1ms para test
        node.last_heartbeat = time.time() - 1  # Simular 1s sin heartbeat
        
        node.tick()
        # Debería haber iniciado elección
        assert node.state in [NodeState.CANDIDATE, NodeState.LEADER]
    
    def test_request_vote_rpc(self):
        """Verifica RequestVote RPC"""
        cluster = RaftCluster(["node1", "node2", "node3"])
        
        node1 = cluster.nodes["node1"]
        node2 = cluster.nodes["node2"]
        
        # node2 solicita voto a node1
        args = RaftRPC.RequestVoteArgs(
            term=1,
            candidate_id="node2",
            last_log_index=0,
            last_log_term=0
        )
        
        reply = node1.request_vote(args)
        assert reply.term == 1
        assert reply.vote_granted is True
    
    def test_append_entries_replication(self):
        """Verifica replicación de entries mediante AppendEntries"""
        cluster = RaftCluster(["node1", "node2", "node3"])
        
        leader = cluster.nodes["node1"]
        follower = cluster.nodes["node2"]
        
        # Simular que node1 es LEADER
        leader.state = NodeState.LEADER
        
        # Enviar comando
        index, term, is_leader = leader.submit_command({"action": "critical"})
        assert is_leader is True
        assert len(leader.raft_state.log) == 1
    
    def test_leader_failover(self):
        """Simula failover de líder"""
        cluster = RaftCluster(["node1", "node2", "node3"])
        
        leader = cluster.nodes["node1"]
        leader.state = NodeState.LEADER
        
        # Simular caída del líder (no envía heartbeats)
        leader.last_heartbeat = time.time() - 1000
        
        # Otros nodos deberían iniciar elección
        for node_id in ["node2", "node3"]:
            node = cluster.nodes[node_id]
            node.last_heartbeat = time.time() - 1000
            node.tick()
        
        # Al menos uno debería ser candidato
        states = [node.state for node in cluster.nodes.values()]
        assert NodeState.CANDIDATE in states or NodeState.LEADER in states


class TestSharedMemoryIPC:
    """Pruebas de shared memory IPC"""
    
    def test_ring_buffer_write_read(self):
        """Verifica escritura/lectura de ring buffer"""
        # Usar nombre único para test
        rb = RingBuffer("test_ring_buffer")
        
        # Crear muestra
        sample = SensorSample(
            timestamp=time.time(),
            sensor_id="test-sensor",
            channel=0,
            value=42.5
        )
        
        # Escribir
        success = rb.write(sample)
        assert success is True
        
        # Leer
        samples = rb.read_latest()
        assert len(samples) == 1
        assert samples[0].value == 42.5
        
        rb.close()
    
    def test_ring_buffer_circular_behavior(self):
        """Verifica comportamiento circular del buffer"""
        rb = RingBuffer("test_circular_buffer")
        
        # Escribir varias muestras
        for i in range(5):
            sample = SensorSample(
                timestamp=time.time(),
                sensor_id=f"sensor-{i}",
                channel=0,
                value=float(i)
            )
            rb.write(sample)
        
        # Leer todas
        samples = rb.read_latest()
        assert len(samples) == 5
        values = [s.value for s in samples]
        assert values == [0.0, 1.0, 2.0, 3.0, 4.0]
        
        rb.close()
    
    def test_buffer_status_metrics(self):
        """Verifica métricas de estado del buffer"""
        rb = RingBuffer("test_metrics_buffer")
        
        status = rb.get_status()
        assert "pending_samples" in status
        assert "buffer_size_mb" in status
        assert status["buffer_size_mb"] == 10
        
        rb.close()


class TestPINNPhysicsConstraints:
    """Pruebas de PINNs con restricciones físicas"""
    
    def test_pinn_model_creation(self):
        """Verifica creación de modelo PINN"""
        config = PINNConfig(input_size=4, output_size=3)
        trainer = PINNTrainer(config)
        
        assert trainer.model is not None
        assert trainer.loss_calculator is not None
    
    def test_pinn_prediction_physically_valid(self):
        """Verifica que predicciones son físicamente válidas"""
        config = PINNConfig(
            input_size=4,
            output_size=3,
            enabled_constraints=[
                PhysicsConstraint.NAVIER_STOKES,
                PhysicsConstraint.CONTINUITY,
            ]
        )
        trainer = PINNTrainer(config)
        
        # Datos de entrada
        x = np.array([[0.0, 0.0, 100.0, 5.0]])  # (x, t, p, u)
        predictions = trainer.model.predict(x)
        
        # Verificar salida
        assert predictions.shape == (1, 3)
        pressure, velocity, temperature = predictions[0]
        
        # Restricciones físicas: presión y temperatura positivas
        assert pressure >= 0, "Pressure must be non-negative"
        assert temperature >= -273.15, "Temperature must be above absolute zero"
    
    def test_pinn_training_with_physics_loss(self):
        """Verifica entrenamiento con pérdida de física"""
        config = PINNConfig(
            input_size=4,
            output_size=3,
            epochs=5,
            physics_loss_weight=1.0,
            enabled_constraints=[PhysicsConstraint.NAVIER_STOKES]
        )
        trainer = PINNTrainer(config)
        
        # Generar datos sintéticos
        x_train = np.random.rand(50, 4)
        y_train = np.random.rand(50, 3)
        
        # Entrenar
        history = trainer.train(x_train, y_train, verbose=False)
        
        # Verificar que pérdida disminuye
        assert len(history["train_loss"]) == 5
        assert history["train_loss"][0] > history["train_loss"][-1]


class TestPhase15Integration:
    """Pruebas de integración Phase 15"""
    
    def test_system_initialization(self):
        """Verifica inicialización del sistema Phase 15"""
        system = Phase15System(
            "petroflow-node1",
            ["petroflow-node2", "petroflow-node3"],
            SecurityLevel.PRODUCTION
        )
        
        assert system.node_id == "petroflow-node1"
        assert system.status.value == "healthy"
    
    def test_sensor_reading_injection(self):
        """Verifica inyección de lectura de sensor"""
        system = Phase15System(
            "petroflow-node1",
            ["petroflow-node2", "petroflow-node3"]
        )
        
        # Crear sensor en PKI
        system.pki_manager.create_root_certificate("Root")
        system.pki_manager.create_sensor_certificate("sensor-001", "Root")
        
        # Firmar datos
        data = {"pressure": 100, "velocity": 5.0, "temperature": 25}
        signature, metadata = system.ecdsa_engine.sign_data(data, "sensor-001")
        
        # Inyectar lectura
        accepted, reason = system.inject_sensor_reading(
            "sensor-001", 100, 5.0, 25, signature, metadata
        )
        
        assert accepted is True
    
    def test_alarm_generation_with_consensus(self):
        """Verifica generación de alarma con consenso"""
        system = Phase15System(
            "petroflow-node1",
            ["petroflow-node2", "petroflow-node3"]
        )
        
        alarm = system.raise_alarm(
            "sensor-001",
            "pressure_surge",
            "critical",
            "Pressure exceeded 150 PSI",
            consensus_required=True
        )
        
        assert alarm.sensor_id == "sensor-001"
        assert alarm.severity == "critical"
        assert system.alarms_generated == 1
    
    def test_3_node_cluster_creation(self):
        """Verifica creación de cluster de 3 nodos"""
        nodes = create_3_node_cluster(SecurityLevel.PRODUCTION)
        
        assert len(nodes) == 3
        assert all(node.status.value == "healthy" for node in nodes.values())
    
    def test_system_metrics_collection(self):
        """Verifica recolección de métricas"""
        system = Phase15System(
            "petroflow-node1",
            ["petroflow-node2", "petroflow-node3"]
        )
        
        metrics = system.get_system_metrics()
        
        assert "node_id" in metrics
        assert "status" in metrics
        assert "raft" in metrics
        assert "security" in metrics
        assert "ring_buffer" in metrics


class TestSecurityAttackDetection:
    """Pruebas de detección de ataques (Stuxnet-style)"""
    
    def test_falsified_sensor_injection_detection(self):
        """Verifica detección de inyección de datos falsificados"""
        system = Phase15System(
            "petroflow-node1",
            ["petroflow-node2", "petroflow-node3"]
        )
        
        system.pki_manager.create_root_certificate("Root")
        system.pki_manager.create_sensor_certificate("sensor-001", "Root")
        
        # Enviar datos con signature falsa
        fake_signature = "00" * 64
        fake_metadata = SignatureMetadata(
            timestamp=time.time(),
            nonce="fake-nonce"
        )
        
        accepted, reason = system.inject_sensor_reading(
            "sensor-001", 100, 5.0, 25, fake_signature, fake_metadata
        )
        
        assert accepted is False
        assert system.security_events > 0
    
    def test_physical_constraint_violation_detection(self):
        """Verifica detección de violación de restricciones físicas"""
        pki = PKIManager(SecurityLevel.PRODUCTION)
        pki.create_root_certificate("Root")
        pki.create_sensor_certificate("sensor-001", "Root")
        
        ecdsa = ECDSASignatureEngine(pki)
        validator = ZeroTrustDataValidator(ecdsa)
        
        # Datos que violan restricciones físicas
        data = {"pressure": 1000, "temperature": 500}  # Temperatura imposible
        signature, metadata = ecdsa.sign_data(data, "sensor-001")
        
        is_valid, reason = validator.validate_sensor_reading(
            data, "sensor-001", signature, metadata
        )
        
        assert is_valid is False
        assert "Physical constraint" in reason


# ========== INTEGRATION TESTS ==========

class TestEnd2EndIntegration:
    """Pruebas end-to-end del sistema completo"""
    
    def test_full_system_lifecycle(self):
        """Prueba ciclo de vida completo del sistema"""
        # 1. Crear cluster
        nodes = create_3_node_cluster()
        
        # 2. Verificar salud inicial
        for node in nodes.values():
            assert node.status.value == "healthy"
        
        # 3. Ejecutar ticks RTOS
        for _ in range(10):
            for node in nodes.values():
                node.run_tick()
        
        # 4. Recolectar métricas
        for node_id, node in nodes.items():
            metrics = node.get_system_metrics()
            assert metrics["node_id"] == node_id
        
        # 5. Shutdown
        for node in nodes.values():
            node.shutdown()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
