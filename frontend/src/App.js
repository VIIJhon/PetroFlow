import React, { useEffect } from 'react';
import { Routes, Route, Navigate } from 'react-router-dom';
import { useDispatch, useSelector } from 'react-redux';
import { Box } from '@mui/material';

// Layout Components
import MainLayout from './components/Layout/MainLayout';
import PrivateRoute from './components/Auth/PrivateRoute';

// Page Components — Core
import Login from './pages/Login';
import Dashboard from './pages/Dashboard';
import ProcessDesigner from './pages/ProcessDesigner/ProcessDesigner';

// Equipment
import EquipmentList from './pages/Equipment/EquipmentList';
import EquipmentDetail from './pages/Equipment/EquipmentDetail';

// Simulation
import SimulationList from './pages/Simulation/SimulationList';

// Analysis Hub + Modulos
import AnalysisDashboard from './pages/Analysis/AnalysisDashboard';
import HistoricalAnalysis from './pages/Analysis/HistoricalAnalysis';
import SpectralAnalysis from './pages/Analysis/SpectralAnalysis';
import ThermalAnalysis from './pages/Analysis/ThermalAnalysis';
import NetworkAnalysis from './pages/Analysis/NetworkAnalysis';
import MultiphaseFlow from './pages/Analysis/MultiphaseFlow';
import CausalDiagnosis from './pages/Analysis/CausalDiagnosis';
import OperationalOptimizer from './pages/Analysis/OperationalOptimizer';
import PrescriptiveActions from './pages/Analysis/PrescriptiveActions';
import DeclineAnalysis from './pages/Analysis/DeclineAnalysis';
import GeminiAnalysis from './pages/Analysis/GeminiAnalysis';
import ArtificialLift from './pages/Analysis/ArtificialLift';
import DigitalTwin from './pages/Analysis/DigitalTwin';

// Modulos secundarios
import MonteCarloAnalysis from './pages/Risk/MonteCarloAnalysis';
import FMEAAnalysis from './pages/Risk/FMEAAnalysis';
import FaultTreeAnalysis from './pages/Risk/FaultTreeAnalysis';
import RULAnalysis from './pages/Risk/RULAnalysis';
import MLOpsPage from './pages/MLOps/MLOpsPage';
import ComplianceAudit from './pages/Compliance/ComplianceAudit';
import CybersecurityDashboard from './pages/Compliance/CybersecurityDashboard';
import OperatorFeedback from './pages/Feedback/OperatorFeedback';
import ExternalIntegration from './pages/Integration/ExternalIntegration';

// Redux Actions
import { checkAuthStatus } from './store/slices/authSlice';

// Utilities
import LoadingSpinner from './components/Common/LoadingSpinner';

/**
 * Root Application Component — PetroFlow v3.0
 *
 * Shell de software de ingenieria de proceso.
 * Gestiona el enrutamiento por vista (activeView en Redux)
 * y aplica el nuevo MainLayout con WorkspaceNav + TopBar + StatusBar.
 */
function App() {
  const dispatch = useDispatch();
  const { isAuthenticated, loading } = useSelector((state) => state.auth);
  const activeView = useSelector((state) => state.ui.activeView);

  useEffect(() => {
    dispatch(checkAuthStatus());
  }, [dispatch]);

  if (loading) {
    return (
      <Box
        sx={{
          display: 'flex',
          justifyContent: 'center',
          alignItems: 'center',
          height: '100vh',
        }}
      >
        <LoadingSpinner size={60} />
      </Box>
    );
  }

  // Componente según la vista activa en Redux
  let viewComponent;
  switch (activeView) {
    // ── DISEÑO ──────────────────────────────────────────────────────────
    case 'dashboard':
      viewComponent = <Dashboard />;
      break;
    case 'processDesigner':
      viewComponent = <ProcessDesigner />;
      break;
    case 'equipment':
      viewComponent = <EquipmentList />;
      break;
    case 'equipmentDetail':
      viewComponent = <EquipmentDetail />;
      break;
    case 'lineList':
      viewComponent = <EquipmentList />;
      break;
    case 'library':
      viewComponent = <ComplianceAudit />;
      break;

    // ── SIMULAR ─────────────────────────────────────────────────────────
    case 'simulations':
      viewComponent = <SimulationList />;
      break;
    case 'multiphase':
      viewComponent = <MultiphaseFlow />;
      break;
    case 'thermal':
      viewComponent = <ThermalAnalysis />;
      break;

    // ── ANALIZAR ────────────────────────────────────────────────────────
    case 'historical':
      viewComponent = <HistoricalAnalysis />;
      break;
    case 'decline':
      viewComponent = <DeclineAnalysis />;
      break;
    case 'spectral':
      viewComponent = <SpectralAnalysis />;
      break;
    case 'network':
      viewComponent = <NetworkAnalysis />;
      break;
    case 'causal':
      viewComponent = <CausalDiagnosis />;
      break;
    case 'optimizer':
      viewComponent = <OperationalOptimizer />;
      break;
    case 'gemini':
      viewComponent = <GeminiAnalysis />;
      break;
    case 'artificialLift':
      viewComponent = <ArtificialLift />;
      break;
    case 'digitalTwin':
      viewComponent = <DigitalTwin />;
      break;
    case 'mlops':
      viewComponent = <MLOpsPage />;
      break;

    // ── RIESGO ──────────────────────────────────────────────────────────
    case 'fmea':
      viewComponent = <FMEAAnalysis />;
      break;
    case 'fta':
      viewComponent = <FaultTreeAnalysis />;
      break;
    case 'rul':
      viewComponent = <RULAnalysis />;
      break;
    case 'monteCarlo':
      viewComponent = <MonteCarloAnalysis />;
      break;

    // ── OPERAR ──────────────────────────────────────────────────────────
    case 'monitoring':
      viewComponent = <Dashboard />;
      break;
    case 'maintenance':
      viewComponent = <SimulationList />;
      break;
    case 'compliance':
      viewComponent = <ComplianceAudit />;
      break;
    case 'cybersecurity':
      viewComponent = <CybersecurityDashboard />;
      break;
    case 'integration':
      viewComponent = <ExternalIntegration />;
      break;
    case 'feedback':
      viewComponent = <OperatorFeedback />;
      break;

    default:
      viewComponent = <Dashboard />;
  }

  if (!isAuthenticated) {
    return <Login />;
  }

  return (
    <MainLayout>
      {viewComponent}
    </MainLayout>
  );
}

export default App;