# Bomb_A

## label
Bomb_A

## type
registered_device

## summary
Bomb_A는 프로젝트에 등록된 객체입니다.
이 절차는 Bomb_A label이 확인된 경우에만 사용합니다.

## procedure
1. Step 1: 오른쪽에 모여있는 세 개의 버튼 중에 가운데 버튼을 누릅니다.
2. Step 2: 가장 왼쪽에 있는 버튼을 누릅니다.
3. Step 3: 가장 오른쪽에 있는 버튼을 누릅니다.
4. 버튼 사이에 있는 점퍼선 2개(주황, 노랑)를 뽑습니다. 
5. LCD의 전원이 꺼졌다면 해체 성공입니다.

## failure_condition
- 순서가 틀리면 타이머가 10초씩 줄어듭니다.
- 타이머가 계속 동작하면 완료로 판단하지 않습니다.
- 타이머가 0초가 되면 실패입니다.

## response_rule
- Bomb_A 절차만 안내합니다.
- 버튼 순서를 바꾸지 않습니다.
- 문서에 없는 추가 절차를 만들지 않습니다.
- 등록되지 않은 객체에 대해서는 절차를 안내하지 않습니다.

---

# Bomb_B

## label
Bomb_B

## type
registered_device

## summary
Bomb_B는 프로젝트에 등록된 객체입니다.
이 절차는 Bomb_B label이 확인된 경우에만 사용합니다.

## procedure
1. Step 1: A(왼쪽) 버튼 입력 (Green LED ON)
2. Step 2: B(오른쪽) 버튼 입력 (Green LED ON)
3. Step 3: A(왼쪽) 버튼 입력 (Green LED ON)
4. Step 4: A(왼쪽) 버튼 + B(오른쪽) 버튼 동시 입력
5. Step 5: 조이스틱 하단 방향 조작
6. Step 6: 조이스틱 좌측 방향 조작
7. Step 7: Yellow LED 점등 시 해체 성공

## failure_condition
- 순서가 틀리면 실패 처리합니다.
- 카운트다운 시간 내 미완료 시 RED LED 점등

## response_rule
- Bomb_B 절차만 안내합니다.
- 버튼 순서를 바꾸지 않습니다.
- 문서에 없는 추가 절차를 만들지 않습니다.
- 등록되지 않은 객체에 대해서는 절차를 안내하지 않습니다.

---

# Empty

## label
Empty

## type
empty_box

## summary
등록된 객체가 탐지되지 않은 상태입니다.

## response_rule
- 등록된 객체가 탐지되지 않았다고 안내합니다.
- 화면 가림이나 낮은 신뢰도가 있으면 재확인을 요청합니다.
