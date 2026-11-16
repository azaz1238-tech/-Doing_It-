// 조건부 클래스 이름을 공백으로 이어 붙인다. clsx 같은 라이브러리는 추가하지 않는다.
export function cn(...classes) {
  return classes.filter(Boolean).join(" ");
}
