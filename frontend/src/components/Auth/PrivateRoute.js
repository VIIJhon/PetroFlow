import React from 'react';
import { Navigate } from 'react-router-dom';
import { useSelector } from 'react-redux';
import { Box } from '@mui/material';
import LoadingSpinner from '../Common/LoadingSpinner';

/**
 * PrivateRoute Component
 * 
 * Protected route wrapper that:
 * - Checks authentication status
 * - Redirects to login if not authenticated
 * - Shows loading state while checking auth
 * - Optionally checks user roles/permissions
 */
const PrivateRoute = ({ children, requiredRole = null }) => {
  const { isAuthenticated, loading, user } = useSelector((state) => state.auth);

  // Show loading spinner while checking authentication
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

  // Redirect to login if not authenticated
  if (!isAuthenticated) {
    return <Navigate to="/login" replace />;
  }

  // Check role-based access if required
  if (requiredRole && user?.role !== requiredRole) {
    return (
      <Box
        sx={{
          display: 'flex',
          justifyContent: 'center',
          alignItems: 'center',
          height: '100vh',
          flexDirection: 'column',
          gap: 2,
        }}
      >
        <h1>Access Denied</h1>
        <p>You do not have permission to access this page.</p>
      </Box>
    );
  }

  // Render protected content
  return children;
};

export default PrivateRoute;