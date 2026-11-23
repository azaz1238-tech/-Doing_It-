import { useEffect, useRef, useState } from "react";
import { Link, useNavigate, useSearchParams } from "react-router";
import { useAuth } from "../../core/auth/useAuth";
import Button from "../../core/ui/Button";
import Input from "../../core/ui/Input";
import { TriangleAlertIcon } from "../../core/ui/icons";
import { useToast } from "../../core/ui/useToast";
import { login as loginRequest } from "./api";

// S1 로그인 — AUTH-02, AUTH-04 · US-02, 03 · UI-DESIGN S1 (모양은 시안 v0.3, 문구는 명세)
// 빈 칸만 프론트에서 막고 형식은 검사하지 않는다: 형식이 틀린 아이디도 서버가 401로 답해야
// 계정이 있는지 드러나지 않는다(API-SPEC §5.1, SPEC-CHANGELOG #8).
const FORM_ERRORS = {
  INVALID_CREDENTIALS: "아이디 또는 비밀번호가 올바르지 않습니다", // AUTH-02-b
  ACCOUNT_DISABLED: "사용할 수 없는 계정입니다", // AUTH-02-c
};

export default function LoginPage() {
  const navigate = useNavigate();
  const toast = useToast();
  const { login } = useAuth();
  const [searchParams, setSearchParams] = useSearchParams();
  const [form, setForm] = useState({ loginId: "", password: "" });
  const [errors, setErrors] = useState({});
  const [formError, setFormError] = useState("");
  const [submitting, setSubmitting] = useState(false);

  // 토큰 만료로 온 경우(client.js가 ?expired=1을 붙임) 한 번만 안내한다 (UI-DESIGN §8, AUTH-04-b)
  const expiredShown = useRef(false);
  useEffect(() => {
    if (searchParams.get("expired") !== "1" || expiredShown.current) return;
    expiredShown.current = true;
    toast.warning("로그인이 만료되었습니다. 다시 로그인해 주세요");
    setSearchParams({}, { replace: true });
  }, [searchParams, setSearchParams, toast]);

  // 입력을 고치면 그 칸의 오류와 폼 아래 오류 상자를 지운다. 아이디 대문자는 입력 즉시 소문자로 보여 준다.
  const change = (key, field) => (e) => {
    const value =
      key === "loginId" ? e.target.value.toLowerCase() : e.target.value;
    setForm((prev) => ({ ...prev, [key]: value }));
    setErrors((prev) => ({ ...prev, [field]: undefined }));
    setFormError("");
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    const found = {};
    if (!form.loginId.trim()) found.login_id = "아이디를 입력해 주세요";
    if (!form.password) found.password = "비밀번호를 입력해 주세요";
    setErrors(found);
    setFormError("");
    if (Object.keys(found).length > 0) return;

    setSubmitting(true);
    try {
      const { access_token: accessToken } = await loginRequest({
        loginId: form.loginId.trim(),
        password: form.password, // 공백을 지우지 않는다 (API-SPEC §5.1)
      });
      await login(accessToken); // 토큰 저장 + /users/me (AuthContext)
      navigate("/", { replace: true }); // AUTH-02-a: 내 대시보드(DASH-04)
    } catch (error) {
      const body = error.response?.data;
      if (FORM_ERRORS[body?.code]) {
        // 서버 문구 대신 명세 문구로 고정: 어떤 경우에도 "없는 아이디"와 "틀린 비밀번호"를 구분해 보이지 않는다
        setFormError(FORM_ERRORS[body.code]);
      } else if (body?.code === "VALIDATION_ERROR" && body.errors?.length) {
        setErrors(
          Object.fromEntries(body.errors.map((er) => [er.field, er.message])),
        );
      } else {
        toast.error(body?.message ?? "잠시 후 다시 시도해 주세요");
      }
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <main className="flex min-h-screen flex-col items-center justify-center bg-neutral-50 px-4 py-10">
      {/* 로고 + 한 줄 소개: 시안 v0.3 S1 — "동"은 본문색, "잇"은 주 색 */}
      <p className="text-4xl font-bold text-neutral-900">
        동<span className="text-primary">잇</span>
      </p>
      <p className="mt-2 mb-8 text-sm text-neutral-500">
        팀 업무를 한눈에, 마감은 놓치지 않게
      </p>
      <form
        onSubmit={handleSubmit}
        noValidate
        className="w-full max-w-md rounded-xl border border-neutral-200 bg-white p-8 shadow-sm"
      >
        <h1 className="mb-6 text-xl font-bold text-neutral-900">로그인</h1>
        <div className="flex flex-col gap-5">
          <Input
            label="아이디"
            autoComplete="username"
            value={form.loginId}
            onChange={change("loginId", "login_id")}
            error={errors.login_id}
          />
          <Input
            label="비밀번호"
            type="password"
            autoComplete="current-password"
            value={form.password}
            onChange={change("password", "password")}
            error={errors.password}
          />
        </div>
        {/* 401·403은 폼 아래 상자로 (UI-DESIGN S1) */}
        {formError && (
          <p
            role="alert"
            className="mt-5 flex items-center gap-2 rounded-lg bg-danger-soft px-4 py-3 text-sm text-danger"
          >
            <TriangleAlertIcon size={16} />
            {formError}
          </p>
        )}
        <Button
          type="submit"
          loading={submitting}
          className="mt-6 h-11 w-full text-base"
        >
          로그인
        </Button>
        <p className="mt-5 text-center text-sm text-neutral-500">
          계정이 없나요?{" "}
          <Link to="/signup" className="font-semibold text-primary">
            회원가입
          </Link>
        </p>
      </form>
    </main>
  );
}
