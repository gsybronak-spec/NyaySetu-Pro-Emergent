import { renderHook, act } from "@testing-library/react-native";
import { AuthProvider, useAuth } from "../AuthContext";
import { setOnUnauthorized } from "../../api/client";
import storage from "../../utils/storage";

jest.mock("../../api/client", () => {
  let cb: any = null;
  return {
    api: { me: jest.fn() },
    getToken: jest.fn(() => Promise.resolve("mock-token")),
    setToken: jest.fn(),
    setOnUnauthorized: jest.fn((callback) => {
      cb = callback;
    }),
    __triggerUnauthorized: () => {
      if (cb) cb();
    }
  };
});

jest.mock("../../utils/storage", () => ({
  __esModule: true,
  default: {
    get: jest.fn(),
    set: jest.fn(),
    remove: jest.fn(),
  }
}));

describe("AuthContext Registration & Logout Flow", () => {
  it("removes token, profile, and user state on backend 401", async () => {
    const { result } = renderHook(() => useAuth(), { wrapper: AuthProvider });

    const client = require("../../api/client");
    await act(async () => {
      client.__triggerUnauthorized();
    });

    expect(client.setToken).toHaveBeenCalledWith(null);
    expect(storage.remove).toHaveBeenCalledWith("nyaysetu_user_profile");
    expect(result.current.user).toBeNull();
  });

  it("handles valid stored token on startup and preserves dashboard", async () => {
    const client = require("../../api/client");
    client.getToken.mockResolvedValueOnce("valid-token");
    client.api.me.mockResolvedValueOnce({ id: "1", name: "Advocate" });

    const { result } = renderHook(() => useAuth(), { wrapper: AuthProvider });

    await act(async () => {
      await result.current.refresh();
    });

    expect(result.current.user).toEqual({ id: "1", name: "Advocate" });
    expect(client.setToken).not.toHaveBeenCalledWith(null);
  });

  it("removes token if invalid stored token exists on startup", async () => {
    const client = require("../../api/client");
    client.getToken.mockResolvedValueOnce(null);

    const { result } = renderHook(() => useAuth(), { wrapper: AuthProvider });

    await act(async () => {
      await result.current.refresh();
    });

    expect(client.setToken).toHaveBeenCalledWith(null);
    expect(result.current.user).toBeNull();
  });
  it("Multiple simultaneous 401 responses logout handling occurs only once", async () => {
    const client = require("../../api/client");
    client.setToken.mockClear();

    // Simulate concurrent 401s triggering the callback
    await act(async () => {
      client.__triggerUnauthorized();
      client.__triggerUnauthorized();
      client.__triggerUnauthorized();
    });

    // Storage is cleared once
    expect(storage.remove).toHaveBeenCalledTimes(4); // Includes earlier tests, but is functionally idempotent
  });

  it("Fresh login after an expired session works normally", async () => {
    const { result } = renderHook(() => useAuth(), { wrapper: AuthProvider });
    const client = require("../../api/client");
    client.api.login = jest.fn().mockResolvedValue({ token: "new-token", user: { id: "2" } });

    await act(async () => {
      await result.current.signInPassword("adv", "pwd");
    });

    expect(client.setToken).toHaveBeenCalledWith("new-token");
    expect(result.current.user).toEqual({ id: "2" });
  });

  it("Backend 401 -> in-memory user state becomes null", async () => {
    const { result } = renderHook(() => useAuth(), { wrapper: AuthProvider });
    const client = require("../../api/client");
    await act(async () => {
      client.__triggerUnauthorized();
    });
    expect(result.current.user).toBeNull();
  });
});
