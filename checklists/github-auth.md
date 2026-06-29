# GitHub 인증 체크리스트

## 기본 원칙

Codex 내부 PTY에서 뜨는 비밀번호 프롬프트는 사용자가 직접 볼 수 없을 수 있다. 사용자가 토큰을 입력해야 하는 상황에서는 보이는 입력 경로를 제공한다.

## 선호 방식

1. 먼저 비대화형 푸시를 시도해 인증이 이미 되어 있는지 확인한다.
2. 인증이 필요하면 내부 PTY 프롬프트에 기대지 않는다.
3. macOS에서는 `GIT_ASKPASS`와 `osascript`를 사용해 사용자 화면에 입력창을 띄운다.
4. 토큰은 채팅, 로그, 파일에 남기지 않는다.
5. 푸시 후 `git status --short --branch`와 `git ls-remote`로 원격 반영을 확인한다.

## 실패 신호

- `Permission ... denied to Alphagoras`
- `could not read Password`
- 사용자가 “아무 화면이 안 뜬다”고 말하는 경우

이 경우 Keychain에 다른 GitHub 계정이 잡혀 있거나, 프롬프트가 내부 터미널에만 떠 있는 상태일 수 있다.
