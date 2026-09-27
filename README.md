# GIGABYTE G292-Z20 Fan Control & Quiet Profile SOP

针对 **技嘉 G292-Z20-00**（2U EPYC + 多 GPU 高密度服务器，BMC MegaRAC SP-X）的一键风扇调优与降噪工具。

将出厂绝望啸叫（8250 ~ 12000 RPM）一键压制至硬件物理极限下限 **3750 RPM**（quiet_max 策略）。

---

## 核心避坑指南 (必读)

1. **无独立 PWM / BIOS 无调速选项**：
   - 技嘉 G292-Z20 仅暴露 BMC Web API 的 fanprofile 策略接口。
   - ipmitool raw 等传统写 PWM 方式会被底层温控线程瞬间覆盖重置。
2. **硬件物理极限下限 = 3750 RPM**：
   - 实测设置占空比 duty: 5% 或 duty: 0%，8 把 80mm 双滚珠风扇均会被底层硬件钳位在 **3750 RPM**。
3. **最大深坑：空槽位传感器引发 BMC 紧急全速狂转**：
   - 出厂 Profile 默认监控 [24..31]（全部 8 个 GPU 槽位）。
   - 若机器仅插了部分显卡（如 Slot 4~7），未插卡的传感器读数为空，BMC 会直接触发安全兜底，风扇拉满狂转！
   - **黄金解法**：自建 Profile 必须只绑定实际存在的传感器 ID（如 4 卡对应 [28, 29, 30, 31]）。

---

## 快速使用

无需复杂第三方依赖，纯 Python 原生标准库：



详细逆向数据与实测日志见 docs/g292-z20-fancontrol.md。
