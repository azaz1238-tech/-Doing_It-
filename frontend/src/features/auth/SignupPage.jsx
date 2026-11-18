import { useState } from "react";
import { Link, useNavigate } from "react-router";
import Button from "../../core/ui/Button";
import Input from "../../core/ui/Input";
import { useToast } from "../../core/ui/useToast";
import { countChars } from "../../core/utils/text"; // 서버(Python len)와 같게 — 이모지도 1자
import { signup } from "./api";

// S2 회원가입 — AUTH-01, AUTH-03 · US-01 · UI-DESIGN S2 (모양은 시안 v0.3, 문구는 명세)
// 입력 규칙: REQUIREMENTS AUTH-01 · SPEC F1 · API-SPEC §5.1 (백엔드 schemas/auth.py와 같은 규칙)
//   아이디 영문 소문자·숫자 4~20자 / 비밀번호 8~64자 + UTF-8 72바이트 이하 / 이름 앞뒤 공백 제거 후 1~50자
const LOGIN_ID_PATTERN = /^[a-z0-9]{4,20}$/;
const PASSWORD_MAX_BYTES = 72; // bcrypt 한계. 한글은 1자 = 3바이트

// 오류 문구는 백엔드 422 문구와 똑같이 쓴다 (schemas/auth.py, core/exceptions.py).
// 검사 순서도 백엔드와 같다: 비밀번호는 길이를 먼저 보고, 길이가 맞을 때만 바이트를 본다.
function checkPassword(password) {
  const passwordLength = countChars(password);
  if (passwordLength < 8) return "8자 이상 입력해 주세요";
  if (passwordLength > 64) return "64자 이하로 입력해 주세요";
  if (new TextEncoder().encode(password).length > PASSWORD_MAX_BYTES) {
    return "72바이트 이하로 입력해 주세요 (한글은 24자까지)";
  }
  return undefined;
}

function validate({ loginId, password, name }) {
  const errors = {};
  if (!LOGIN_ID_PATTERN.test(loginId.trim())) {
    errors.login_id = "영문 소문자·숫자 4~20자로 입력해 주세요";
  }
  const passwordError = checkPassword(password);
  if (passwordError) errors.password = passwordError;
  const nameLength = countChars(name.trim());
  if (nameLength < 1) {
    errors.name = "1자 이상 입력해 주세요";
  } else if (nameLength > 50) {
    errors.name = "50자 이하로 입력해 주세요";
  }
  return errors;
}

export default function SignupPage() {
  const navigate = useNavigate();
  const toast = useToast();
  const [form, setForm] = useState({ loginId: "", password: "", name: "" });
  const [errors, setErrors] = useState({});
  const [submitting, setSubmitting] = useState(false);
  // 비밀번호가 규칙(8~64자, 72바이트 이하)에 맞으면 입력하는 동안 바로 알려 준다(시안 v0.3 S2).
  // 틀린 경우는 지금처럼 제출할 때만 보여 준다.
  const passwordOk = form.password !== "" && !checkPassword(form.password);

  // 입력을 고치면 그 칸의 오류만 지운다. 아이디 대문자는 입력 즉시 소문자로 바꿔 보여 준다.
  const change = (key, field) => (e) => {
    const value =
      key === "loginId" ? e.target.value.toLowerCase() : e.target.value;
    setForm((prev) => ({ ...prev, [key]: value }));
    setErrors((prev) => ({ ...prev, [field]: undefined }));
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    const found = validate(form);
    setErrors(found);
    if (Object.keys(found).length > 0) return;

    setSubmitting(true);
    try {
      await signup({
        loginId: form.loginId.trim(),
        password: form.password,
        name: form.name.trim(),
      });
      toast.success("가입되었습니다. 로그인해 주세요");
      navigate("/login"); // 자동 로그인 안 함 (UI-DESIGN S2)
    } catch (error) {
      const body = error.response?.data;
      if (body?.code === "LOGIN_ID_ALREADY_EXISTS") {
        setErrors({ login_id: "이미 사용 중인 아이디입니다" }); // SPEC AUTH-01-b
      } else if (body?.code === "VALIDATION_ERROR" && body.errors?.length) {
        // 422: 서버 field(login_id·password·name)에 맞춰 칸 아래에 표시
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
      {/* 로고: 시안 v0.3 — "동"은 본문색, "잇"은 주 색 (S2에는 부제 없음) */}
      <p className="mb-8 text-4xl font-bold text-neutral-900">
        동<span className="text-primary">잇</span>
      </p>
      <form
        onSubmit={handleSubmit}
        noValidate
        className="w-full max-w-md rounded-xl border border-neutral-200 bg-white p-8 shadow-sm"
      >
        <h1 className="mb-6 text-xl font-bold text-neutral-900">회원가입</h1>
        <div className="flex flex-col gap-5">
          <Input
            label="아이디"
            labelHint="영문 소문자·숫자 4~20자"
            autoComplete="username"
            value={form.loginId}
            onChange={change("loginId", "login_id")}
            error={errors.login_id}
          />
          <Input
            label="비밀번호"
            labelHint="8~64자"
            type="password"
            autoComplete="new-password"
            value={form.password}
            onChange={change("password", "password")}
            error={errors.password}
            success={passwordOk ? "사용할 수 있습니다" : undefined}
          />
          <Input
            label="이름"
            autoComplete="name"
            value={form.name}
            onChange={change("name", "name")}
            error={errors.name}
          />
        </div>
        <Button
          type="submit"
          loading={submitting}
          className="mt-6 h-11 w-full text-base"
        >
          가입하기
        </Button>
        <p className="mt-5 text-center text-sm text-neutral-500">
          이미 계정이 있나요?{" "}
          <Link to="/login" className="font-semibold text-primary">
            로그인
          </Link>
        </p>
      </form>
    </main>
  );
}
