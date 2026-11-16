import axios from "axios";

const TOKEN_KEY = "doingit_token";

// 토큰 읽기·저장·삭제는 이 객체로만 한다. 토큰 값을 콘솔에 출력하지 않는다.
export const tokenStorage = {
  get: () => localStorage.getItem(TOKEN_KEY),
  set: (token) => localStorage.setItem(TOKEN_KEY, token),
  clear: () => localStorage.removeItem(TOKEN_KEY),
};

const client = axios.create({ baseURL: "/api" });

client.interceptors.request.use((config) => {
  const token = tokenStorage.get();
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

client.interceptors.response.use(
  (response) => response,
  (error) => {
    const status = error.response?.status;
    // 로그인 요청의 401은 "아이디 또는 비밀번호가 올바르지 않습니다" 문구로 보여야 하므로 제외한다.
    const isLoginRequest = error.config?.url === "/auth/login";
    if (status === 401 && !isLoginRequest) {
      tokenStorage.clear();
      // core/는 라우터를 모르므로 브라우저 이동을 쓴다. 로그인 화면이 expired 값을 보고 안내한다.
      if (window.location.pathname !== "/login") {
        window.location.assign("/login?expired=1");
      }
    }
    // 403·404·400 등은 각 화면이 처리하도록 그대로 넘긴다.
    return Promise.reject(error);
  },
);

export default client;
