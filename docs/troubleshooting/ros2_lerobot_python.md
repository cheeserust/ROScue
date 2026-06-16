# Troubleshooting: ROS2-LeRobot Python Conflict

ROS 2와 LeRobot Python 환경 충돌 해결 기록입니다.

---

## Problem

```text
ROS 2 node: Python 환경 A
LeRobot: Python 환경 B
두 환경을 같은 프로세스에서 import하면 모듈 로딩 실패 또는 실행 오류 발생
```

---

## Cause

```text
- ROS 2와 LeRobot의 요구 Python 버전 또는 의존성 차이
- 동일 환경에서 동시 실행 불가
- 필요한 모듈 일부만 import하면 되는 구조
```

---

## Solution

```text
1. LeRobot source 분석
2. 실행에 필요한 모듈만 추출
3. ROScue 패키지 내부로 복사/분리
4. ROS 2 환경에서 최소 의존성으로 실행
```

---

## Result

```text
- Python 버전 충돌 완화
- ROS 2 환경에서 추론 관련 코드 실행 가능
```

---

## TODO

- [ ] 실제 오류 로그 추가
- [ ] 사용한 Python 버전 기록
- [ ] 복사한 모듈 목록 작성
