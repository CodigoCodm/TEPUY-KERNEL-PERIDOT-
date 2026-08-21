#!/usr/bin/env python3
"""
Tepuy GameMode Patcher v4 - Peridot-U-OSS / KMI-Safe

Target:
    POCO F6 / Peridot / SM8635

Compatible con:
    Xiaomi peridot-u-oss
    Xiaomi Kernel OpenSource

Diseño:
    - tepuy_sysfs.c
    - cpufreq.c
    - thermal_core.c opcional
    - schedutil.c NO se modifica
    - no modifica voltajes
    - no fija una frecuencia concreta
    - GameMode solamente permite utilizar el maximo
      que el kernel ya declara como cpuinfo.max_freq
"""

import os
import shutil
import sys
import subprocess


KERNEL_DIR = sys.argv[1] if len(sys.argv) > 1 else "."
REPO_DIR = os.path.dirname(os.path.abspath(__file__))

ORIGINAL_PERIDOT_REPO = (
    "https://github.com/MiCode/Xiaomi_Kernel_OpenSource.git"
)


# ============================================================
# Helpers
# ============================================================

def error(message):
    print(f"[ERROR] {message}")
    sys.exit(1)


def info(message):
    print(f"[INFO] {message}")


def ok(message):
    print(f"[OK] {message}")


def warning(message):
    print(f"[WARNING] {message}")


def backup(path):
    backup_path = path + ".tepuy.bak"

    if not os.path.exists(backup_path):
        shutil.copy2(path, backup_path)
        info(f"Backup creado: {backup_path}")


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
        errors="replace"
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
# Header
# ============================================================

print("============================================================")
print(" Tepuy GameMode Patcher v4 - Peridot-U-OSS / KMI-Safe")
print(" POCO F6 / Peridot / SM8635")
print("============================================================")
print()


# ============================================================
# 0. Kernel validation
# ============================================================

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


# ============================================================
# Git validation
# ============================================================

info("Comprobando repositorio Git...")

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
                "\n"
                "El workflow esta utilizando el repo "
                "de LineageOS.\n\n"
                "Este patcher esta preparado para "
                "Peridot-U-OSS/Xiaomi source.\n"
            )

        if (
            "Xiaomi_Kernel_OpenSource"
            in remote
        ):

            ok(
                "Repositorio Xiaomi Kernel OpenSource "
                "detectado"
            )

        elif (
            "peridot-dev/android_kernel_xiaomi_sm8635"
            in remote
        ):

            ok(
                "Repositorio Peridot detectado"
            )

        else:

            warning(
                "El remote no coincide exactamente "
                "con un repositorio conocido."
            )

            info(
                "Se continuara porque el workflow "
                "puede utilizar un mirror."
            )

    else:

        info(
            "No se encontro Git remote."
        )

        info(
            "Se continuara utilizando el source local."
        )

except FileNotFoundError:

    warning(
        "Git no esta disponible; "
        "se omitira la comprobacion."
    )

except Exception as exc:

    warning(
        f"No se pudo comprobar Git: {exc}"
    )


# ============================================================
# 1. OpenSSL 3 compatibility
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

        ok(
            "certs/extract-cert.c parcheado "
            "para OpenSSL 3.0"
        )

    else:

        info(
            "certs/extract-cert.c ya esta parcheado "
            "o utiliza otro formato"
        )

else:

    info(
        "certs/extract-cert.c no encontrado; "
        "OpenSSL fix omitido"
    )


# ============================================================
# 2. tepuy_sysfs.c
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

ok(
    "kernel/tepuy_sysfs.c copiado"
)


# ============================================================
# 3. kernel/Makefile
# ============================================================

kernel_makefile = os.path.join(
    KERNEL_DIR,
    "kernel/Makefile"
)

require_file(
    kernel_makefile,
    "kernel/Makefile"
)

content = read_file(kernel_makefile)

if "tepuy_sysfs.o" not in content:

    backup(kernel_makefile)

    if not content.endswith("\n"):
        content += "\n"

    content += (
        "\n"
        "# Tepuy GameMode\n"
        "obj-$(CONFIG_SYSFS) += tepuy_sysfs.o\n"
    )

    write_file(
        kernel_makefile,
        content
    )

    ok(
        "kernel/Makefile actualizado"
    )

else:

    info(
        "tepuy_sysfs.o ya esta presente "
        "en kernel/Makefile"
    )


# ============================================================
# 4. cpufreq.c
# ============================================================

cpufreq_core = os.path.join(
    KERNEL_DIR,
    "drivers/cpufreq/cpufreq.c"
)

cpufreq_patched = False

if os.path.exists(cpufreq_core):

    content = read_file(cpufreq_core)

    # --------------------------------------------------------
    # extern
    # --------------------------------------------------------

    if "extern bool tepuy_game_mode;" not in content:

        backup(cpufreq_core)

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

                ok(
                    "cpufreq.c: declaracion extern agregada"
                )

                break

        if not inserted:

            warning(
                "cpufreq.c: no se encontro include "
                "compatible para insertar extern"
            )

    else:

        info(
            "cpufreq.c: extern ya presente"
        )


    # --------------------------------------------------------
    # GameMode boost
    # --------------------------------------------------------

    boost_marker = (
        "/* TEPuy GameMode boost */"
    )

    if boost_marker not in content:

        target_candidates = [

            "int cpufreq_driver_target("
            "struct cpufreq_policy *policy,",

            "int cpufreq_driver_target("
            "struct cpufreq_policy *policy,",

            "int __cpufreq_driver_target("
            "struct cpufreq_policy *policy,"

        ]

        target = None

        for candidate in target_candidates:

            if candidate in content:

                target = candidate
                break

        if target:

            idx = content.find(target)

            brace_idx = content.find(
                "{",
                idx
            )

            if brace_idx != -1:

                insert = """
\t/* TEPuy GameMode boost */
\tif (tepuy_game_mode &&
\t    policy->max < policy->cpuinfo.max_freq) {
\t\tpolicy->max = policy->cpuinfo.max_freq;
\t}
"""

                content = (
                    content[:brace_idx + 1]
                    + insert
                    + content[brace_idx + 1:]
                )

                cpufreq_patched = True

                ok(
                    "cpufreq.c: GameMode boost agregado"
                )

            else:

                warning(
                    "cpufreq.c: no se encontro apertura "
                    "de funcion target"
                )

        else:

            warning(
                "cpufreq.c: firma cpufreq_driver_target "
                "no encontrada"
            )

            info(
                "Se conserva tepuy_sysfs.c; "
                "no se fuerza un parche incompatible."
            )

    else:

        info(
            "cpufreq.c: GameMode boost ya presente"
        )

        cpufreq_patched = True


    write_file(
        cpufreq_core,
        content
    )

else:

    warning(
        "drivers/cpufreq/cpufreq.c no encontrado"
    )


# ============================================================
# 5. thermal_core.c
#
# IMPORTANTE:
# El source peridot-u-oss puede no utilizar la misma
# implementacion de thermal_zone_device_set_trips().
#
# Por seguridad:
#   - NO se fuerza el parche si la funcion no existe.
#   - NO se hace fallar el build.
#   - GameMode sigue funcionando mediante sysfs/cpufreq.
# ============================================================

thermal_core = os.path.join(
    KERNEL_DIR,
    "drivers/thermal/thermal_core.c"
)

thermal_patched = False

if os.path.exists(thermal_core):

    content = read_file(thermal_core)

    if "extern bool tepuy_game_mode;" not in content:

        thermal_include_candidates = [
            "#include <linux/thermal.h>",
            "#include <linux/thermal.h>\n"
        ]

        inserted = False

        for include in thermal_include_candidates:

            if include in content:

                backup(thermal_core)

                content = content.replace(
                    include,
                    include +
                    "\nextern bool tepuy_game_mode;",
                    1
                )

                inserted = True

                ok(
                    "thermal_core.c: extern agregado"
                )

                break

        if not inserted:

            info(
                "thermal_core.c: no se inserta extern "
                "porque el formato difiere"
            )

    else:

        info(
            "thermal_core.c: extern ya presente"
        )


    # --------------------------------------------------------
    # Buscar variantes de set_trips
    # --------------------------------------------------------

    thermal_targets = [
        "thermal_zone_device_set_trips(",
        "__thermal_zone_device_update(",
    ]

    found_thermal_function = False

    for target in thermal_targets:

        if target in content:

            found_thermal_function = True

            break


    if found_thermal_function:

        info(
            "thermal_core.c: implementacion thermal "
            "compatible detectada"
        )

        info(
            "Parche passive_delay omitido "
            "para preservar estabilidad KMI."
        )

    else:

        info(
            "thermal_core.c: no se encontro "
            "implementacion compatible de set_trips"
        )

        info(
            "Parche thermal omitido correctamente."
        )


    write_file(
        thermal_core,
        content
    )

else:

    info(
        "thermal_core.c no encontrado; "
        "thermal patch omitido"
    )


# ============================================================
# 6. schedutil.c
# ============================================================

print()
info(
    "schedutil.c: OMITIDO deliberadamente"
)

info(
    "No se modifica schedutil para evitar "
    "incompatibilidades KMI."
)


# ============================================================
# 7. Final verification
# ============================================================

print()
print("============================================================")
print(" Verificacion final")
print("============================================================")


# ------------------------------------------------------------
# sysfs
# ------------------------------------------------------------

require_file(
    dst_sysfs,
    "kernel/tepuy_sysfs.c"
)

ok(
    "kernel/tepuy_sysfs.c"
)


# ------------------------------------------------------------
# cpufreq
# ------------------------------------------------------------

if os.path.exists(cpufreq_core):

    cpufreq_check = read_file(cpufreq_core)

    if (
        "extern bool tepuy_game_mode;"
        not in cpufreq_check
    ):

        error(
            "cpufreq.c no contiene "
            "extern bool tepuy_game_mode"
        )

    if (
        "TEPuy GameMode boost"
        not in cpufreq_check
    ):

        warning(
            "cpufreq.c no contiene el marcador "
            "TEPuy GameMode boost."
        )

        warning(
            "Esto significa que el source utiliza "
            "otra implementacion de cpufreq."
        )

    else:

        ok(
            "cpufreq.c: GameMode verificado"
        )


# ------------------------------------------------------------
# thermal
# ------------------------------------------------------------

if os.path.exists(thermal_core):

    thermal_check = read_file(
        thermal_core
    )

    if (
        "extern bool tepuy_game_mode;"
        in thermal_check
    ):

        ok(
            "thermal_core.c: extern verificado"
        )

    else:

        info(
            "thermal_core.c: extern no requerido "
            "por el parche thermal"
        )

    info(
        "thermal_core.c: passive_delay NO es obligatorio"
    )

    info(
        "Se evita modificar la logica thermal "
        "cuando la firma KMI no coincide."
    )


# ============================================================
# Summary
# ============================================================

print()
print("============================================================")
print(" RESULTADO TEPUY")
print("============================================================")

print()
print("SYSFS:")
print("  [OK] tepuy_sysfs.c")

print()
print("CPUFREQ:")

if cpufreq_patched:
    print("  [OK] GameMode boost")
else:
    print("  [INFO] boost no insertado por diferencia KMI")

print()
print("THERMAL:")
print("  [INFO] passive_delay omitido por seguridad")

print()
print("SCHEDUTIL:")
print("  [OK] OMITIDO")

print()
print("Voltajes:")
print("  [OK] NO modificados")

print()
print("Frecuencias:")
print("  [OK] NO se fija una frecuencia concreta")

print()
print("GameMode:")
print(
    "  [OK] utiliza cpuinfo.max_freq cuando "
    "tepuy_game_mode esta activo"
)

print()
print("============================================================")
print(" [OK] Patch Tepuy aplicado sin error fatal")
print("============================================================")
print()

print("Source:")
print(
    "  Xiaomi peridot-u-oss / SM8635"
)

print()
