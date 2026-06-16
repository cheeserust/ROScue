# Troubleshooting: Imitation Learning Latency

모방학습 추론 적용 과정에서 발생한 통신 지연과 환경 세팅 문제를 정리합니다.

---

## Problem

```text
- 추론 서버와 로봇 노드 간 응답 지연
- 공용망 사용 시 latency 증가
- 카메라 환경 차이로 policy 불안정
```

---

## Cause

```text
- 네트워크 레이턴시
- 영상 전송 bandwidth
- 학습 데이터와 실제 조명/각도 차이
- 추론 서버 부하
```

---

## Solution

```text
1. 독립망 구성
2. 추론 서버와 ROS 노드 통신 최적화
3. 지연 허용 범위 조정
4. 실제 조건에서 데이터 추가 수집
5. 카메라 위치/각도 고정
```

---

## TODO

- [ ] latency 측정 표 추가
- [ ] FPS 측정 추가
- [ ] 네트워크 구성도 추가
- [ ] 실패/복구 데이터 수집 정책 작성
