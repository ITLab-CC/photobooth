import { createTheme } from "@mui/material";

// The kiosk is one dedicated touchscreen: a 49" TV standing upright, about 1080 px wide. The layout was
// drawn for 760 px, so everything on the kiosk page is scaled by this factor (1 on small windows).
const DESIGN_WIDTH = 760;
export const KIOSK_SCALE = Math.min(
  1.5,
  Math.max(1, (typeof window !== "undefined" ? window.innerWidth : DESIGN_WIDTH) / DESIGN_WIDTH)
);
export const KIOSK_WIDTH = Math.round(680 * KIOSK_SCALE);

// Scale a pixel size for the kiosk screen.
export const px = (value: number): number => Math.round(value * KIOSK_SCALE);

// IT-Lab identity: navy from the logo, teal from the banner. Shared by the kiosk and the admin panel.
export const brand = {
  navy: "#252b3f",
  navySoft: "#4a5168", // secondary text, 7:1 on the surface color
  teal: "#007585", // actions; white text on it is 5.4:1
  tealHover: "#005f6c",
  tealTint: "rgba(0, 117, 133, 0.10)",
  magic: "#d9480f", // reserved for the Magic moments (white text on it is 4.9:1)
  surface: "#f5f7fa",
  line: "rgba(37, 43, 63, 0.16)",
};

const fontFamily = "'Inter', 'Segoe UI', system-ui, sans-serif";

export const appTheme = createTheme({
  palette: {
    primary: { main: brand.teal, dark: brand.tealHover, contrastText: "#ffffff" },
    secondary: { main: brand.navy },
    text: { primary: brand.navy, secondary: brand.navySoft },
    background: { default: brand.surface, paper: "#ffffff" },
    divider: brand.line,
  },
  typography: {
    fontFamily,
    h1: { fontWeight: 600 },
    h2: { fontWeight: 600 },
    h3: { fontWeight: 600 },
    h4: { fontWeight: 600 },
    h5: { fontWeight: 500 },
    h6: { fontWeight: 500 },
    button: { textTransform: "none", fontWeight: 600 },
  },
  components: {
    MuiButton: {
      styleOverrides: {
        root: {
          borderRadius: 30,
          padding: "10px 22px",
          minHeight: 48,
        },
      },
    },
    MuiDialog: {
      styleOverrides: {
        paper: {
          borderRadius: 16,
          padding: 8,
        },
      },
    },
  },
});
