# CoachFlow smoke test

## Infrastructure

- [ ] `docker compose ps` shows postgres healthy
- [ ] `docker compose logs --tail=50 bot` has no traceback
- [ ] `./scripts/backup_postgres.sh` creates backup
- [ ] `./scripts/test_restore_postgres.sh` succeeds

## Telegram / trainer

- [ ] Trainer `/start` opens trainer menu
- [ ] Trainer can create invite
- [ ] Trainer can create availability slot
- [ ] Trainer can view slots

## Telegram / client

- [ ] Client registers through invite
- [ ] Client accepts privacy consent
- [ ] Client books slot
- [ ] Client sees booking in "Мои записи"
- [ ] Client cancels booking if allowed

## Food reports

- [ ] Client sends meal photo
- [ ] Trainer receives notification
- [ ] Trainer sees report in "На проверку"
- [ ] Trainer marks report as OK
- [ ] Client receives review notification
- [ ] Trainer asks clarification
- [ ] Client answers clarification
- [ ] Trainer sees report again
- [ ] `notification_logs` contains sent rows