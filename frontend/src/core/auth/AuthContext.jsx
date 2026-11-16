import { useCallback, useEffect, useMemo, useState } from "react";
import client, { tokenStorage } from "../api/client";
import { AuthContext } from "./useAuth";

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null);
  // 토큰이 있으면 /users/me 응답이 올 때까지 loading으로 둔다(새로고침 시 로그인 화면 깜빡임 방지).
  const [loading, setLoading] = useState(() => Boolean(tokenStorage.get()));

  const fetchMe = useCallback(async () => {
    const { data } = await client.get("/users/me");
    setUser(data);
    return data;
  }, []);

  // 앱 시작 시 한 번, 저장된 토큰으로 로그인 상태를 복원한다.
  useEffect(() => {
    if (!tokenStorage.get()) return;
    client
      .get("/users/me")
      .then(({ data }) => setUser(data))
      .catch(() => {
        tokenStorage.clear();
        setUser(null);
      })
      .finally(() => setLoading(false));
  }, []);

  // 로그인 API 호출은 features/auth/api.js가 하고, 받은 토큰만 여기로 넘긴다.
  const login = useCallback(
    async (accessToken) => {
      tokenStorage.set(accessToken);
      try {
        return await fetchMe();
      } catch (error) {
        tokenStorage.clear();
        setUser(null);
        throw error;
      }
    },
    [fetchMe],
  );

  // 로그아웃 API는 없다. 토큰을 지우는 것으로 끝낸다(API-SPEC §1).
  const logout = useCallback(() => {
    tokenStorage.clear();
    setUser(null);
  }, []);

  const value = useMemo(
    () => ({ user, loading, login, logout }),
    [user, loading, login, logout],
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}
