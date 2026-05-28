import React from 'react';
import { Button as MuiButton } from '@mui/material';
import LoadingSpinner from './LoadingSpinner';

/**
 * Button Component
 * 
 * Enhanced button with:
 * - Loading state
 * - Disabled state
 * - Icon support
 * - All Material-UI button variants
 */
const Button = ({
  children,
  loading = false,
  disabled = false,
  startIcon,
  endIcon,
  ...props
}) => {
  return (
    <MuiButton
      disabled={disabled || loading}
      startIcon={loading ? <LoadingSpinner size={20} /> : startIcon}
      endIcon={!loading && endIcon}
      {...props}
    >
      {children}
    </MuiButton>
  );
};

export default Button;