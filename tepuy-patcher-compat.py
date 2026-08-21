#!/usr/bin/env python3
"""
Tepuy GameMode Patcher v3 - KMI-Safe
POCO F6 / Peridot / SM8635

Mantiene la estructura del patcher original funcional.

Parchea únicamente:
    kernel/tepuy_sysfs.c
    kernel/Makefile
    drivers/cpufreq/cpufreq.c
    drivers/thermal/thermal_core.c

OMITE:
    kernel/sched/cpufreq_schedutil.c
    drivers GPU
    drivers QCOM propietarios
    Kconfig
    Makefile externos
"""

import os
import shutil
import sys


KERNEL_DIR = sys.argv[1] if len(sys.argv) > 1 else "."
REPO_DIR = os.path.dirname(os.path.abspath(__file__))


# ============================================================
# Helpers
# ============================================================

def fail(message):
    print("[ERROR] " + message)
    sys.exit(1)


def read_file(path):
    with open(path, "r", encoding="utf-8") as f:
        return f.read()


def write_file(path, content):
    with open(path, "w", encoding="utf-8") as f:
        f.write(content)


# ============================================================
# Header
# ============================================================

print("============================================================")
print(" Tepuy GameMode Patcher v3 - KMI-Safe")
print(" POCO F6 / Peridot / SM8635")
print("============================================================")
print()


# ============================================================
# 0. Basic kernel validation
# ============================================================

if not os.path.isdir(KERNEL_DIR):
    fail(
        "KERNEL_DIR no existe:\n"
        + KERNEL_DIR
    )

if not os.path.isfile(
    os.path.join(KERNEL_DIR, "Makefile")
):
    fail(
        "El directorio indicado no parece ser "
        "la raiz de un kernel."
    )

print("[OK] Kernel source encontrado:")
print("     " + KERNEL_DIR)


# ============================================================
# FIX: OpenSSL 3.0 compatibility
# ============================================================

extract_cert = os.path.join(
    KERNEL_DIR,
    "certs/extract-cert.c"
)

if os.path.exists(extract_cert):

    content = read_file(extract_cert)

    old_decl = """#ifdef USE_PKCS11_ENGINE
static const char *key_pass;
#endif"""

    new_decl = "static const char *key_pass;"

    if old_decl in content:

        content = content.replace(
            old_decl,
            new_decl,
            1
        )

        write_file(
            extract_cert,
            content
        )

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
# 1. Copy tepuy_sysfs.c
# ============================================================

src_sysfs = os.path.join(
    REPO_DIR,
    "tepuy_sysfs.c"
)

dst_sysfs = os.path.join(
    KERNEL_DIR,
    "kernel/tepuy_sysfs.c"
)

if not os.path.exists(src_sysfs):

    fail(
        "tepuy_sysfs.c no encontrado en el repositorio.\n"
        "Debe estar en la raiz del proyecto."
    )

if not os.path.isdir(
    os.path.join(KERNEL_DIR, "kernel")
):

    fail(
        "Directorio kernel/ no encontrado."
    )


shutil.copy2(
    src_sysfs,
    dst_sysfs
)

print(
    "[OK] kernel/tepuy_sysfs.c copied from repo"
)


# ============================================================
# 1.1 Add tepuy_sysfs.o to kernel/Makefile
# ============================================================

kernel_makefile = os.path.join(
    KERNEL_DIR,
    "kernel/Makefile"
)

if not os.path.exists(kernel_makefile):

    fail(
        "kernel/Makefile no encontrado."
    )

content = read_file(
    kernel_makefile
)

if "tepuy_sysfs.o" not in content:

    with open(
        kernel_makefile,
        "a",
        encoding="utf-8"
    ) as f:

        f.write(
            "\n"
            "obj-$(CONFIG_SYSFS) += tepuy_sysfs.o\n"
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
# 2. drivers/cpufreq/cpufreq.c
# ============================================================

cpufreq_core = os.path.join(
    KERNEL_DIR,
    "drivers/cpufreq/cpufreq.c"
)

if os.path.exists(cpufreq_core):

    content = read_file(
        cpufreq_core
    )


    # --------------------------------------------------------
    # extern declaration
    # --------------------------------------------------------

    if "extern bool tepuy_game_mode;" not in content:

        include = "#include <linux/suspend.h>"

        if include in content:

            content = content.replace(
                include,
                include
                + "\n"
                + "extern bool tepuy_game_mode;",
                1
            )

            print(
                "[OK] cpufreq.c: "
                "declaracion extern agregada"
            )

        else:

            print(
                "[INFO] cpufreq.c: "
                "no se encontro linux/suspend.h"
            )

    else:

        print(
            "[INFO] cpufreq.c: "
            "ya tiene declaracion"
        )


    # --------------------------------------------------------
    # GameMode boost
    # --------------------------------------------------------

    if "tepuy_game_mode" not in content:

        target = (
            "int cpufreq_driver_target("
            "struct cpufreq_policy *policy,"
        )

        if target in content:

            idx = content.find(
                target
            )

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
                    "no se encontro brace "
                    "de cpufreq_driver_target"
                )

        else:

            print(
                "[INFO] cpufreq.c: "
                "funcion target no encontrada, "
                "saltando"
            )

    else:

        print(
            "[INFO] cpufreq.c: "
            "ya contiene Tepuy"
        )


    write_file(
        cpufreq_core,
        content
    )

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

    content = read_file(
        thermal_core
    )


    # --------------------------------------------------------
    # extern declaration
    # --------------------------------------------------------

    if "extern bool tepuy_game_mode;" not in content:

        include = "#include <linux/thermal.h>"

        if include in content:

            content = content.replace(
                include,
                include
                + "\n"
                + "extern bool tepuy_game_mode;",
                1
            )

            print(
                "[OK] thermal_core.c: "
                "declaracion extern agregada"
            )

        else:

            print(
                "[INFO] thermal_core.c: "
                "no se encontro linux/thermal.h"
            )

    else:

        print(
            "[INFO] thermal_core.c: "
            "ya tiene declaracion"
        )


    # --------------------------------------------------------
    # passive delay
    # --------------------------------------------------------

    if "tepuy_game_mode" not in content:

        target = (
            "static int "
            "thermal_zone_device_set_trips("
            "struct thermal_zone_device *tz)"
        )

        if target in content:

            idx = content.find(
                target
            )

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
                    "no se encontro brace "
                    "de set_trips"
                )

        else:

            print(
                "[INFO] thermal_core.c: "
                "funcion set_trips no encontrada, "
                "saltando"
            )

    else:

        print(
            "[INFO] thermal_core.c: "
            "ya contiene Tepuy"
        )


    write_file(
        thermal_core,
        content
    )

else:

    print(
        "[WARNING] thermal_core.c no encontrado"
    )


# ============================================================
# 4. schedutil - OMITIDO
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
# 5. Final verification
# ============================================================

print()
print("============================================================")
print(" Verificacion final")
print("============================================================")


# ------------------------------------------------------------
# tepuy_sysfs.c
# ------------------------------------------------------------

if not os.path.exists(dst_sysfs):

    fail(
        "kernel/tepuy_sysfs.c no fue instalado."
    )

print(
    "[OK] kernel/tepuy_sysfs.c"
)


# ------------------------------------------------------------
# kernel Makefile
# ------------------------------------------------------------

makefile_check = read_file(
    kernel_makefile
)

if "tepuy_sysfs.o" not in makefile_check:

    fail(
        "kernel/Makefile no contiene tepuy_sysfs.o"
    )

print(
    "[OK] kernel/Makefile"
)


# ------------------------------------------------------------
# cpufreq
# ------------------------------------------------------------

if os.path.exists(cpufreq_core):

    cpufreq_check = read_file(
        cpufreq_core
    )

    if "extern bool tepuy_game_mode;" in cpufreq_check:

        print(
            "[OK] cpufreq.c extern verificado"
        )

    else:

        fail(
            "cpufreq.c no contiene "
            "extern bool tepuy_game_mode"
        )

    if (
        "policy->max ="
        in cpufreq_check
        and
        "policy->cpuinfo.max_freq"
        in cpufreq_check
    ):

        print(
            "[OK] cpufreq.c boost verificado"
        )

    else:

        print(
            "[WARNING] cpufreq.c boost "
            "no pudo verificarse"
        )


# ------------------------------------------------------------
# thermal
# ------------------------------------------------------------

if os.path.exists(thermal_core):

    thermal_check = read_file(
        thermal_core
    )

    if "extern bool tepuy_game_mode;" in thermal_check:

        print(
            "[OK] thermal_core.c extern verificado"
        )

    else:

        fail(
            "thermal_core.c no contiene "
            "extern bool tepuy_game_mode"
        )

    if "tz->passive_delay = 50;" in thermal_check:

        print(
            "[OK] thermal_core.c passive_delay verificado"
        )

    else:

        print(
            "[WARNING] thermal_core.c passive_delay "
            "no pudo verificarse"
        )


# ============================================================
# Final
# ============================================================

print()
print("============================================================")
print(" [OK] Tepuy KMI-safe patch aplicado")
print("============================================================")
print()
print("Target: POCO F6 / Peridot / SM8635")
print()
print("Defconfig recomendado:")
print("  peridot_defconfig")
print()
print("Parcheados:")
print("  kernel/tepuy_sysfs.c")
print("  kernel/Makefile")
print("  drivers/cpufreq/cpufreq.c")
print("  drivers/thermal/thermal_core.c")
print()
print("Omitido:")
print("  kernel/sched/cpufreq_schedutil.c")
print("  GPU drivers")
print("  QCOM vendor drivers")
print("  Kconfig")
print()
