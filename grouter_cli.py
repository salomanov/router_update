#!/usr/bin/env python3
"""grouter — router-side CLI for the GRouter profile.

Runs the same code paths as the web panel, without needing an HTTP session:

    grouter plan        # what is missing / outdated compared to configs/profile.json
    grouter apply       # install missing packages and services (idempotent)
    grouter status      # services, versions, update availability
    grouter update-all  # upgrade every package that has a newer version

Exit codes: 0 = ok, 1 = failure, 2 = plan has drift.
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import router_api as api  # noqa: E402


def print_plan(plan):
    profile = plan.get("profile") or {}
    print("Профиль: %s" % profile.get("name", "default"))
    print("Пакеты: %s" % (", ".join(profile.get("packages") or []) or "—"))
    print("")

    for item in plan.get("items") or []:
        state = item.get("state")
        marker = {"ok": "[ok]  ", "missing": "[!!]  ", "outdated": "[up]  "}.get(state, "[?]   ")
        current = item.get("current") or "—"
        available = item.get("available")
        line = "%s%-28s %-10s %s" % (marker, item.get("name"), current, state)
        if available and available != current:
            line += " -> %s" % available
        print(line)

    summary = plan.get("summary") or {}
    print("")
    print("Не установлено: %s" % (", ".join(summary.get("missing") or []) or "нет"))
    print("Устарело:       %s" % (", ".join(summary.get("outdated") or []) or "нет"))
    if plan.get("extra"):
        print("Вне профиля:    %s" % ", ".join(plan["extra"]))
    print("")
    print("Состояние: %s" % ("в порядке" if plan.get("in_sync") else "требуется apply"))


def print_steps(result):
    for step in result.get("steps") or []:
        status = "OK  " if step.get("ok") else "FAIL"
        print("[%s] %s" % (status, step.get("step")))
        output = (step.get("output") or "").strip()
        if output:
            for line in output.splitlines()[-15:]:
                print("       %s" % line)
    print("")


def cmd_plan():
    plan = api.build_plan()
    print_plan(plan)
    return 0 if plan.get("in_sync") else 2


def cmd_apply():
    print("Применение профиля...")
    result = api.apply_plan()
    print_steps(result)
    print_plan(result.get("plan") or {})
    return 0 if result.get("success") else 1


def cmd_status():
    services = api.discover_services(force=True)
    statuses = api.get_service_statuses(services, force=True)
    versions = api.get_installed_versions(force=True)
    repo_versions = api.get_all_opkg_repo_versions()

    print("%-28s %-10s %-18s %s" % ("СЛУЖБА", "СТАТУС", "ВЕРСИЯ", "ОБНОВЛЕНИЕ"))
    for s_id, info in sorted(services.items()):
        current = versions.get(s_id) or "—"
        available = repo_versions.get(info.get("package")) if info.get("package") else None
        update = "да -> %s" % available if api.is_newer_version(available, current) else "нет"
        print("%-28s %-10s %-18s %s" % (
            s_id, statuses.get(s_id, "?"), current, update))

    plan = api.build_plan()
    summary = plan.get("summary") or {}
    print("")
    print("Профиль: не установлено %d, устарело %d"
          % (len(summary.get("missing") or []), len(summary.get("outdated") or [])))
    return 0


def cmd_update_all():
    print("Обновление пакетов...")
    result = api.update_all_packages()
    for row in result.get("results") or []:
        print("%-24s %-12s %s" % (row.get("target"), row.get("state"),
                                  row.get("available") or row.get("current") or ""))
        if row.get("state") == "error" and row.get("output"):
            print("    %s" % (row["output"] or "").strip()[-300:])
    summary = result.get("summary") or {}
    print("")
    print("Обновлено: %d, актуальных: %d, ошибок: %d" % (
        summary.get("updated", 0), summary.get("up_to_date", 0), summary.get("errors", 0)))
    return 0 if result.get("success") else 1


COMMANDS = {
    "plan": cmd_plan,
    "apply": cmd_apply,
    "status": cmd_status,
    "update-all": cmd_update_all,
    "update_all": cmd_update_all,
}


def main(argv):
    if len(argv) < 2 or argv[1] in ("-h", "--help", "help"):
        print(__doc__.strip())
        return 0
    command = COMMANDS.get(argv[1])
    if not command:
        print("Неизвестная команда: %s" % argv[1], file=sys.stderr)
        print("Доступно: %s" % ", ".join(sorted(set(COMMANDS))), file=sys.stderr)
        return 1
    return command()


if __name__ == "__main__":
    sys.exit(main(sys.argv))
