import { useSelector, useDispatch } from 'react-redux';
import { useCallback, useEffect } from 'react';
import {
  fetchSimulations,
  fetchSimulationById,
  createSimulation,
  startSimulation,
  stopSimulation,
  pauseSimulation,
  fetchSimulationResults,
  deleteSimulation,
  clearActiveSimulation,
} from '../store/slices/simulationSlice';

/**
 * useSimulation Hook
 * 
 * Custom hook for simulation operations
 * 
 * Parameters:
 * - autoLoad: Automatically load simulations on mount (default: false)
 * 
 * Returns:
 * - simulations: Array of simulations
 * - activeSimulation: Currently active simulation
 * - simulationResults: Results of active simulation
 * - loading: Loading state
 * - error: Error message
 * - status: Simulation status (idle, running, paused, completed, failed)
 * - fetchList: Fetch simulations function
 * - fetchById: Fetch simulation by ID function
 * - create: Create simulation function
 * - start: Start simulation function
 * - stop: Stop simulation function
 * - pause: Pause simulation function
 * - fetchResults: Fetch simulation results function
 * - remove: Delete simulation function
 * - clearActive: Clear active simulation function
 */
const useSimulation = (autoLoad = false) => {
  const dispatch = useDispatch();
  const {
    simulations,
    activeSimulation,
    simulationResults,
    loading,
    error,
    status,
  } = useSelector((state) => state.simulation);

  // Fetch simulations list
  const fetchList = useCallback(async () => {
    try {
      const result = await dispatch(fetchSimulations()).unwrap();
      return { success: true, data: result };
    } catch (err) {
      return { success: false, error: err };
    }
  }, [dispatch]);

  // Fetch simulation by ID
  const fetchById = useCallback(
    async (id) => {
      try {
        const result = await dispatch(fetchSimulationById(id)).unwrap();
        return { success: true, data: result };
      } catch (err) {
        return { success: false, error: err };
      }
    },
    [dispatch]
  );

  // Create simulation
  const create = useCallback(
    async (simulationData) => {
      try {
        const result = await dispatch(createSimulation(simulationData)).unwrap();
        return { success: true, data: result };
      } catch (err) {
        return { success: false, error: err };
      }
    },
    [dispatch]
  );

  // Start simulation
  const start = useCallback(
    async (id) => {
      try {
        const result = await dispatch(startSimulation(id)).unwrap();
        return { success: true, data: result };
      } catch (err) {
        return { success: false, error: err };
      }
    },
    [dispatch]
  );

  // Stop simulation
  const stop = useCallback(
    async (id) => {
      try {
        const result = await dispatch(stopSimulation(id)).unwrap();
        return { success: true, data: result };
      } catch (err) {
        return { success: false, error: err };
      }
    },
    [dispatch]
  );

  // Pause simulation
  const pause = useCallback(
    async (id) => {
      try {
        const result = await dispatch(pauseSimulation(id)).unwrap();
        return { success: true, data: result };
      } catch (err) {
        return { success: false, error: err };
      }
    },
    [dispatch]
  );

  // Fetch simulation results
  const fetchResults = useCallback(
    async (id) => {
      try {
        const result = await dispatch(fetchSimulationResults(id)).unwrap();
        return { success: true, data: result };
      } catch (err) {
        return { success: false, error: err };
      }
    },
    [dispatch]
  );

  // Delete simulation
  const remove = useCallback(
    async (id) => {
      try {
        await dispatch(deleteSimulation(id)).unwrap();
        return { success: true };
      } catch (err) {
        return { success: false, error: err };
      }
    },
    [dispatch]
  );

  // Clear active simulation
  const clearActive = useCallback(() => {
    dispatch(clearActiveSimulation());
  }, [dispatch]);

  // Auto-load simulations on mount
  useEffect(() => {
    if (autoLoad) {
      fetchList();
    }
  }, [autoLoad]); // Only run on mount

  return {
    simulations,
    activeSimulation,
    simulationResults,
    loading,
    error,
    status,
    fetchList,
    fetchById,
    create,
    start,
    stop,
    pause,
    fetchResults,
    remove,
    clearActive,
  };
};

export default useSimulation;