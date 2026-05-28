import React from 'react';
import {
  AppBar,
  Toolbar,
  Typography,
  IconButton,
  Badge,
  Box,
  Breadcrumbs,
  Link,
} from '@mui/material';
import {
  Notifications as NotificationsIcon,
  Brightness4 as Brightness4Icon,
  Brightness7 as Brightness7Icon,
} from '@mui/icons-material';
import { useDispatch, useSelector } from 'react-redux';
import { useNavigate } from 'react-router-dom';
import { toggleTheme, setActiveView } from '../../store/slices/uiSlice';
import UserMenu from '../Auth/UserMenu';

/**
 * Header Component
 * 
 * Top application header with:
 * - Breadcrumbs navigation
 * - Theme toggle
 * - Notifications
 * - User menu
 */
const Header = () => {
  const dispatch = useDispatch();
  const { theme, breadcrumbs, notifications } = useSelector((state) => state.ui);

  const unreadNotifications = notifications.filter((n) => !n.read).length;

  const handleThemeToggle = () => {
    dispatch(toggleTheme());
  };

  const handleNotificationsClick = () => {
    // Show status instead of route transition
    alert(`Mensajes operacionales:\nTiene ${unreadNotifications} notificaciones activas de telemetría de campo.`);
  };

  return (
    <AppBar
      position="static"
      color="default"
      elevation={1}
      sx={{
        backgroundColor: (theme) =>
          theme.palette.mode === 'light' ? '#fff' : theme.palette.background.paper,
      }}
    >
      <Toolbar>
        {/* Breadcrumbs */}
        <Box sx={{ flexGrow: 1 }}>
          {breadcrumbs.length > 0 ? (
            <Breadcrumbs aria-label="breadcrumb">
              {breadcrumbs.map((crumb, index) => {
                const isLast = index === breadcrumbs.length - 1;
                return isLast ? (
                  <Typography key={index} color="text.primary">
                    {crumb.label}
                  </Typography>
                ) : (
                  <Link
                    key={index}
                    underline="hover"
                    color="inherit"
                    href={crumb.path}
                    onClick={(e) => {
                      e.preventDefault();
                      const path = crumb.path;
                      const viewName = path.startsWith('/analysis/')
                        ? path.split('/').pop()
                        : path.replace('/', '');
                      dispatch(setActiveView(viewName || 'dashboard'));
                    }}
                  >
                    {crumb.label}
                  </Link>
                );
              })}
            </Breadcrumbs>
          ) : (
            <Typography variant="h6" component="div">
              Industrial Equipment Platform
            </Typography>
          )}
        </Box>

        {/* Theme Toggle */}
        <IconButton
          onClick={handleThemeToggle}
          color="inherit"
          aria-label="toggle theme"
        >
          {theme === 'dark' ? <Brightness7Icon /> : <Brightness4Icon />}
        </IconButton>

        {/* Notifications */}
        <IconButton
          onClick={handleNotificationsClick}
          color="inherit"
          aria-label="notifications"
        >
          <Badge badgeContent={unreadNotifications} color="error">
            <NotificationsIcon />
          </Badge>
        </IconButton>

        {/* User Menu */}
        <UserMenu />
      </Toolbar>
    </AppBar>
  );
};

export default Header;