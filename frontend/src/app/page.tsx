import styles from "./page.module.css";

export default function Home() {
  return (
    <main className={styles.main}>
      <h1 className={styles.title}>Meeting Action Tracker</h1>
      <p className={styles.lead}>
        회의록 텍스트를 구조화하고 액션아이템을 관리하는 서비스입니다.
      </p>
      <p className={styles.note}>
        Frontend(Next.js) ↔ Backend(FastAPI) 분리 구성. 이후 커밋에서 API·화면을
        연결합니다.
      </p>
    </main>
  );
}
