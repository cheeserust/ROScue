# Folder Structure

ROScue 레포지토리의 폴더 구성 원칙입니다.

## Principle

최상위 `README.md`는 프로젝트 소개와 문서 링크 허브로만 사용합니다. 세부 기술 설명은 `docs/` 하위 폴더의 `README.md`에 섹션 단위로 정리합니다.

```text
root README.md
  → 짧은 프로젝트 소개 + Documentation 링크

docs/<category>/README.md
  → 해당 카테고리의 전체 내용
  → 세부 파일로 쪼개지 않고 섹션과 목차로 이동
```

## Recommended Structure

```text
ROScue/
├── README.md
├── FOLDER_STRUCTURE.md
├── docs/
│   ├── README.md
│   ├── scenario/README.md
│   ├── setup/README.md
│   ├── runbook/README.md
│   ├── ros_interfaces/README.md
│   ├── architecture/README.md
│   ├── navigation/README.md
│   ├── perception/README.md
│   ├── manipulation/README.md
│   ├── llm_rag/README.md
│   ├── embedded/README.md
│   ├── web/README.md
│   ├── troubleshooting/README.md
│   └── assets/README.md
├── ros2_ws/README.md
├── web/README.md
├── ai/README.md
├── embedded/README.md
├── maps/README.md
├── models/README.md
├── scripts/README.md
└── tests/README.md
```

## Why one README per category?

GitHub에서 폴더를 클릭하면 해당 폴더 안의 `README.md`가 자동으로 표시됩니다. 따라서 사용자는 최상위 README의 링크를 클릭한 뒤, 같은 페이지 안의 섹션 목차를 통해 필요한 내용으로 이동할 수 있습니다.

## Section Anchor Rule

각 카테고리 README에는 아래처럼 명시적 anchor를 둡니다.

```md
## On this page

- [System Architecture](#system-architecture)
- [Hardware Architecture](#hardware-architecture)

<a id="system-architecture"></a>
## 1. System Architecture

...
```

한국어 제목의 자동 anchor는 환경에 따라 불편할 수 있으므로, 영어 기반 id를 직접 지정하는 방식을 권장합니다.
