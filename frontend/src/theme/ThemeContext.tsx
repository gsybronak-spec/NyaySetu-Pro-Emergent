import React, { createContext, useContext, useEffect, useState } from "react";
import { Appearance } from "react-native";
import { storage } from "@/src/utils/storage";
import { LightColors, DarkColors, ThemeColors } from "./tokens";

type Mode = "light" | "dark" | "system";

interface ThemeCtx {
  mode: Mode;
  isDark: boolean;
  colors: ThemeColors;
  setMode: (m: Mode) => void;
}

const Ctx = createContext<ThemeCtx>({
  mode: "light",
  isDark: false,
  colors: LightColors,
  setMode: () => {},
});

const KEY = "nyaysetu_theme_mode";

export function ThemeProvider({ children }: { children: React.ReactNode }) {
  const [mode, setModeState] = useState<Mode>("light");
  const [systemDark, setSystemDark] = useState(Appearance.getColorScheme() === "dark");

  useEffect(() => {
    storage.getItem(KEY, "light").then((v) => {
      if (v === "light" || v === "dark" || v === "system") setModeState(v);
    });
    const sub = Appearance.addChangeListener(({ colorScheme }) => setSystemDark(colorScheme === "dark"));
    return () => sub.remove();
  }, []);

  const setMode = (m: Mode) => {
    setModeState(m);
    storage.setItem(KEY, m);
  };

  const isDark = mode === "system" ? systemDark : mode === "dark";
  const colors = isDark ? DarkColors : LightColors;

  return <Ctx.Provider value={{ mode, isDark, colors, setMode }}>{children}</Ctx.Provider>;
}

export const useTheme = () => useContext(Ctx);
