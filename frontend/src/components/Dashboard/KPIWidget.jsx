import React, { useState, useEffect } from 'react';
import PropTypes from 'prop-types';
import {
  Box,
  Typography,
  Skeleton,
  alpha,
  useTheme,
} from '@mui/material';
import {
  TrendingUp,
  TrendingDown,
  TrendingFlat,
} from '@mui/icons-material';
import {
  LineChart,
  Line,
  ResponsiveContainer,
} from 'recharts';

/**
 * KPIWidget Component
 * 
 * Enhanced KPI card with:
 * - Animated value transitions
 * - Trend indicators (up/down/stable)
 * - Optional sparkline mini-chart
 * - Loading skeleton state
 */
const KPIWidget = ({
  label,
  value,
  unit,
  icon: Icon,
  color,
  trend,
  trendValue,
  sparklineData,
  loading = false,
}) => {
  const theme = useTheme();
  const [displayValue, setDisplayValue] = useState(0);
  const [isAnimating, setIsAnimating] = useState(false);

  // Animate value changes
  useEffect(() => {
    if (loading || value === undefined || value === null) return;

    const numericValue = typeof value === 'number' ? value : parseFloat(value);
    if (isNaN(numericValue)) {
      setDisplayValue(value);
      return;
    }

    setIsAnimating(true);
    const startValue = displayValue;
    const endValue = numericValue;
    const duration = 800; // Animation duration in ms
    const startTime = Date.now();

    const animate = () => {
      const elapsed = Date.now() - startTime;
      const progress = Math.min(elapsed / duration, 1);
      
      // Easing function for smooth animation
      const easeOutQuart = 1 - Math.pow(1 - progress, 4);
      const currentValue = startValue + (endValue - startValue) * easeOutQuart;
      
      setDisplayValue(currentValue);

      if (progress < 1) {
        requestAnimationFrame(animate);
      } else {
        setIsAnimating(false);
      }
    };

    requestAnimationFrame(animate);
  }, [value, loading]);

  // Format display value
  const formatValue = (val) => {
    if (typeof val === 'number') {
      return val % 1 === 0 ? val.toFixed(0) : val.toFixed(2);
    }
    return val;
  };

  // Get trend icon and color
  const getTrendIcon = () => {
    switch (trend) {
      case 'up':
        return <TrendingUp sx={{ fontSize: 16, color: theme.palette.success.main }} />;
      case 'down':
        return <TrendingDown sx={{ fontSize: 16, color: theme.palette.error.main }} />;
      case 'stable':
        return <TrendingFlat sx={{ fontSize: 16, color: theme.palette.text.secondary }} />;
      default:
        return null;
    }
  };

  const getTrendColor = () => {
    switch (trend) {
      case 'up':
        return theme.palette.success.main;
      case 'down':
        return theme.palette.error.main;
      case 'stable':
        return theme.palette.text.secondary;
      default:
        return theme.palette.text.secondary;
    }
  };

  if (loading) {
    return (
      <Box
        sx={{
          p: 2.5,
          borderRadius: 2,
          background: alpha(theme.palette.primary.main, 0.05),
          border: `1px solid ${alpha(theme.palette.primary.main, 0.1)}`,
          height: '100%',
          display: 'flex',
          flexDirection: 'column',
          gap: 1,
        }}
      >
        <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
          <Skeleton variant="text" width="60%" height={20} />
          <Skeleton variant="circular" width={32} height={32} />
        </Box>
        <Skeleton variant="text" width="40%" height={40} />
        {sparklineData && <Skeleton variant="rectangular" width="100%" height={40} />}
        {trendValue && <Skeleton variant="text" width="50%" height={16} />}
      </Box>
    );
  }

  return (
    <Box
      sx={{
        p: 2.5,
        borderRadius: 2,
        background: `linear-gradient(135deg, ${alpha(color, 0.15)} 0%, ${alpha(
          color,
          0.05
        )} 100%)`,
        border: `1px solid ${alpha(color, 0.3)}`,
        height: '100%',
        display: 'flex',
        flexDirection: 'column',
        gap: 1,
        transition: 'all 0.3s ease',
        '&:hover': {
          transform: 'translateY(-2px)',
          boxShadow: `0 4px 12px ${alpha(color, 0.2)}`,
        },
      }}
    >
      {/* Header with label and icon */}
      <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
        <Typography variant="body2" color="text.secondary" fontWeight={500}>
          {label}
        </Typography>
        {Icon && (
          <Box
            sx={{
              p: 0.75,
              borderRadius: 1.5,
              bgcolor: alpha(color, 0.2),
              display: 'flex',
              alignItems: 'center',
            }}
          >
            <Icon sx={{ fontSize: 20, color }} />
          </Box>
        )}
      </Box>

      {/* Value display */}
      <Box sx={{ display: 'flex', alignItems: 'baseline', gap: 0.5 }}>
        <Typography
          variant="h3"
          fontWeight={700}
          sx={{
            color,
            transition: 'all 0.3s ease',
            transform: isAnimating ? 'scale(1.05)' : 'scale(1)',
          }}
        >
          {formatValue(displayValue)}
        </Typography>
        {unit && (
          <Typography variant="body2" color="text.secondary">
            {unit}
          </Typography>
        )}
      </Box>

      {/* Sparkline chart */}
      {sparklineData && sparklineData.length > 0 && (
        <Box sx={{ height: 40, mt: 0.5 }}>
          <ResponsiveContainer width="100%" height="100%">
            <LineChart data={sparklineData}>
              <Line
                type="monotone"
                dataKey="value"
                stroke={color}
                strokeWidth={2}
                dot={false}
                isAnimationActive={true}
                animationDuration={500}
              />
            </LineChart>
          </ResponsiveContainer>
        </Box>
      )}

      {/* Trend indicator */}
      {trend && trendValue && (
        <Box sx={{ display: 'flex', alignItems: 'center', gap: 0.5, mt: 'auto' }}>
          {getTrendIcon()}
          <Typography
            variant="caption"
            sx={{
              color: getTrendColor(),
              fontWeight: 600,
            }}
          >
            {trendValue}
          </Typography>
        </Box>
      )}
    </Box>
  );
};

KPIWidget.propTypes = {
  label: PropTypes.string.isRequired,
  value: PropTypes.oneOfType([PropTypes.number, PropTypes.string]),
  unit: PropTypes.string,
  icon: PropTypes.elementType,
  color: PropTypes.string.isRequired,
  trend: PropTypes.oneOf(['up', 'down', 'stable']),
  trendValue: PropTypes.string,
  sparklineData: PropTypes.arrayOf(
    PropTypes.shape({
      value: PropTypes.number.isRequired,
    })
  ),
  loading: PropTypes.bool,
};

export default KPIWidget;