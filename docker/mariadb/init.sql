-- MariaDB 컨테이너를 처음 만들 때 한 번 실행된다 (ARCHITECTURE §3)
-- 개발 DB(doing_it)와 pytest 전용 DB(doing_it_test)를 utf8mb4로 만든다 (DATABASE-DESIGN §1-7)
-- 테이블은 여기서 만들지 않는다. 테이블은 Alembic 마이그레이션으로만 만든다 (CONSTITUTION 8)

CREATE DATABASE IF NOT EXISTS doing_it
  CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;

CREATE DATABASE IF NOT EXISTS doing_it_test
  CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;

-- 'doingit' 계정은 .env의 MARIADB_USER로 컨테이너가 먼저 만든다.
-- SQL 파일은 .env 값을 읽지 못하므로 계정 이름을 여기 고정한다 → MARIADB_USER는 doingit으로 둔다.
GRANT ALL PRIVILEGES ON doing_it.* TO 'doingit'@'%';
GRANT ALL PRIVILEGES ON doing_it_test.* TO 'doingit'@'%';
FLUSH PRIVILEGES;
