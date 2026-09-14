import React, { createContext, useContext } from "react";

export interface KeyboardScrollContextValue {
  scrollToInput: (ref: React.RefObject<any>, extraOffset?: number) => void;
  keyboardHeight: number;
  isKeyboardVisible: boolean;
}

const defaultContext: KeyboardScrollContextValue = {
  scrollToInput: () => {},
  keyboardHeight: 0,
  isKeyboardVisible: false,
};

export const KeyboardScrollContext = createContext<KeyboardScrollContextValue>(defaultContext);

export function useKeyboardScroll(): KeyboardScrollContextValue {
  return useContext(KeyboardScrollContext);
}
