# EasyGo 결제 독촉(dunning) cron

독촉 사다리는 **cron 이 돌아야만 동작한다.** 커맨드만 있고 스케줄이 없으면
Payment notice 이후 단계가 영원히 안 나가고 자동취소도 안 된다.

| 파일 | 역할 |
|---|---|
| `run.sh` | cron 에서 management command 를 실행하는 공용 러너 (경로 자동 인식 · flock 중복 방지 · 로그 · 실패 알림) |
| `easygo-dunning.crontab` | 스케줄 정의 (`__PROJECT_ROOT__` 는 설치 시 실제 경로로 치환) |
| `install_crontab.sh` | 기존 crontab 을 보존하면서 이 블록만 넣거나 갱신 |

## 스케줄

| 작업 | 주기 | 이유 |
|---|---|---|
| `no_payment_yet` | 매시 :05 | 사다리 임계값이 시간 단위(dep 72h/48h, arr 96h/72h)라 매시간 판정해야 제때 나간다 |
| `auto_cancel_pending` | 매시 :35 | 같은 시간대에 예고와 취소가 동시에 판정되지 않도록 30분 뒤 |
| `final_notice` (SMS) | 매일 09:10 | 문자는 새벽에 보내면 안 됨 |
| `send_final_warning` | 매일 09:20 | 픽업 21일 초과 미결제 건 안내, 하루 1회면 충분 |

## 설치 (실서버에서)

```bash
cd /경로/easygo
git pull

# 1) 무엇이 설치될지 먼저 확인 — 실제로 반영하지 않는다
scripts/cron/install_crontab.sh --dry-run

# 2) 기존 crontab 에 이미 같은 커맨드가 있는지 확인 (이중 실행 방지)
crontab -l | grep -E 'no_payment_yet|auto_cancel_pending|final_notice|send_final_warning'

# 3) 설치 (기존 줄은 보존, 설치 전 백업 자동 생성)
scripts/cron/install_crontab.sh

# 4) 확인
crontab -l | grep run.sh
```

되돌리기: `crontab logs/cron/crontab.backup.<시각>` 또는
`scripts/cron/install_crontab.sh --uninstall`.

## 설치 전 확인할 것

**① 서버 시간대.** cron 은 서버 시스템 시간으로 스케줄을 읽고, Django 는
`Australia/Sydney` 로 동작한다. 다르면 매일 작업(SMS 포함)이 손님 기준 새벽에
나간다. 매시간 작업은 영향 없다.

```bash
date                      # 서버 시간
TZ=Australia/Sydney date  # 시드니 시간 — 다르면 crontab 의 09:10/09:20 을 조정
```

**② venv 경로.** `run.sh` 는 `<프로젝트루트>/venv/bin/python` 을 쓴다. 실서버
venv 위치가 다르면 `run.sh` 의 `PYTHON` 을 고친다.

**③ 첫 실행은 dry-run 으로.** 실제 발송/취소 전에 대상 건수를 눈으로 본다.

```bash
scripts/cron/run.sh no_payment_yet --dry-run
scripts/cron/run.sh auto_cancel_pending --dry-run
```

`--dry-run` 은 `no_payment_yet` / `auto_cancel_pending` 만 지원한다.
`final_notice` 는 dry-run 이 없으므로 SMS 가 실제로 나간다 — 먼저
`logs/cron/no_payment_yet.log` 로 사다리가 정상인지 확인한 뒤 넣는 게 안전하다.

## 운영

```bash
tail -f logs/cron/no_payment_yet.log      # 진행 상황
grep '✘' logs/cron/*.log                  # 실패만
grep '⏭' logs/cron/*.log                  # 이전 실행과 겹쳐 건너뛴 경우
```

- 로그는 `logs/cron/<command>.log`, 10MB 넘으면 `.log.1` 로 1회 회전.
- 실패 시에만 stderr 로 한 줄 → crontab 의 `MAILTO` 로 메일 (MTA 없으면 무시).
- `flock` 으로 같은 커맨드가 겹쳐 돌지 않는다. 겹치면 그 회차는 건너뛰고
  다음 시간에 다시 판정하므로 단계를 놓치지 않는다.
