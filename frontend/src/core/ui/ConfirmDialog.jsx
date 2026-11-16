import Button from "./Button";
import Modal from "./Modal";

/**
 * ConfirmDialog — 되돌릴 수 없는 동작(삭제·멤버 제거) 전에 한 번 더 묻는다.
 * 사용처: S6 업무 삭제, S7 프로젝트 삭제·멤버 제거
 * 시안 v0.3처럼 ✕가 없다 — `취소`·ESC·바깥 클릭으로 닫는다.
 *
 * @param {React.ReactNode} message 본문 문구 (~합니다체, 끝 마침표 없음). 문장마다 줄을 바꾸려면 \n을 넣는다(시안 v0.3)
 * @param {boolean} [danger] 삭제처럼 위험한 동작이면 확인 버튼을 빨간색으로
 * @param {boolean} [loading] 요청 중이면 버튼 비활성
 * @param {boolean} [confirmDisabled] 예: S7 프로젝트 이름이 다르면 삭제 비활성
 * @param {React.ReactNode} [children] 추가 입력(예: 프로젝트 이름 확인 Input)
 */
export default function ConfirmDialog({
  open,
  title,
  message,
  confirmLabel = "확인",
  cancelLabel = "취소",
  danger = false,
  loading = false,
  confirmDisabled = false,
  onConfirm,
  onCancel,
  children,
}) {
  return (
    <Modal
      open={open}
      onClose={onCancel}
      title={title}
      size="sm"
      showClose={false}
      footer={
        <>
          <Button variant="secondary" onClick={onCancel} disabled={loading}>
            {cancelLabel}
          </Button>
          <Button
            variant={danger ? "danger" : "primary"}
            onClick={onConfirm}
            loading={loading}
            disabled={confirmDisabled}
          >
            {confirmLabel}
          </Button>
        </>
      }
    >
      {message && (
        <p className="whitespace-pre-line text-neutral-600">{message}</p>
      )}
      {children && <div className="mt-3">{children}</div>}
    </Modal>
  );
}
