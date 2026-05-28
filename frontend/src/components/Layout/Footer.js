import React from 'react';
import { Box, Typography, Link } from '@mui/material';

/**
 * Footer Component
 * 
 * Application footer with:
 * - Copyright information
 * - Links to documentation
 * - Version information
 */
const Footer = () => {
  const currentYear = new Date().getFullYear();

  return (
    <Box
      component="footer"
      sx={{
        py: 2,
        px: 3,
        mt: 'auto',
        backgroundColor: (theme) =>
          theme.palette.mode === 'light'
            ? theme.palette.grey[200]
            : theme.palette.grey[800],
        borderTop: (theme) => `1px solid ${theme.palette.divider}`,
      }}
    >
      <Box
        sx={{
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center',
          flexWrap: 'wrap',
        }}
      >
        <Typography variant="body2" color="text.secondary">
          © {currentYear} Industrial Equipment Platform. All rights reserved.
        </Typography>

        <Box sx={{ display: 'flex', gap: 2 }}>
          <Link
            href="/docs"
            variant="body2"
            color="text.secondary"
            underline="hover"
          >
            Documentation
          </Link>
          <Link
            href="/support"
            variant="body2"
            color="text.secondary"
            underline="hover"
          >
            Support
          </Link>
          <Link
            href="/privacy"
            variant="body2"
            color="text.secondary"
            underline="hover"
          >
            Privacy Policy
          </Link>
        </Box>
      </Box>
    </Box>
  );
};

export default Footer;