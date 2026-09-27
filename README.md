# GIGABYTE G292-Z20 Fan Control &amp; Acoustic Optimization SOP

<div align="center">

<img src="docs/banner.jpg" width="600" alt="G292 Fan Control Banner" />

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![Platform](https://img.shields.io/badge/Platform-GIGABYTE%20G292--Z20-orange.svg)](https://www.gigabyte.com)
[![BMC](https://img.shields.io/badge/BMC-MegaRAC%20SP--X-green.svg)]()
[![Hardware Limit](https://img.shields.io/badge/Acoustic%20Limit-3750%20RPM-cyan.svg)]()

[**English**](#english-documentation) | [**中文说明**](#中文说明)

</div>

---

## 中文说明

针对 **技嘉 G292-Z20-00**（2U EPYC + 多 GPU 高密度服务器，BMC MegaRAC SP-X）的一键风扇调优与静音降噪工具。

通过逆向分析 BMC 原生 Web API 的 `fanprofile` 策略接口，彻底解决未满插显卡时空槽位传感器读数为空导致的“出厂 12000 RPM 紧急全速尖啸”大坑，将 8 把 80mm 双滚珠暴力扇平稳压制在底层硬件的物理极限下限 **3750 RPM**（`quiet_max` 策略）。

### 核心避坑指南 (必读)

1. **前端无独立 PWM 接口，BIOS 无调速选项**：
   - 技嘉 G292-Z20 仅暴露 BMC Web API 的 `fanprofile` 策略接口。
   - `ipmitool raw` 等传统强制写入 PWM 的指令会被底层 BMC 固件温控线程在毫秒级内覆盖重置。
2. **硬件物理下限 = 3750 RPM (定论)**：
   - 实测无论将占空比设置为 `duty: 5%` 还是 `duty: 0%`，风扇均会被底层微控制器硬锁死在 **3750 RPM**。
   - 软件层面无法再降，如需更低噪音只能通过物理改装或更换低速风扇。
3. **最关键的深坑：空槽位温度传感器导致 BMC 触发全速狂转**：
   - 出厂 Profile 默认监控 `[24..31]`（全部 8 个 GPU 槽位）。
   - 若机器仅插入了部分显卡（如仅 Slot 4~7 插卡），未插卡的槽位传感器读数为空，BMC 会直接触发安全兜底机制，风扇拉满至 8250 ~ 12000 RPM 疯狂啸叫。
   - **黄金解法**：自建 Profile 必须且只能绑定实际物理存在的传感器 ID（例如 Slot 4~7 对应传感器 ID 为 `[28, 29, 30, 31]`）。
4. **真正的调节旋钮是“温度斜坡拐点”**：
   - 拐点以下稳定在 3750 RPM；`quiet_max` 策略将拐点设为 74°C，在被动散热 GPU 保持 65~74°C（安全温区）的同时，最大化延长 3750 RPM 的静音停留时间。

### 快速使用

纯 Python 3 原生标准库编写，无需安装任何额外依赖：

```bash
# 1. 查询当前生效模式与全部传感器实时转速/温度
python3 scripts/set_g292_fan.py --host <BMC_IP> --user admin --password <PASSWORD> --mode status

# 2. 一键注入并激活 quiet_max 静音策略 (压至 3750 RPM)
python3 scripts/set_g292_fan.py --host <BMC_IP> --user admin --password <PASSWORD> --mode quiet_max

# 3. 紧急切回出厂默认全速策略
python3 scripts/set_g292_fan.py --host <BMC_IP> --user admin --password <PASSWORD> --mode default
```

详细逆向数据与实测日志见 [docs/g292-z20-fancontrol.md | [English Documentation](docs/g292-z20-fancontrol.en.md)](docs/g292-z20-fancontrol.md | [English Documentation](docs/g292-z20-fancontrol.en.md))。

---

## English Documentation

A lightweight, zero-dependency Python utility and reverse-engineered SOP for acoustic optimization and fan curve tuning on the **GIGABYTE G292-Z20-00** 2U EPYC multi-GPU server (MegaRAC SP-X BMC).

This tool safely bypasses the empty-slot sensor failsafe that causes factory default fans to scream at 8250 ~ 12000 RPM, clamping fan speeds down to the **3750 RPM** physical hardware baseline (`quiet_max` profile).

### Key Architectural Findings

1. **No BIOS Fan Options & No Raw PWM Control**:
   - The BIOS offers zero fan or thermal controls.
   - Standard `ipmitool raw` PWM overrides are immediately reverted by the internal BMC thermal management loop.
2. **Hard Minimum Speed Clamped at 3750 RPM**:
   - Setting duty cycle to 5% or even 0% clamps the 80mm dual-rotor fans to a hardware minimum of **3750 RPM**.
3. **The Sensor Trap (Factory Failsafe)**:
   - Factory fan profiles blindly monitor all 8 PCIe slots (Sensors `[24..31]`).
   - If only a subset of slots are populated (e.g., Slots 4–7), the empty sensors report null, triggering emergency 100% duty failsafes.
   - **Fix**: Custom profiles must explicitly monitor **only physically populated sensors** (e.g. `[28, 29, 30, 31]`).
4. **Thermal Knee Configuration**:
   - Fans idle at 3750 RPM below the knee temperature (74°C for GPU, 76°C for CPU). Above this threshold, dynamic ramp curves ensure complete thermal safety under full compute load.

### Quick Start

```bash
# 1. Query current mode and sensor telemetry
python3 scripts/set_g292_fan.py --host <BMC_IP> --user admin --password <PASSWORD> --mode status

# 2. Apply and activate quiet_max profile (clamped to 3750 RPM)
python3 scripts/set_g292_fan.py --host <BMC_IP> --user admin --password <PASSWORD> --mode quiet_max

# 3. Revert to factory default failsafe profile
python3 scripts/set_g292_fan.py --host <BMC_IP> --user admin --password <PASSWORD> --mode default
```

---

## License

MIT License. See [LICENSE](LICENSE) for details.

