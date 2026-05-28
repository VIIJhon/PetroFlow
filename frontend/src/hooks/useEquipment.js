import { useSelector, useDispatch } from 'react-redux';
import { useCallback, useEffect } from 'react';
import {
  fetchEquipmentList,
  fetchEquipmentById,
  createEquipment,
  updateEquipment,
  deleteEquipment,
  setFilters,
  clearSelectedEquipment,
} from '../store/slices/equipmentSlice';

/**
 * useEquipment Hook
 * 
 * Custom hook for equipment operations
 * 
 * Parameters:
 * - autoLoad: Automatically load equipment list on mount (default: false)
 * 
 * Returns:
 * - equipmentList: Array of equipment
 * - selectedEquipment: Currently selected equipment
 * - loading: Loading state
 * - error: Error message
 * - pagination: Pagination info
 * - filters: Current filters
 * - fetchList: Fetch equipment list function
 * - fetchById: Fetch equipment by ID function
 * - create: Create equipment function
 * - update: Update equipment function
 * - remove: Delete equipment function
 * - setFilters: Set filters function
 * - clearSelected: Clear selected equipment function
 */
const useEquipment = (autoLoad = false) => {
  const dispatch = useDispatch();
  const {
    equipmentList,
    selectedEquipment,
    loading,
    error,
    pagination,
    filters,
  } = useSelector((state) => state.equipment);

  // Fetch equipment list
  const fetchList = useCallback(
    async (options = {}) => {
      try {
        const result = await dispatch(
          fetchEquipmentList({
            page: options.page || pagination.page,
            pageSize: options.pageSize || pagination.pageSize,
            filters: options.filters || filters,
          })
        ).unwrap();
        return { success: true, data: result };
      } catch (err) {
        return { success: false, error: err };
      }
    },
    [dispatch, pagination.page, pagination.pageSize, filters]
  );

  // Fetch equipment by ID
  const fetchById = useCallback(
    async (id) => {
      try {
        const result = await dispatch(fetchEquipmentById(id)).unwrap();
        return { success: true, data: result };
      } catch (err) {
        return { success: false, error: err };
      }
    },
    [dispatch]
  );

  // Create equipment
  const create = useCallback(
    async (equipmentData) => {
      try {
        const result = await dispatch(createEquipment(equipmentData)).unwrap();
        return { success: true, data: result };
      } catch (err) {
        return { success: false, error: err };
      }
    },
    [dispatch]
  );

  // Update equipment
  const update = useCallback(
    async (id, equipmentData) => {
      try {
        const result = await dispatch(
          updateEquipment({ id, data: equipmentData })
        ).unwrap();
        return { success: true, data: result };
      } catch (err) {
        return { success: false, error: err };
      }
    },
    [dispatch]
  );

  // Delete equipment
  const remove = useCallback(
    async (id) => {
      try {
        await dispatch(deleteEquipment(id)).unwrap();
        return { success: true };
      } catch (err) {
        return { success: false, error: err };
      }
    },
    [dispatch]
  );

  // Update filters
  const updateFilters = useCallback(
    (newFilters) => {
      dispatch(setFilters(newFilters));
    },
    [dispatch]
  );

  // Clear selected equipment
  const clearSelected = useCallback(() => {
    dispatch(clearSelectedEquipment());
  }, [dispatch]);

  // Auto-load equipment list on mount
  useEffect(() => {
    if (autoLoad) {
      fetchList();
    }
  }, [autoLoad]); // Only run on mount

  return {
    equipmentList,
    selectedEquipment,
    loading,
    error,
    pagination,
    filters,
    fetchList,
    fetchById,
    create,
    update,
    remove,
    setFilters: updateFilters,
    clearSelected,
  };
};

export default useEquipment;