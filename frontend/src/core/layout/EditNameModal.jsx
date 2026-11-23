import { useId, useRef, useState } from "react";
import { useAuth } from "../auth/useAuth";
import Button from "../ui/Button";
import Input from "../ui/Input";
import Modal from "../ui/Modal";
import { useToast } from "../ui/useToast";
import { countChars } from "../utils/text";

const NAME_MAX = 50;
// 회원가입(S2)과 같은 문구 — 이름 규칙이 같다(앞뒤 공백 제거 후 1~50자)
const NAME_EMPTY = "1자 이상 입력해 주세요";
const NAME_TOO_LONG = "50자 이하로 입력해 주세요";

/**
 * 내 정보 수정 — 이름 바꾸기 (AUTH-06, API-SPEC §6 `PATCH /users/me`)
 * TopBar 메뉴 `내 정보 수정`에서 연다(UI-DESIGN §3.1).
 * - AUTH-06-b: 비우거나 51자 이상이면 입력칸 아래 오류, 저장 버튼이 꺼져 바뀌지 않는다.
 * - AUTH-06-a: 저장하면 TopBar 이름이 바로 바뀌고, 업무 담당자·댓글 작성자는 서버에서 다시 받을 때 새 이름으로 보인다.
 * 열 때마다 지금 이름으로 시작하도록, 열려 있을 때만 그린다({open && <EditNameModal/>}).
 */
export default function EditNameModal({ onClose }) {
  const formId = useId();
  const toast = useToast();
  const { user, updateName } = useAuth();
  const [name, setName] = useState(user.name);
  const [serverError, setServerError] = useState();
  const [submitting, setSubmitting] = useState(false);
  // 빠르게 두 번 누르면 submitting이 바뀌기 전에 두 번째 요청이 나간다 → ref로 바로 막는다(이슈 #48).
  const submittingRef = useRef(false);

  const trimmed = name.trim();
  const length = countChars(trimmed);
  const localError =
    length < 1 ? NAME_EMPTY : length > NAME_MAX ? NAME_TOO_LONG : undefined;
  const unchanged = trimmed === user.name;
  const isDirty = name !== user.name;

  const submit = async (e) => {
    e.preventDefault();
    if (submittingRef.current || localError) return;
    if (unchanged) {
      onClose();
      return;
    }
    submittingRef.current = true;
    setSubmitting(true);
    try {
      await updateName(trimmed);
      toast.success("이름을 바꿨습니다");
      onClose();
    } catch (error) {
      const body = error.response?.data;
      const fieldError = body?.errors?.find((er) => er.field === "name");
      if (fieldError) {
        setServerError(fieldError.message); // 422 — 칸 아래에 서버 문구
      } else {
        toast.error(body?.message ?? "잠시 후 다시 시도해 주세요");
      }
      submittingRef.current = false;
      setSubmitting(false);
    }
  };

  return (
    <Modal
      open
      onClose={onClose}
      title="내 정보 수정"
      subtitle="팀원에게 보이는 이름입니다"
      size="sm"
      isDirty={isDirty}
      footer={
        <>
          <Button variant="secondary" onClick={onClose}>
            취소
          </Button>
          <Button
            type="submit"
            form={formId}
            loading={submitting}
            disabled={Boolean(localError) || unchanged}
          >
            저장
          </Button>
        </>
      }
    >
      <form id={formId} onSubmit={submit} noValidate>
        <Input
          label="이름"
          required
          autoFocus
          autoComplete="name"
          maxCount={NAME_MAX}
          value={name}
          onChange={(e) => {
            setName(e.target.value);
            setServerError(undefined);
          }}
          error={localError ?? serverError}
        />
      </form>
    </Modal>
  );
}
