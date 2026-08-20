#!/usr/bin/env python3
"""
Tepuy GameMode Patcher
Modifica los archivos del kernel de LineageOS para peridot (SM8635)
para añadir el modo juego que desbloquea OPPs máximos.
"""

import os
import sys

KERNEL_DIR = sys.argv[1] if len(sys.argv) > 1 else "."

# ============================================================================
# 1. drivers/cpufreq/qcom-cpufreq-hw.c
# ============================================================================
cpufreq_file = os.path.join(KERNEL_DIR, "drivers/cpufreq/qcom-cpufreq-hw.c")

with open(cpufreq_file, "r") as f:
    content = f.read()

# Añadir includes después de #include <linux/of_address.h>
content = content.replace(
    '#include <linux/of_address.h>
',
    '#include <linux/of_address.h>
#include <linux/of.h>
#include <linux/kobject.h>
'
)

# Insertar código Tepuy después de #include <soc/qcom/cpufreq.h>
tepuy_code = """
/* ========================================================================
 * Tepuy GameMode
 * ======================================================================== */

bool tepuy_game_mode = false;
EXPORT_SYMBOL_GPL(tepuy_game_mode);

static ssize_t game_mode_show(struct kobject *kobj, struct kobj_attribute *attr,
		      char *buf)
{
	return sprintf(buf, "%u\n", tepuy_game_mode);
}

static ssize_t game_mode_store(struct kobject *kobj, struct kobj_attribute *attr,
		       const char *buf, size_t count)
{
	unsigned int val;

	if (kstrtouint(buf, 10, &val))
		return -EINVAL;
	tepuy_game_mode = !!val;
	pr_info("Tepuy GameMode: %s\n", tepuy_game_mode ? "ON" : "OFF");
	return count;
}

static struct kobj_attribute game_mode_attr = __ATTR(game_mode, 0666,
			     game_mode_show, game_mode_store);

static struct attribute *tepuy_boost_attrs[] = {
	&game_mode_attr.attr,
	NULL,
};

static struct attribute_group tepuy_boost_attr_group = {
	.attrs = tepuy_boost_attrs,
};

static int __init tepuy_boost_init(void)
{
	struct kobject *tepuy_boost_kobj;

	tepuy_boost_kobj = kobject_create_and_add("tepuy_boost", kernel_kobj);
	if (!tepuy_boost_kobj)
		return -ENOMEM;

	if (sysfs_create_group(tepuy_boost_kobj, &tepuy_boost_attr_group))
		pr_err("Tepuy GameMode: failed to create sysfs group\n");

	return 0;
}
late_initcall(tepuy_boost_init);

/* ======================================================================== */
"""

content = content.replace(
    '#include <soc/qcom/cpufreq.h>
',
    '#include <soc/qcom/cpufreq.h>' + tepuy_code
)

# Modificar qcom_cpufreq_hw_target_index
old_code1 = """	ret = dev_pm_opp_adjust_voltage(cpu_dev, freq_hz, volt, volt, volt);
	if (ret) {
		dev_err(cpu_dev, "Voltage update failed freq=%ld\n", freq_khz);
		return ret;
	}

	return dev_pm_opp_enable(cpu_dev, freq_hz);"""

new_code1 = """	ret = dev_pm_opp_adjust_voltage(cpu_dev, freq_hz, volt, volt, volt);
	if (ret) {
		struct dev_pm_opp *opp;
		if (!tepuy_game_mode)
			return ret;
		opp = dev_pm_opp_add(cpu_dev, freq_hz, volt);
		if (!IS_ERR(opp)) {
			dev_pm_opp_put(opp);
			return 0;
		}
		if (PTR_ERR(opp) != -EEXIST)
			dev_err(cpu_dev, "Failed to add missing OPP freq=%ld: %ld\n", freq_khz, PTR_ERR(opp));
		else
			return 0;

		dev_err(cpu_dev, "Voltage/OPP update failed freq=%ld\n", freq_khz);
		return ret;
	}

	ret = dev_pm_opp_enable(cpu_dev, freq_hz);
	if (ret == -ENODEV || ret == -ENOENT) {
		struct dev_pm_opp *opp;
		if (!tepuy_game_mode)
			return ret;
		opp = dev_pm_opp_add(cpu_dev, freq_hz, volt);
		if (!IS_ERR(opp)) {
			dev_pm_opp_put(opp);
			ret = 0;
		} else if (PTR_ERR(opp) == -EEXIST) {
			ret = 0;
		} else {
			ret = PTR_ERR(opp);
		}
	}

	return ret;"""

content = content.replace(old_code1, new_code1)

with open(cpufreq_file, "w") as f:
    f.write(content)

print("[OK] drivers/cpufreq/qcom-cpufreq-hw.c modificado")

# ============================================================================
# 2. drivers/gpu/drm/msm/adreno/adreno_gpu.c
# ============================================================================
adreno_file = os.path.join(KERNEL_DIR, "drivers/gpu/drm/msm/adreno/adreno_gpu.c")

with open(adreno_file, "r") as f:
    content = f.read()

# Añadir include
content = content.replace(
    '#include <linux/of_address.h>
',
    '#include <linux/of_address.h>
#include <linux/of.h>
'
)

# Añadir extern después de #include "a7xx_gpu.h"
content = content.replace(
    '#include "a7xx_gpu.h"
',
    '#include "a7xx_gpu.h"

extern bool tepuy_game_mode;
'
)

# Insertar código OPP antes de "if (!ret) {"
old_code2 = """		DRM_DEV_ERROR(dev, "Unable to set the OPP table\n");
	}

	if (!ret) {
		/* Find the fastest defined rate */"""

new_code2 = """		DRM_DEV_ERROR(dev, "Unable to set the OPP table\n");
	}

	if (!ret && of_machine_is_compatible("xiaomi,peridot") && tepuy_game_mode) {
		struct dev_pm_opp *opp;
		opp = dev_pm_opp_add(dev, 1100000000UL, 0);
		if (IS_ERR(opp)) {
			if (PTR_ERR(opp) != -EEXIST)
				DRM_DEV_DEBUG(dev, "Failed to add 1100 MHz peridot GPU OPP: %ld\n", PTR_ERR(opp));
		} else {
			dev_pm_opp_put(opp);
		}
	}

	if (!ret) {
		/* Find the fastest defined rate */"""

content = content.replace(old_code2, new_code2)

with open(adreno_file, "w") as f:
    f.write(content)

print("[OK] drivers/gpu/drm/msm/adreno/adreno_gpu.c modificado")

# ============================================================================
# 3. drivers/gpu/drm/msm/adreno/a6xx_gmu.c
# ============================================================================
gmu_file = os.path.join(KERNEL_DIR, "drivers/gpu/drm/msm/adreno/a6xx_gmu.c")

with open(gmu_file, "r") as f:
    content = f.read()

# Añadir extern después de #include "msm_mmu.h"
content = content.replace(
    '#include "msm_mmu.h"
',
    '#include "msm_mmu.h"

extern bool tepuy_game_mode;
'
)

# Modificar el loop de frecuencias
old_code3 = """	for (perf_index = 0; perf_index < gmu->nr_gpu_freqs - 1; perf_index++)
		if (gpu_freq == gmu->gpu_freqs[perf_index])
			break;

	gmu->current_perf_index = perf_index;"""

new_code3 = """	for (perf_index = 0; perf_index < gmu->nr_gpu_freqs; perf_index++)
		if (gpu_freq == gmu->gpu_freqs[perf_index])
			break;

	if (perf_index == gmu->nr_gpu_freqs) {
		DRM_DEV_ERROR(gmu->dev, "GPU frequency %lu Hz is not in the GMU table\n",
			      gpu_freq);
		return;
	}

	if (!tepuy_game_mode && perf_index == gmu->nr_gpu_freqs - 1) {
		DRM_DEV_DEBUG(gmu->dev, "Tepuy GameMode off, capping GPU perf index\n");
		perf_index = gmu->nr_gpu_freqs - 2;
	}

	gmu->current_perf_index = perf_index;"""

content = content.replace(old_code3, new_code3)

with open(gmu_file, "w") as f:
    f.write(content)

print("[OK] drivers/gpu/drm/msm/adreno/a6xx_gmu.c modificado")
print("
Todas las modificaciones aplicadas correctamente.")
