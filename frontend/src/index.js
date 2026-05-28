import React from 'react';
import ReactDOM from 'react-dom/client';
import { Provider, useSelector } from 'react-redux';
import { BrowserRouter } from 'react-router-dom';
import { ThemeProvider } from '@mui/material/styles';
import CssBaseline from '@mui/material/CssBaseline';
import App from './App';
import store from './store';
import { getTheme } from './styles/theme';
import './styles/global.css';
import ErrorBoundary from './components/Common/ErrorBoundary';

/**
 * ThemeWrapper — Lee el estado de tema de Redux y aplica el ThemeProvider
 * correcto de forma reactiva. Se coloca dentro del Provider para tener
 * acceso al store.
 */
const ThemeWrapper = ({ children }) => {
  const themeMode = useSelector((state) => state.ui.theme);
  const theme = getTheme(themeMode);
  return (
    <ThemeProvider theme={theme}>
      <CssBaseline />
      {children}
    </ThemeProvider>
  );
};

const root = ReactDOM.createRoot(document.getElementById('root'));

root.render(
  <React.StrictMode>
    <ErrorBoundary>
      <Provider store={store}>
        <BrowserRouter>
          <ThemeWrapper>
            <App />
          </ThemeWrapper>
        </BrowserRouter>
      </Provider>
    </ErrorBoundary>
  </React.StrictMode>
);

if (module.hot) {
  module.hot.accept('./App', () => {
    const NextApp = require('./App').default;
    root.render(
      <React.StrictMode>
        <ErrorBoundary>
          <Provider store={store}>
            <BrowserRouter>
              <ThemeWrapper>
                <NextApp />
              </ThemeWrapper>
            </BrowserRouter>
          </Provider>
        </ErrorBoundary>
      </React.StrictMode>
    );
  });
}

if (process.env.NODE_ENV === 'development') {
  console.log('PetroFlow iniciado en modo desarrollo');
  console.log('API URL:', process.env.REACT_APP_API_URL);
  console.log('WebSocket URL:', process.env.REACT_APP_WS_URL);
}