/**
 * 홈 페이지 컴포넌트.
 *
 * Next.js App Router에서:
 * - 파일 경로 src/app/page.tsx
 * - 주소로는 "/" (사이트 첫 화면)
 *
 * 지금은 안내 문구만 보여주는 scaffold 상태이다.
 * 나중에 회의 목록·입력·AI 결과 화면으로 바꿀 예정.
 */

// page.module.css 의 클래스 이름들을 styles 객체로 가져온다
// 예: styles.main → 실제로는 "page_main_xxxxx" 같은 고유 클래스명으로 변환됨
// (CSS Modules: 다른 파일과 클래스 이름이 충돌하지 않게 해줌)
import styles from "./page.module.css";

/**
 * export default = 이 파일이 페이지일 때 Next.js가 기본으로 쓰는 컴포넌트
 * function Home = 화면에 그릴 React 컴포넌트
 */
export default function Home() {
  return (
    // <main> = 페이지의 주요 내용 영역 (시맨틱 HTML)
    // className={styles.main} = page.module.css 의 .main 스타일 적용
    <main className={styles.main}>
      {/* <h1> = 가장 큰 제목 */}
      <h1 className={styles.title}>Meeting Action Tracker</h1>

      {/* 서비스가 무엇인지 짧게 설명 */}
      <p className={styles.lead}>
        회의록 텍스트를 구조화하고 액션아이템을 관리하는 서비스입니다.
      </p>

      {/* 현재 구조/진행 상태 안내 */}
      <p className={styles.note}>
        Frontend(Next.js) ↔ Backend(FastAPI) 분리 구성. 이후 커밋에서 API·화면을
        연결합니다.
      </p>
    </main>
  );
}
