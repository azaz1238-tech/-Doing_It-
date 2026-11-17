import client from "../../core/api/client";

// 인증 API (API-SPEC §5.1). 화면에서 axios를 직접 부르지 않는다(ARCHITECTURE §5).

export async function signup({ loginId, password, name }) {
  const { data } = await client.post("/auth/signup", {
    login_id: loginId,
    password,
    name,
  });
  return data; // User (비밀번호 정보 없음)
}

export async function login({ loginId, password }) {
  const { data } = await client.post("/auth/login", {
    login_id: loginId,
    password,
  });
  return data; // { access_token, ... }
}
