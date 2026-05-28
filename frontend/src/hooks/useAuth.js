import { useSelector, useDispatch } from 'react-redux';
import { useCallback } from 'react';
import { login, logout, checkAuthStatus } from '../store/slices/authSlice';

/**
 * useAuth Hook
 * 
 * Custom hook for authentication operations
 * 
 * Returns:
 * - user: Current user object
 * - isAuthenticated: Boolean authentication status
 * - loading: Loading state
 * - error: Error message
 * - login: Login function
 * - logout: Logout function
 * - checkAuth: Check authentication status function
 */
const useAuth = () => {
  const dispatch = useDispatch();
  const { user, isAuthenticated, loading, error } = useSelector((state) => state.auth);

  const handleLogin = useCallback(
    async (credentials) => {
      try {
        const result = await dispatch(login(credentials)).unwrap();
        return { success: true, data: result };
      } catch (err) {
        return { success: false, error: err };
      }
    },
    [dispatch]
  );

  const handleLogout = useCallback(async () => {
    try {
      await dispatch(logout()).unwrap();
      return { success: true };
    } catch (err) {
      return { success: false, error: err };
    }
  }, [dispatch]);

  const checkAuth = useCallback(async () => {
    try {
      const result = await dispatch(checkAuthStatus()).unwrap();
      return { success: true, data: result };
    } catch (err) {
      return { success: false, error: err };
    }
  }, [dispatch]);

  return {
    user,
    isAuthenticated,
    loading,
    error,
    login: handleLogin,
    logout: handleLogout,
    checkAuth,
  };
};

export default useAuth;