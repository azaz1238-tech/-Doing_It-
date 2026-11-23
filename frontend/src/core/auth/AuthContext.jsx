import { useCallback, useEffect, useMemo, useState } from "react";
import client, { tokenStorage } from "../api/client";
import { AuthContext } from "./useAuth";

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null);
  // 토큰이 있으면 /users/me 응답이 올 때까지 loading으로 둔다(새로고침 시 로그인 화면 깜빡임 방지).
  const [loading, setLoading] = useState(() => Boolean(tokenStorage.get()));
  // 복원이 서버 꺼짐·네트워크·500 때문에 실패하면 true. 토큰은 지우지 않고 "다시 시도"를 보인다(D9-04).
  const [restoreFailed, setRestoreFailed] = useState(false);

  const fetchMe = useCallback(async () => {
    const { data } = await client.get("/users/me");
    setUser(data);
    return data;
  }, []);

  // 저장된 토큰으로 로그인 상태를 복원한다.
  // 토큰은 서버가 "이 토큰으로는 안 된다"고 답할 때(401 만료·잘못됨, 403 비활성 계정)만 지운다.
  // 그 밖의 실패(서버 꺼짐·네트워크·500)에 지우면 잠깐 끊긴 사이 새로고침만 해도 로그아웃된다.
  const restore = useCallback(
    () =>
      client
        .get("/users/me")
        .then(({ data }) => {
          setUser(data);
          setRestoreFailed(false);
        })
        .catch((error) => {
          const status = error.response?.status;
          if (status === 401 || status === 403) {
            tokenStorage.clear();
            setUser(null);
          } else {
            setRestoreFailed(true);
          }
        })
        .finally(() => setLoading(false)),
    [],
  );

  // 앱 시작 시 한 번
  useEffect(() => {
    if (!tokenStorage.get()) return;
    restore();
  }, [restore]);

  // 복원 실패 화면의 "다시 시도"
  const retryRestore = useCallback(() => {
    setRestoreFailed(false);
    setLoading(true);
    restore();
  }, [restore]);

  // 뒤로 가기로 bfcache(브라우저가 얼려 둔 페이지)에서 돌아오면 React 상태가 그대로 살아 있다.
  // 그 사이 로그아웃해 토큰이 없으면 user를 비워 보호 라우트가 로그인 화면으로 보내게 한다(AUTH-04-c, 이슈 #35).
  useEffect(() => {
    const handlePageShow = (event) => {
      if (event.persisted && !tokenStorage.get()) setUser(null);
    };
    window.addEventListener("pageshow", handlePageShow);
    return () => window.removeEventListener("pageshow", handlePageShow);
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

  // 내 이름 수정 (AUTH-06, API-SPEC §6 `PATCH /users/me`). 응답 User로 바꿔 TopBar 이름이 바로 바뀐다.
  // /users/me를 이미 여기서 다루므로 features가 아니라 여기에 둔다(core는 features를 import하지 않는다).
  const updateName = useCallback(async (name) => {
    const { data } = await client.patch("/users/me", { name });
    setUser(data);
    return data;
  }, []);

  const value = useMemo(
    () => ({
      user,
      loading,
      restoreFailed,
      retryRestore,
      login,
      logout,
      updateName,
    }),
    [user, loading, restoreFailed, retryRestore, login, logout, updateName],
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}
