import React from 'react';
import { Card as MuiCard, CardContent, CardHeader, CardActions } from '@mui/material';

/**
 * Card Component
 * 
 * Reusable card container with:
 * - Optional header with title and actions
 * - Content area
 * - Optional footer actions
 * - Customizable styling
 */
const Card = ({
  title,
  subtitle,
  headerAction,
  children,
  actions,
  elevation = 1,
  sx = {},
  ...props
}) => {
  return (
    <MuiCard elevation={elevation} sx={sx} {...props}>
      {(title || headerAction) && (
        <CardHeader
          title={title}
          subheader={subtitle}
          action={headerAction}
        />
      )}
      
      <CardContent>{children}</CardContent>
      
      {actions && <CardActions>{actions}</CardActions>}
    </MuiCard>
  );
};

export default Card;