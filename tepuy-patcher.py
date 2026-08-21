#!/usr/bin/env python3
"""Tepuy GameMode Patcher + OpenSSL 3.0 fix"""

import os
import sys
import subprocess
import shutil

KERNEL_DIR = sys.argv[1] if len(sys.argv) > 1 else "."

# ============================================================
# Repository validation
# Target: original Peridot kernel
# peridot-dev/android_kernel_xiaomi_sm8635
#
# The repository itself is cloned by the workflow.
# This script only validates the source directory passed to it.
# ============================================================

def fail(message):
    print(f"[ERROR] {message}")
    sys.exit(1)


def backup(path):
    backup_path = path + ".tepuy.bak"

    if not os.path.exists(backup_path):
        shutil.copy2(path, backup_path)
        print(f"[INFO] Backup: {backup_path}")


def require_file(path):
    if not os.path.isfile(path):
        fail(f"Archivo requerido no encontrado: {path}")


def replace_required(content, old, new, description):
    if new in content:
        print(f"[INFO] {description}: ya aplicado")
        return content

    if old not in content:
        fail(
            f"No se encontró el bloque esperado para:\n"
            f"  {description}\n"
            f"El source no coincide con la versión esperada."
        )

    content = content.replace(old, new, 1)
    print(f"[OK] {description}")
    return content


# ============================================================
# Verify kernel tree
# ============================================================

if not os.path.isdir(KERNEL_DIR):
    fail(f"No existe el directorio del kernel: {KERNEL_DIR}")

if not os.path.isfile(os.path.join(KERNEL_DIR, "Makefile")):
    fail(
        "El directorio indicado no parece ser la raíz del kernel "
        "(no existe Makefile)."
    )

# Check Git remote when available.
# We do NOT clone here; the workflow is responsible for that.
try:
    result = subprocess.run(
        ["git", "-C", KERNEL_DIR, "remote", "-v"],
        stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL,
        text=True,
        check=False,
    )

    remote = result.stdout

    if remote:
        if "peridot-dev/android_kernel_xiaomi_sm8635" in remote:
            print("[OK] Repo original Peridot detectado")
        elif "LineageOS/android_kernel_xiaomi_sm8635" in remote:
            fail(
                "El workflow está utilizando el repositorio de LineageOS.\n"
                "Usa el repo original:\n"
                "https://github.com/peridot-dev/android_kernel_xiaomi_sm8635.git"
            )
        else:
            print(
                "[INFO] Git remoto diferente/no identificado. "
                "Se continuará usando la estructura del source."
            )

except Exception:
    print("[INFO] No se pudo comprobar el remote Git.")


# ============================================================
# FIX: OpenSSL 3.0 compatibility
# ============================================================

extract_cert = os.path.join(KERNEL_DIR, "certs/extract-cert.c")

require_file(extract_cert)

with open(extract_cert, "r", encoding="utf-8") as file:
    content = file.read()

old_decl = """#ifdef USE_PKCS11_ENGINE
static const char *key_pass;
#endif"""

new_decl = "static const char *key_pass;"

if old_decl in content:
    backup(extract_cert)

    content = content.replace(old_decl, new_decl, 1)

    with open(extract_cert, "w", encoding="utf-8") as file:
        file.write(content)

    print("[OK] certs/extract-cert.c patched for OpenSSL 3.0")

elif new_decl in content:
    print("[INFO] certs/extract-cert.c ya contiene el fix OpenSSL 3.0")

else:
    print(
        "[INFO] certs/extract-cert.c already patched "
        "or different format"
    )


# ============================================================
# 1. drivers/cpufreq/qcom-cpufreq-hw.c
# ============================================================

cpufreq_file = os.path.join(
    KERNEL_DIR,
    "drivers/cpufreq/qcom-cpufreq-hw.c"
)

require_file(cpufreq_file)

with open(cpufreq_file, "r", encoding="utf-8") as f:
    content = f.read()

backup(cpufreq_file)


# ------------------------------------------------------------
# Includes
# ------------------------------------------------------------

content = replace_required(
    content,
    "#include <linux/of_address.h>\n",
    "#include <linux/of_address.h>\n"
    "#include <linux/of.h>\n"
    "#include <linux/kobject.h>\n",
    "qcom-cpufreq-hw.c: includes Tepuy",
)


# ------------------------------------------------------------
# Tepuy GameMode
# ------------------------------------------------------------

tepuy_code = """
/* ========================================================================
 * Tepuy GameMode
 * ======================================================================== */

bool tepuy_game_mode = false;
EXPORT_SYMBOL_GPL(tepuy_game_mode);

static ssize_t game_mode_show(struct kobject *kobj, struct kobj_attribute *attr,
\t\t      char *buf)
{
\treturn sprintf(buf, "%u\\n", tepuy_game_mode);
}

static ssize_t game_mode_store(struct kobject *kobj, struct kobj_attribute *attr,
\t\t       const char *buf, size_t count)
{
\tunsigned int val;
\t
\tif (kstrtouint(buf, 10, &val))
\t\treturn -EINVAL;
\ttepuy_game_mode = !!val;
\tpr_info("Tepuy GameMode: %s\\n", tepuy_game_mode ? "ON" : "OFF");
\treturn count;
}

static struct kobj_attribute game_mode_attr = __ATTR(game_mode, 0666,
\t\t\t     game_mode_show, game_mode_store);

static struct attribute *tepuy_boost_attrs[] = {
\t&game_mode_attr.attr,
\tNULL,
};

static struct attribute_group tepuy_boost_attr_group = {
\t.attrs = tepuy_boost_attrs,
};

static int __init tepuy_boost_init(void)
{
\tstruct kobject *tepuy_boost_kobj;

\ttepuy_boost_kobj = kobject_create_and_add("tepuy_boost", kernel_kobj);
\tif (!tepuy_boost_kobj)
\t\treturn -ENOMEM;

\tif (sysfs_create_group(tepuy_boost_kobj, &tepuy_boost_attr_group))
\t\tpr_err("Tepuy GameMode: failed to create sysfs group\\n");

\treturn 0;
}
late_initcall(tepuy_boost_init);

/* ======================================================================== */
"""

content = replace_required(
    content,
    "#include <soc/qcom/cpufreq.h>\n",
    "#include <soc/qcom/cpufreq.h>\n" + tepuy_code,
    "qcom-cpufreq-hw.c: Tepuy GameMode",
)


# ------------------------------------------------------------
# CPU OPP fallback
# ------------------------------------------------------------

old_code1 = """
\tret = dev_pm_opp_adjust_voltage(cpu_dev, freq_hz, volt, volt, volt);
\tif (ret) {
\t\tdev_err(cpu_dev, "Voltage update failed freq=%ld\\n", freq_khz);
\t\treturn ret;
\t}

\treturn dev_pm_opp_enable(cpu_dev, freq_hz);
}
"""

new_code1 = """
\tret = dev_pm_opp_adjust_voltage(cpu_dev, freq_hz, volt, volt, volt);
\tif (ret) {
\t\tstruct dev_pm_opp *opp;
\t\tif (!tepuy_game_mode)
\t\t\treturn ret;
\t\topp = dev_pm_opp_add(cpu_dev, freq_hz, volt);
\t\tif (!IS_ERR(opp)) {
\t\t\tdev_pm_opp_put(opp);
\t\t\treturn 0;
\t\t}
\t\tif (PTR_ERR(opp) != -EEXIST)
\t\t\tdev_err(cpu_dev, "Failed to add missing OPP freq=%ld: %ld\\n", freq_khz, PTR_ERR(opp));
\t\telse
\t\t\treturn 0;

\t\tdev_err(cpu_dev, "Voltage/OPP update failed freq=%ld\\n", freq_khz);
\t\treturn ret;
\t}

\tret = dev_pm_opp_enable(cpu_dev, freq_hz);
\tif (ret == -ENODEV || ret == -ENOENT) {
\t\tstruct dev_pm_opp *opp;
\t\tif (!tepuy_game_mode)
\t\t\treturn ret;
\t\topp = dev_pm_opp_add(cpu_dev, freq_hz, volt);
\t\tif (!IS_ERR(opp)) {
\t\t\tdev_pm_opp_put(opp);
\t\t\tret = 0;
\t\t} else if (PTR_ERR(opp) == -EEXIST) {
\t\t\tret = 0;
\t\t} else {
\t\t\tret = PTR_ERR(opp);
\t\t}
\t}

\treturn ret;
}
"""

content = replace_required(
    content,
    old_code1,
    new_code1,
    "qcom-cpufreq-hw.c: CPU OPP GameMode fallback",
)

with open(cpufreq_file, "w", encoding="utf-8") as f:
    f.write(content)

print("[OK] drivers/cpufreq/qcom-cpufreq-hw.c modificado")


# ============================================================
# 2. drivers/gpu/drm/msm/adreno/adreno_gpu.c
# ============================================================

adreno_file = os.path.join(
    KERNEL_DIR,
    "drivers/gpu/drm/msm/adreno/adreno_gpu.c"
)

require_file(adreno_file)

with open(adreno_file, "r", encoding="utf-8") as f:
    content = f.read()

backup(adreno_file)


# ------------------------------------------------------------
# Includes
# ------------------------------------------------------------

content = replace_required(
    content,
    "#include <linux/of_address.h>\n",
    "#include <linux/of_address.h>\n"
    "#include <linux/of.h>\n",
    "adreno_gpu.c: linux/of.h",
)


# ------------------------------------------------------------
# Tepuy GameMode extern
# ------------------------------------------------------------

content = replace_required(
    content,
    '#include "a7xx_gpu.h"\n',
    '#include "a7xx_gpu.h"\n\n'
    'extern bool tepuy_game_mode;\n',
    "adreno_gpu.c: Tepuy GameMode extern",
)


# ------------------------------------------------------------
# GPU 1100 MHz
# ------------------------------------------------------------

old_code2 = """
\t\tDRM_DEV_ERROR(dev, "Unable to set the OPP table\\n");
\t}

\tif (!ret) {
\t\t/* Find the fastest defined rate */
"""

new_code2 = """
\t\tDRM_DEV_ERROR(dev, "Unable to set the OPP table\\n");
\t}

\tif (!ret && of_machine_is_compatible("xiaomi,peridot") && tepuy_game_mode) {
\t\tstruct dev_pm_opp *opp;
\t\tstruct dev_pm_opp *top_opp;
\t\tunsigned long top_freq = ULONG_MAX;
\t\tunsigned long top_volt;

\t\t/*
\t\t * Nunca usar voltaje 0/inventado: no viene del binning real
\t\t * de silicio y puede causar hangs/inestabilidad de GPU.
\t\t * Reutilizamos el voltaje del OPP mas alto ya calibrado por
\t\t * Xiaomi/Qualcomm y solo agregamos una frecuencia extra sobre
\t\t * ese mismo riel.
\t\t */
\t\ttop_opp = dev_pm_opp_find_freq_floor(dev, &top_freq);
\t\tif (!IS_ERR(top_opp)) {
\t\t\ttop_volt = dev_pm_opp_get_voltage(top_opp);
\t\t\tdev_pm_opp_put(top_opp);

\t\t\tif (top_volt > 0) {
\t\t\t\topp = dev_pm_opp_add(dev, 1100000000UL, top_volt);
\t\t\t\tif (IS_ERR(opp)) {
\t\t\t\t\tif (PTR_ERR(opp) != -EEXIST)
\t\t\t\t\t\tDRM_DEV_DEBUG(dev, "Failed to add 1100 MHz peridot GPU OPP: %ld\\n", PTR_ERR(opp));
\t\t\t\t} else {
\t\t\t\t\tdev_pm_opp_put(opp);
\t\t\t\t\tDRM_DEV_INFO(dev, "Tepuy: added 1100 MHz OPP at %lu uV\\n", top_volt);
\t\t\t\t}
\t\t\t} else {
\t\t\t\tDRM_DEV_DEBUG(dev, "Tepuy: top OPP voltage invalid, skip 1100 MHz\\n");
\t\t\t}
\t\t} else {
\t\t\tDRM_DEV_DEBUG(dev, "Tepuy: no calibrated OPP found, skip 1100 MHz\\n");
\t\t}
\t}

\tif (!ret) {
\t\t/* Find the fastest defined rate */
"""

content = replace_required(
    content,
    old_code2,
    new_code2,
    "adreno_gpu.c: GPU 1100 MHz Tepuy OPP",
)

with open(adreno_file, "w", encoding="utf-8") as f:
    f.write(content)

print("[OK] drivers/gpu/drm/msm/adreno/adreno_gpu.c modificado")


# ============================================================
# 3. drivers/gpu/drm/msm/adreno/a6xx_gmu.c
# ============================================================

gmu_file = os.path.join(
    KERNEL_DIR,
    "drivers/gpu/drm/msm/adreno/a6xx_gmu.c"
)

require_file(gmu_file)

with open(gmu_file, "r", encoding="utf-8") as f:
    content = f.read()

backup(gmu_file)


# ------------------------------------------------------------
# Tepuy GameMode extern
# ------------------------------------------------------------

content = replace_required(
    content,
    '#include "msm_mmu.h"\n',
    '#include "msm_mmu.h"\n\n'
    'extern bool tepuy_game_mode;\n',
    "a6xx_gmu.c: Tepuy GameMode extern",
)


# ------------------------------------------------------------
# GMU frequency index
# ------------------------------------------------------------

old_code3 = """
\tfor (perf_index = 0; perf_index < gmu->nr_gpu_freqs - 1; perf_index++)
\t\tif (gpu_freq == gmu->gpu_freqs[perf_index])
\t\t\tbreak;

\tgmu->current_perf_index = perf_index;
"""

new_code3 = """
\tfor (perf_index = 0; perf_index < gmu->nr_gpu_freqs; perf_index++)
\t\tif (gpu_freq == gmu->gpu_freqs[perf_index])
\t\t\tbreak;

\tif (perf_index == gmu->nr_gpu_freqs) {
\t\tDRM_DEV_ERROR(gmu->dev, "GPU frequency %lu Hz is not in the GMU table\\n",
\t\t\t      gpu_freq);
\t\treturn;
\t}

\tif (!tepuy_game_mode && perf_index == gmu->nr_gpu_freqs - 1) {
\t\tDRM_DEV_DEBUG(gmu->dev, "Tepuy GameMode off, capping GPU perf index\\n");
\t\tperf_index = gmu->nr_gpu_freqs - 2;
\t}

\tgmu->current_perf_index = perf_index;
"""

content = replace_required(
    content,
    old_code3,
    new_code3,
    "a6xx_gmu.c: Tepuy GameMode GPU perf index",
)

with open(gmu_file, "w", encoding="utf-8") as f:
    f.write(content)

print("[OK] drivers/gpu/drm/msm/adreno/a6xx_gmu.c modificado")


# ============================================================
# Final verification
# ============================================================

print("\n============================================================")
print(" Verificación final")
print("============================================================")

checks = [
    (
        cpufreq_file,
        "bool tepuy_game_mode = false;",
        "Tepuy GameMode CPU",
    ),
    (
        cpufreq_file,
        "Failed to add missing OPP freq=",
        "CPU OPP fallback",
    ),
    (
        adreno_file,
        'of_machine_is_compatible("xiaomi,peridot")',
        "Peridot GPU compatibility",
    ),
    (
        adreno_file,
        "dev_pm_opp_find_freq_floor(dev, &top_freq)",
        "GPU 1100 MHz (voltaje calibrado, no 0)",
    ),
    (
        gmu_file,
        "Tepuy GameMode off, capping GPU perf index",
        "GMU GameMode",
    ),
]

for path, pattern, description in checks:

    with open(path, "r", encoding="utf-8") as f:
        text = f.read()

    if pattern not in text:
        fail(
            f"Verificación fallida: {description}\n"
            f"Archivo: {path}\n"
            f"Patrón: {pattern}"
        )

    print(f"[OK] {description}")


print("\n============================================================")
print(" Todas las modificaciones aplicadas correctamente.")
print("============================================================")
print()
print("Repo objetivo:")
print("  peridot-dev/android_kernel_xiaomi_sm8635")
print()
print("Archivos modificados:")
print("  certs/extract-cert.c")
print("  drivers/cpufreq/qcom-cpufreq-hw.c")
print("  drivers/gpu/drm/msm/adreno/adreno_gpu.c")
print("  drivers/gpu/drm/msm/adreno/a6xx_gmu.c")
print()
print("Backups:")
print("  *.tepuy.bak")
print()
