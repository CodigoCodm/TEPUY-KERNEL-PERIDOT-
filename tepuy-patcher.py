#!/usr/bin/env python3
"""Tepuy GameMode Patcher"""

import os
import sys

KERNEL_DIR = sys.argv[1] if len(sys.argv) > 1 else "."

# === 1. drivers/cpufreq/qcom-cpufreq-hw.c ===
cpufreq_file = os.path.join(KERNEL_DIR, "drivers/cpufreq/qcom-cpufreq-hw.c")
with open(cpufreq_file, "r") as f:
    content = f.read()

content = content.replace(
    "#include <linux/of_address.h>\n",
    "#include <linux/of_address.h>\n#include <linux/of.h>\n#include <linux/kobject.h>\n"
)

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

content = content.replace(
    "#include <soc/qcom/cpufreq.h>\n",
    "#include <soc/qcom/cpufreq.h>\n" + tepuy_code
)

old_code1 = """
\tret = dev_pm_opp_adjust_voltage(cpu_dev, freq_hz, volt, volt, volt);
\tif (ret) {
\t\tdev_err(cpu_dev, "Voltage update failed freq=%ld\\n", freq_khz);
\t\treturn ret;
\t}

\treturn dev_pm_opp_enable(cpu_dev, freq_hz);
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
"""

content = content.replace(old_code1, new_code1)

with open(cpufreq_file, "w") as f:
    f.write(content)

print("[OK] drivers/cpufreq/qcom-cpufreq-hw.c modificado")

# === 2. drivers/gpu/drm/msm/adreno/adreno_gpu.c ===
adreno_file = os.path.join(KERNEL_DIR, "drivers/gpu/drm/msm/adreno/adreno_gpu.c")
with open(adreno_file, "r") as f:
    content = f.read()

content = content.replace(
    "#include <linux/of_address.h>\n",
    "#include <linux/of_address.h>\n#include <linux/of.h>\n"
)

content = content.replace(
    "#include \"a7xx_gpu.h\"\n",
    "#include \"a7xx_gpu.h\"\n\nextern bool tepuy_game_mode;\n"
)

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
\t\topp = dev_pm_opp_add(dev, 1100000000UL, 0);
\t\tif (IS_ERR(opp)) {
\t\t\tif (PTR_ERR(opp) != -EEXIST)
\t\t\t\tDRM_DEV_DEBUG(dev, "Failed to add 1100 MHz peridot GPU OPP: %ld\\n", PTR_ERR(opp));
\t\t} else {
\t\t\tdev_pm_opp_put(opp);
\t\t}
\t}

\tif (!ret) {
\t\t/* Find the fastest defined rate */
"""

content = content.replace(old_code2, new_code2)

with open(adreno_file, "w") as f:
    f.write(content)

print("[OK] drivers/gpu/drm/msm/adreno/adreno_gpu.c modificado")

# === 3. drivers/gpu/drm/msm/adreno/a6xx_gmu.c ===
gmu_file = os.path.join(KERNEL_DIR, "drivers/gpu/drm/msm/adreno/a6xx_gmu.c")
with open(gmu_file, "r") as f:
    content = f.read()

content = content.replace(
    "#include \"msm_mmu.h\"\n",
    "#include \"msm_mmu.h\"\n\nextern bool tepuy_game_mode;\n"
)

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

content = content.replace(old_code3, new_code3)

with open(gmu_file, "w") as f:
    f.write(content)

print("[OK] drivers/gpu/drm/msm/adreno/a6xx_gmu.c modificado")
print("\nTodas las modificaciones aplicadas correctamente.")
