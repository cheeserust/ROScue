# ROS Domain & Namespace

ROScue 다중 로봇 통신 구조를 정리합니다.

---

## Domain Plan

| System | ROS_DOMAIN_ID | Namespace | Role |
|---|---:|---|---|
| Central Server PC | `10` | `/server` | Mission Manager, DB, bridge, Web UI |
| Pinky Mapping Robot | `13` | `/pinky` | SLAM mapping |
| WF1 Robot | `14` | `/wf1` | Navigation and manipulation |
| WF2 Robot | `15` | `/wf2` | Navigation and manipulation |

---

## Topic Separation

```text
/wf1/cmd_vel
/wf1/odom
/wf1/scan
/wf1/navigate_to_pose

/wf2/cmd_vel
/wf2/odom
/wf2/scan
/wf2/navigate_to_pose
```

---

## Frame ID Rule

```text
map
 ├── wf1/odom
 │    └── wf1/base_link
 │         └── wf1/base_scan
 └── wf2/odom
      └── wf2/base_link
           └── wf2/base_scan
```

---

## Bridge Policy

- 로봇 내부에서는 가능한 기본 topic 구조를 유지합니다.
- 중앙 서버 PC에서 domain별 bridge를 운영합니다.
- WF1/WF2의 map server 중복 실행을 피하고, Pinky map을 bridge로 공유합니다.
- 서버-로봇 간 bridge 구간에서만 topic 분리와 remap을 관리합니다.

---

## TODO

- [ ] 최종 domain_bridge 설정 파일 링크
- [ ] `/tf`, `/tf_static` 처리 정책 확정
- [ ] map bridge topic 목록 작성
- [ ] namespace launch 예시 추가
