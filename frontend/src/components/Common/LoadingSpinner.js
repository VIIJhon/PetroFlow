import React from 'react';
import { CircularProgress, Box } from '@mui/material';

/**
 * LoadingSpinner Component
 * 
 * Reusable loading spinner with:
 * - Customizable size
 * - Optional centered layout
 * - Color variants
 */
const LoadingSpinner = ({ 
  size = 40, 
  centered = false, 
  color = 'primary',
  sx = {} 
}) => {
  const spinner = (
    <CircularProgress 
      size={size} 
      color={color}
      sx={sx}
    />
  );

  if (centered) {
    return (
      <Box
        sx={{
          display: 'flex',
          justifyContent: 'center',
          alignItems: 'center',
          width: '100%',
          height: '100%',
          minHeight: 200,
        }}
      >
        {spinner}
      </Box>
    );
  }

  return spinner;
};

export default LoadingSpinner;