import { createTheme } from "@mui/material";

// Fixed kiosk display size — the app targets one dedicated touchscreen device, not a responsive range.
export const KIOSK_WIDTH = 680;

// Black and white theme shared by both the kiosk-facing app and the admin panel.
export const appTheme = createTheme({
  palette: {
    primary: {
      main: "#000000",
    },
    secondary: {
      main: "#333333",
    },
    background: {
      default: "#ffffff",
    },
  },
  typography: {
    fontFamily: "'Inter', sans-serif",
    h1: {
      fontFamily: "'Inter', sans-serif",
      color: "#000000",
      fontWeight: 600,
    },
    h2: {
      fontFamily: "'Inter', sans-serif",
      color: "#000000",
      fontWeight: 600,
    },
    h3: {
      fontFamily: "'Inter', sans-serif",
      color: "#000000",
      fontWeight: 500,
    },
    h4: {
      fontFamily: "'Inter', sans-serif",
      color: "#000000",
      fontWeight: 500,
    },
    h5: {
      fontFamily: "'Inter', sans-serif",
      color: "#000000",
      fontWeight: 400,
    },
    h6: {
      fontFamily: "'Inter', sans-serif",
      color: "#000000",
      fontWeight: 400,
    },
    button: {
      fontFamily: "'Inter', sans-serif",
      textTransform: "none",
      color: "#000000",
      fontWeight: 500,
    },
  },
  components: {
    MuiButton: {
      styleOverrides: {
        root: {
          borderRadius: 30,
          padding: "10px 20px",
          color: "#000000",
          borderColor: "#000000",
          "&:hover": {
            boxShadow: "0px 2px 4px rgba(0, 0, 0, 0.1)",
          },
        },
        contained: {
          backgroundColor: "#000000",
          color: "#ffffff",
          "&:hover": {
            backgroundColor: "#333333",
          },
        },
        outlined: {
          borderColor: "#000000",
          color: "#000000",
          "&:hover": {
            borderColor: "#333333",
            backgroundColor: "rgba(0, 0, 0, 0.04)",
          },
        },
      },
    },
    MuiDialog: {
      styleOverrides: {
        paper: {
          borderRadius: 12,
          padding: 8,
        },
      },
    },
  },
});
