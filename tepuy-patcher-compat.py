#!/usr/bin/env python3
"""
Tepuy GameMode Patcher v3 - KMI-Safe
Copia tepuy_sysfs.c y hace parches simples en cpufreq.c y thermal_core.c.
OMITE schedutil.c para evitar problemas de compilacion.

Target:
    POCO F6 / Peridot / SM8635

Repo esperado:
    https://github.com/peridot-dev/android_kernel_xiaomi_sm8635.git
"""

import os
import shutil
import sys
import subprocess

KERNEL_DIR = sys.argv[1] if len(sys.argv) > 1 else "."
REPO_DIR = os.path.dirname(os.path.abspath(__file__))

ORIGINAL_PERIDOT_REPO = (
    "https://github.com/peridot-dev/android_kernel_xiaomi_sm8635.git"
)


# ============================================================
# Helpers
# ============================================================

def error(message):
    print(f"[ERROR] {message}")
    sys.exit(1)


def backup(path):
    backup_path = path + ".tepuy.bak"

    if not os.path.exists(backup_path):
        shutil.copy2(path, backup_path)
        print(f"[INFO] Backup creado: {backup_path}")


def require_file(path, description):
    if not os.path.exists(path):
        error(
            f"{description} no encontrado:\n"
            f"{path}"
        )


# ============================================================
# 0. Verify original Peridot repository
# ============================================================

print("============================================================")
print(" Tepuy GameMode Patcher v3 - KMI-Safe")
print(" POCO F6 / Peridot / SM8635")
print("============================================================")
print()

if not os.path.isdir(KERNEL_DIR):
    error(
        f"KERNEL_DIR no existe:\n"
        f"{KERNEL_DIR}"
    )

if not os.path.isfile(
    os.path.join(KERNEL_DIR, "Makefile")
):
    error(
        "El directorio indicado no parece ser "
        "la raiz de un kernel."
    )


print("[INFO] Comprobando repositorio Git...")

try:

    result = subprocess.run(
        [
            "git",
            "-C",
            KERNEL_DIR,
            "remote",
            "-v"
        ],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        check=False
    )

    remote = result.stdout.strip()

    if remote:

        print("[INFO] Git remote:")
        print(remote)

        # ----------------------------------------------------
        # Reject LineageOS
        # ----------------------------------------------------

        if (
            "LineageOS/android_kernel_xiaomi_sm8635"
            in remote
        ):
            error(
                "\n"
                "El workflow esta utilizando el repo "
                "de LineageOS.\n\n"
                "Repo requerido:\n"
                f"  {ORIGINAL_PERIDOT_REPO}\n"
            )

        # ----------------------------------------------------
        # Detect original Peridot
        # ----------------------------------------------------

        if (
            "peridot-dev/android_kernel_xiaomi_sm8635"
            in remote
        ):

            print(
                "[OK] Repo original Peridot detectado"
            )

        else:

            print(
                "[WARNING] El remote Git no coincide "
                "exactamente con peridot-dev."
            )

            print(
                "[INFO] Se continuara porque el workflow "
                "puede estar usando un mirror."
            )

    else:

        print(
            "[INFO] No se encontro Git remote."
        )

        print(
            "[INFO] Se continuara usando el source "
            "local proporcionado."
        )

except FileNotFoundError:

    print(
        "[INFO] Git no esta disponible; "
        "se omitira la comprobacion del remote."
    )

except Exception as exc:

    print(
        f"[INFO] No se pudo comprobar Git: {exc}"
    )


# ============================================================
# FIX: OpenSSL 3.0 compatibility
# ============================================================

extract_cert = os.path.join(
    KERNEL_DIR,
    "certs/extract-cert.c"
)

if os.path.exists(extract_cert):

    with open(
        extract_cert,
        "r",
        encoding="utf-8"
    ) as file:

        content = file.read()

    old_decl = """#ifdef USE_PKCS11_ENGINE
static const char *key_pass;
#endif"""

    new_decl = "static const char *key_pass;"

    if old_decl in content:

        backup(extract_cert)

        content = content.replace(
            old_decl,
            new_decl,
            1
        )

        with open(
            extract_cert,
            "w",
            encoding="utf-8"
        ) as file:

            file.write(content)

        print(
            "[OK] certs/extract-cert.c "
            "patched for OpenSSL 3.0"
        )

    else:

        print(
            "[INFO] certs/extract-cert.c "
            "already patched or different format"
        )

else:

    print(
        "[INFO] certs/extract-cert.c no encontrado; "
        "OpenSSL fix omitido"
    )


# ============================================================
# 1. Copy tepuy_sysfs.c from repo to kernel
# ============================================================

src_sysfs = os.path.join(
    REPO_DIR,
    "tepuy_sysfs.c"
)

dst_sysfs = os.path.join(
    KERNEL_DIR,
    "kernel/tepuy_sysfs.c"
)

require_file(
    src_sysfs,
    "tepuy_sysfs.c del repositorio del patch"
)

require_file(
    os.path.join(KERNEL_DIR, "kernel"),
    "directorio kernel/"
)

if os.path.exists(dst_sysfs):
    backup(dst_sysfs)

shutil.copy2(
    src_sysfs,
    dst_sysfs
)

print(
    "[OK] kernel/tepuy_sysfs.c copied from repo"
)


# ============================================================
# Add tepuy_sysfs.o to kernel/Makefile
# ============================================================

kernel_makefile = os.path.join(
    KERNEL_DIR,
    "kernel/Makefile"
)

require_file(
    kernel_makefile,
    "kernel/Makefile"
)

with open(
    kernel_makefile,
    "r",
    encoding="utf-8"
) as f:

    content = f.read()

if "tepuy_sysfs.o" not in content:

    backup(kernel_makefile)

    with open(
        kernel_makefile,
        "a",
        encoding="utf-8"
    ) as f:

        f.write(
            "\nobj-$(CONFIG_SYSFS) += tepuy_sysfs.o\n"
        )

    print(
        "[OK] kernel/Makefile actualizado"
    )

else:

    print(
        "[INFO] tepuy_sysfs.o ya esta "
        "en kernel/Makefile"
    )


# ============================================================
# 2. drivers/cpufreq/cpufreq.c - Simple boost
# ============================================================

cpufreq_core = os.path.join(
    KERNEL_DIR,
    "drivers/cpufreq/cpufreq.c"
)

if os.path.exists(cpufreq_core):

    with open(
        cpufreq_core,
        "r",
        encoding="utf-8"
    ) as f:

        content = f.read()

    backup(cpufreq_core)

    # --------------------------------------------------------
    # extern declaration
    # --------------------------------------------------------

    if "extern bool tepuy_game_mode;" not in content:

        if "#include <linux/suspend.h>" in content:

            content = content.replace(
                "#include <linux/suspend.h>",
                "#include <linux/suspend.h>\n"
                "extern bool tepuy_game_mode;",
                1
            )

            print(
                "[OK] cpufreq.c: "
                "declaracion extern agregada"
            )

        else:

            print(
                "[INFO] cpufreq.c: "
                "no se encontro lugar para insertar"
            )

    else:

        print(
            "[INFO] cpufreq.c: "
            "ya tiene declaracion"
        )


    # --------------------------------------------------------
    # GameMode boost
    # --------------------------------------------------------

    if (
        "policy->max < policy->cpuinfo.max_freq"
        not in content
    ):

        target = (
            "int cpufreq_driver_target("
            "struct cpufreq_policy *policy,"
        )

        if target in content:

            idx = content.find(target)

            brace_idx = content.find(
                "{",
                idx
            )

            if brace_idx != -1:

                insert = """
\tif (tepuy_game_mode &&
\t    policy->max < policy->cpuinfo.max_freq) {
\t\tpolicy->max =
\t\t\tpolicy->cpuinfo.max_freq;
\t}
"""

                content = (
                    content[:brace_idx + 1]
                    + insert
                    + content[brace_idx + 1:]
                )

                print(
                    "[OK] cpufreq.c: "
                    "boost agregado"
                )

            else:

                print(
                    "[INFO] cpufreq.c: "
                    "no se encontro lugar para insertar boost"
                )

        else:

            print(
                "[INFO] cpufreq.c: "
                "funcion target no encontrada, saltando"
            )

    else:

        print(
            "[INFO] cpufreq.c: "
            "ya tiene logica Tepuy"
        )


    with open(
        cpufreq_core,
        "w",
        encoding="utf-8"
    ) as f:

        f.write(content)

else:

    print(
        "[WARNING] cpufreq.c no encontrado"
    )


# ============================================================
# 3. drivers/thermal/thermal_core.c
# ============================================================

thermal_core = os.path.join(
    KERNEL_DIR,
    "drivers/thermal/thermal_core.c"
)

if os.path.exists(thermal_core):

    with open(
        thermal_core,
        "r",
        encoding="utf-8"
    ) as f:

        content = f.read()

    backup(thermal_core)

    # --------------------------------------------------------
    # extern declaration
    # --------------------------------------------------------

    if "extern bool tepuy_game_mode;" not in content:

        if "#include <linux/thermal.h>" in content:

            content = content.replace(
                "#include <linux/thermal.h>",
                "#include <linux/thermal.h>\n"
                "extern bool tepuy_game_mode;",
                1
            )

            print(
                "[OK] thermal_core.c: "
                "declaracion extern agregada"
            )

        else:

            print(
                "[INFO] thermal_core.c: "
                "no se encontro lugar para insertar"
            )

    else:

        print(
            "[INFO] thermal_core.c: "
            "ya tiene declaracion"
        )


    # --------------------------------------------------------
    # passive delay
    # --------------------------------------------------------

    if "tz->passive_delay = 50;" not in content:

        target = (
            "static int "
            "thermal_zone_device_set_trips("
            "struct thermal_zone_device *tz)"
        )

        if target in content:

            idx = content.find(target)

            brace_idx = content.find(
                "{",
                idx
            )

            if brace_idx != -1:

                insert = """
\tif (tepuy_game_mode &&
\t    tz->passive_delay > 100)
\t\ttz->passive_delay = 50;
"""

                content = (
                    content[:brace_idx + 1]
                    + insert
                    + content[brace_idx + 1:]
                )

                print(
                    "[OK] thermal_core.c: "
                    "passive delay modificado"
                )

            else:

                print(
                    "[INFO] thermal_core.c: "
                    "no se encontro lugar para insertar"
                )

        else:

            print(
                "[INFO] thermal_core.c: "
                "funcion set_trips no encontrada, saltando"
            )

    else:

        print(
            "[INFO] thermal_core.c: "
            "ya tiene logica Tepuy"
        )


    with open(
        thermal_core,
        "w",
        encoding="utf-8"
    ) as f:

        f.write(content)

else:

    print(
        "[WARNING] thermal_core.c no encontrado"
    )


# ============================================================
# 4. kernel/sched/cpufreq_schedutil.c - OMITIDO
# ============================================================

print(
    "[INFO] schedutil.c: omitido "
    "para evitar problemas de compilacion"
)

print(
    "[INFO] GameMode funciona con "
    "tepuy_sysfs.c + cpufreq.c + thermal_core.c"
)


# ============================================================
# Final verification
# ============================================================

print()
print("============================================================")
print(" Verificacion final")
print("============================================================")

require_file(
    dst_sysfs,
    "kernel/tepuy_sysfs.c"
)

print(
    "[OK] kernel/tepuy_sysfs.c"
)


if os.path.exists(cpufreq_core):

    with open(
        cpufreq_core,
        "r",
        encoding="utf-8"
    ) as f:

        cpufreq_check = f.read()

    if "extern bool tepuy_game_mode;" not in cpufreq_check:

        error(
            "cpufreq.c no contiene "
            "extern bool tepuy_game_mode"
        )

    if (
        "policy->max < policy->cpuinfo.max_freq"
        not in cpufreq_check
    ):

        error(
            "cpufreq.c no contiene "
            "la logica de boost Tepuy"
        )

    print(
        "[OK] cpufreq.c verificado"
    )


if os.path.exists(thermal_core):

    with open(
        thermal_core,
        "r",
        encoding="utf-8"
    ) as f:

        thermal_check = f.read()

    if (
        "extern bool tepuy_game_mode;"
        not in thermal_check
    ):

        error(
            "thermal_core.c no contiene "
            "extern bool tepuy_game_mode"
        )

    if (
        "tz->passive_delay = 50;"
        not in thermal_check
    ):

        error(
            "thermal_core.c no contiene "
            "el ajuste passive_delay"
        )

    print(
        "[OK] thermal_core.c verificado"
    )


print()
print("============================================================")
print(" [OK] Todos los parches KMI-safe aplicados.")
print("============================================================")
print()
print("Repo objetivo:")
print(
    "  https://github.com/peridot-dev/"
    "android_kernel_xiaomi_sm8635.git"
)
print()
print("schedutil.c: OMITIDO")
print()
