#!/usr/bin/env python3

"""
Tepuy GameMode Patcher - Peridot U OSS compatible

Target:
    POCO F6 / Peridot
    Redmi Turbo 3
    SM8635
    Xiaomi peridot-u-oss

Principios:
    - Mantener el source original Xiaomi.
    - No modificar voltajes.
    - No fijar frecuencias.
    - No tocar schedutil.
    - Liberar los limites cpufreq cuando GameMode esta activo.
    - Thermal patch opcional/adaptativo.
"""

import os
import shutil
import sys
import subprocess


KERNEL_DIR = os.path.abspath(
    sys.argv[1] if len(sys.argv) > 1 else "."
)

REPO_DIR = os.path.dirname(
    os.path.abspath(__file__)
)

EXPECTED_REPO = (
    "https://github.com/MiCode/"
    "Xiaomi_Kernel_OpenSource.git"
)

EXPECTED_BRANCH = "peridot-u-oss"


# ============================================================
# HELPERS
# ============================================================

def error(message):
    print(f"[ERROR] {message}")
    sys.exit(1)


def backup(path):

    backup_path = path + ".tepuy.bak"

    if not os.path.exists(backup_path):

        shutil.copy2(
            path,
            backup_path
        )

        print(
            f"[INFO] Backup creado: {backup_path}"
        )


def require_file(path, description):

    if not os.path.exists(path):

        error(
            f"{description} no encontrado:\n"
            f"{path}"
        )


def read_file(path):

    with open(
        path,
        "r",
        encoding="utf-8",
        errors="ignore"
    ) as f:

        return f.read()


def write_file(path, content):

    with open(
        path,
        "w",
        encoding="utf-8"
    ) as f:

        f.write(content)


# ============================================================
# HEADER
# ============================================================

print("============================================================")
print(" Tepuy GameMode Patcher")
print(" Peridot U OSS / KMI-Safe")
print(" POCO F6 / Peridot / SM8635")
print("============================================================")
print()


# ============================================================
# SOURCE CHECK
# ============================================================

if not os.path.isdir(KERNEL_DIR):

    error(
        f"KERNEL_DIR no existe:\n"
        f"{KERNEL_DIR}"
    )


require_file(
    os.path.join(KERNEL_DIR, "Makefile"),
    "Makefile"
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

        if (
            "LineageOS/android_kernel_xiaomi_sm8635"
            in remote
        ):

            error(
                "Se detecto un repositorio "
                "LineageOS.\n"
                "Este patcher requiere el source "
                "Xiaomi peridot-u-oss."
            )

        if (
            "MiCode/Xiaomi_Kernel_OpenSource"
            in remote
        ):

            print(
                "[OK] Xiaomi Kernel OpenSource detectado"
            )

        else:

            print(
                "[WARNING] Remote diferente al esperado."
            )

            print(
                "[WARNING] Se continua porque puede "
                "existir un mirror."
            )

    else:

        print(
            "[INFO] Sin Git remote."
        )

except Exception as exc:

    print(
        f"[INFO] No se pudo comprobar Git: {exc}"
    )


# ============================================================
# 1. OPENSSL COMPATIBILITY
# ============================================================

extract_cert = os.path.join(
    KERNEL_DIR,
    "certs/extract-cert.c"
)


if os.path.exists(extract_cert):

    content = read_file(
        extract_cert
    )

    old_decl = """#ifdef USE_PKCS11_ENGINE
static const char *key_pass;
#endif"""

    new_decl = (
        "static const char *key_pass;"
    )

    if old_decl in content:

        backup(extract_cert)

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
            "[OK] extract-cert.c "
            "OpenSSL compatibility aplicada"
        )

    else:

        print(
            "[INFO] extract-cert.c "
            "ya compatible o formato diferente"
        )


# ============================================================
# 2. TEPUY SYSFS
# ============================================================

src_sysfs = os.path.join(
    REPO_DIR,
    "tepuy_sysfs.c"
)

dst_sysfs = os.path.join(
    KERNEL_DIR,
    "kernel",
    "tepuy_sysfs.c"
)


require_file(
    src_sysfs,
    "tepuy_sysfs.c del repositorio Tepuy"
)


if os.path.exists(dst_sysfs):

    backup(
        dst_sysfs
    )


shutil.copy2(
    src_sysfs,
    dst_sysfs
)


print(
    "[OK] kernel/tepuy_sysfs.c instalado"
)


# ============================================================
# 3. KERNEL MAKEFILE
# ============================================================

kernel_makefile = os.path.join(
    KERNEL_DIR,
    "kernel",
    "Makefile"
)


require_file(
    kernel_makefile,
    "kernel/Makefile"
)


content = read_file(
    kernel_makefile
)


if "tepuy_sysfs.o" not in content:

    backup(
        kernel_makefile
    )

    with open(
        kernel_makefile,
        "a",
        encoding="utf-8"
    ) as f:

        f.write(
            "\n"
            "# Tepuy GameMode\n"
            "obj-$(CONFIG_SYSFS) += tepuy_sysfs.o\n"
        )

    print(
        "[OK] kernel/Makefile actualizado"
    )

else:

    print(
        "[INFO] tepuy_sysfs.o ya presente"
    )


# ============================================================
# 4. CPUFREQ
# ============================================================

cpufreq_core = os.path.join(
    KERNEL_DIR,
    "drivers",
    "cpufreq",
    "cpufreq.c"
)


if not os.path.exists(cpufreq_core):

    print(
        "[WARNING] drivers/cpufreq/cpufreq.c "
        "no existe"
    )

else:

    content = read_file(
        cpufreq_core
    )

    original = content

    # --------------------------------------------------------
    # EXTERN
    # --------------------------------------------------------

    if "extern bool tepuy_game_mode;" not in content:

        include_candidates = [
            "#include <linux/suspend.h>",
            "#include <linux/cpufreq.h>",
            "#include <linux/kernel.h>"
        ]

        inserted = False

        for include in include_candidates:

            if include in content:

                content = content.replace(
                    include,
                    include +
                    "\nextern bool tepuy_game_mode;",
                    1
                )

                inserted = True

                print(
                    "[OK] cpufreq.c: extern agregado"
                )

                break

        if not inserted:

            print(
                "[WARNING] No se encontro include "
                "compatible para extern"
            )

    # --------------------------------------------------------
    # BOOST
    # --------------------------------------------------------

    boost_marker = (
        "policy->max < policy->cpuinfo.max_freq"
    )

    if boost_marker not in content:

        target_patterns = [

            "int cpufreq_driver_target("
            "(struct cpufreq_policy *policy,",

            "int cpufreq_driver_target("
            "struct cpufreq_policy *policy,"

        ]

        target = None

        for candidate in target_patterns:

            if candidate in content:

                target = candidate
                break

        if target:

            idx = content.find(
                target
            )

            brace_idx = content.find(
                "{",
                idx
            )

            if brace_idx != -1:

                insert = """
    /*
     * Tepuy GameMode:
     * libera el limite maximo de la policy.
     *
     * No cambia voltaje.
     * No fija una frecuencia.
     * Solo permite utilizar el maximo
     * declarado por el driver.
     */
    if (tepuy_game_mode &&
        policy->max < policy->cpuinfo.max_freq) {
        policy->max = policy->cpuinfo.max_freq;
    }
"""

                content = (
                    content[:brace_idx + 1]
                    + insert
                    + content[brace_idx + 1:]
                )

                print(
                    "[OK] cpufreq.c: GameMode boost agregado"
                )

            else:

                print(
                    "[WARNING] No se encontro "
                    "brace de cpufreq_driver_target"
                )

        else:

            print(
                "[WARNING] cpufreq_driver_target "
                "no encontrado."
            )

            print(
                "[INFO] Se omite boost cpufreq "
                "para mantener compatibilidad."
            )

    else:

        print(
            "[INFO] cpufreq.c: boost Tepuy "
            "ya presente"
        )

    if content != original:

        backup(
            cpufreq_core
        )

        write_file(
            cpufreq_core,
            content
        )


# ============================================================
# 5. THERMAL - OPTIONAL
# ============================================================

thermal_core = os.path.join(
    KERNEL_DIR,
    "drivers",
    "thermal",
    "thermal_core.c"
)


thermal_patched = False


if not os.path.exists(thermal_core):

    print(
        "[INFO] thermal_core.c no encontrado."
    )

else:

    content = read_file(
        thermal_core
    )

    original = content

    # --------------------------------------------------------
    # EXTERN
    # --------------------------------------------------------

    if "extern bool tepuy_game_mode;" not in content:

        includes = [
            "#include <linux/thermal.h>",
            "#include <linux/kernel.h>"
        ]

        inserted = False

        for include in includes:

            if include in content:

                content = content.replace(
                    include,
                    include +
                    "\nextern bool tepuy_game_mode;",
                    1
                )

                inserted = True

                print(
                    "[OK] thermal_core.c: extern agregado"
                )

                break

        if not inserted:

            print(
                "[INFO] thermal_core.c: "
                "no se encontro include compatible"
            )

    # --------------------------------------------------------
    # ONLY PATCH IF REAL FUNCTION EXISTS
    # --------------------------------------------------------

    thermal_targets = [

        "static int thermal_zone_device_set_trips(",

        "int thermal_zone_device_set_trips(",

        "static void thermal_zone_device_set_trips("

    ]

    thermal_target = None

    for candidate in thermal_targets:

        if candidate in content:

            thermal_target = candidate
            break


    if thermal_target:

        marker = (
            "tz->passive_delay = 50;"
        )

        if marker not in content:

            idx = content.find(
                thermal_target
            )

            brace_idx = content.find(
                "{",
                idx
            )

            if brace_idx != -1:

                insert = """
    /*
     * Tepuy GameMode thermal response.
     * Only reduce an excessive passive delay.
     */
    if (tepuy_game_mode &&
        tz->passive_delay > 100)
        tz->passive_delay = 50;
"""

                content = (
                    content[:brace_idx + 1]
                    + insert
                    + content[brace_idx + 1:]
                )

                thermal_patched = True

                print(
                    "[OK] thermal_core.c: "
                    "passive_delay agregado"
                )

    else:

        print(
            "[INFO] thermal_core.c: "
            "set_trips no existe en este source."
        )

        print(
            "[INFO] Thermal patch omitido "
            "intencionalmente."
        )


    if content != original:

        backup(
            thermal_core
        )

        write_file(
            thermal_core,
            content
        )


# ============================================================
# 6. SCHEDUTIL
# ============================================================

print(
    "[INFO] schedutil.c: OMITIDO"
)

print(
    "[INFO] No se modifica schedutil "
    "para maximizar compatibilidad KMI."
)


# ============================================================
# 7. FINAL VERIFICATION
# ============================================================

print()
print("============================================================")
print(" VERIFICACION FINAL")
print("============================================================")


require_file(
    dst_sysfs,
    "kernel/tepuy_sysfs.c"
)

print(
    "[OK] kernel/tepuy_sysfs.c"
)


# ------------------------------------------------------------
# CPU verification
# ------------------------------------------------------------

if os.path.exists(cpufreq_core):

    content = read_file(
        cpufreq_core
    )

    if (
        "extern bool tepuy_game_mode;"
        in content
    ):

        print(
            "[OK] cpufreq.c: extern"
        )

    else:

        print(
            "[WARNING] cpufreq.c: extern "
            "no encontrado"
        )


    if (
        "policy->max < policy->cpuinfo.max_freq"
        in content
    ):

        print(
            "[OK] cpufreq.c: GameMode boost"
        )

    else:

        print(
            "[WARNING] cpufreq.c: GameMode "
            "boost no aplicado"
        )


# ------------------------------------------------------------
# Thermal verification
# ------------------------------------------------------------

if os.path.exists(thermal_core):

    content = read_file(
        thermal_core
    )

    if (
        "tz->passive_delay = 50;"
        in content
    ):

        print(
            "[OK] thermal_core.c: "
            "passive_delay"
        )

    else:

        print(
            "[INFO] thermal_core.c: "
            "passive_delay no aplicado"
        )

        print(
            "[INFO] Esto NO es un error."
        )


# ============================================================
# DONE
# ============================================================

print()
print("============================================================")
print(" [OK] TEPUY PATCH COMPLETADO")
print("============================================================")
print()
print("Source:")
print(
    "  MiCode/Xiaomi_Kernel_OpenSource"
)

print()
print("Branch:")
print(
    f"  {EXPECTED_BRANCH}"
)

print()
print("GameMode:")
print(
    "  cpufreq boost: adaptativo"
)

print(
    "  thermal patch: opcional"
)

print(
    "  schedutil: omitido"
)

print()
print(
    "Voltajes: SIN MODIFICAR"
)

print(
    "Frecuencias: NO FIJADAS"
)

print()
