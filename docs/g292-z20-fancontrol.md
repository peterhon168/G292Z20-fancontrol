# 技嘉 G292-Z20-00 (BMC 192.168.0.120) 风扇调速实录

> 实测日期 2026-09-20。主机上电、4×被动散热 GPU 在 Slot4-7 待机、进风 28°C。
> **本机风扇与 MZ32-AR0 完全不同**（硬件下限 **3750 RPM** vs 1200 RPM），不要照搬 `t10-gpu-fancontrol.md` 的占空比表。
> 另有配套结论：**唯一风扇调节接口就是 fanprofile**（前端 11MB JS 全量搜完，无独立 PWM 接口；BIOS 613 项属性里 fan/thermal 相关 0 条）。

## 1. 八把风扇的传感器号
| SensorNum | 名称 | 说明 |
|---|---|---|
| 160 | GPU_FAN12 | Slot1/2 区域 |
| 161 | GPU_FAN56 | Slot5/6 区域 |
| 162 | SYS_FAN1 | 系统风扇（跟 CPU 温度） |
| 163 | SYS_FAN2 | 系统风扇 |
| 164 | GPU_FAN34 | Slot3/4 区域 |
| 165 | GPU_FAN78 | Slot7/8 区域 |
| 166 | GPU_FAN12E | 冗余/排风 |
| 167 | GPU_FAN56E | 冗余/排风 |

风扇下限告警 1500 RPM，critical 1200 RPM。

## 2. 出厂自带 3 个 profile
`low_profile_mi_a`（出厂默认激活） / `default` / `SPECpower`。
出厂 profile 的 `arrSensor` 都是 `[24..31]`（GPU0-7 **全部 8 个槽位**）——见 §4 的坑。

## 3. API 速查（Gigabyte MegaRAC SP-X Web API）
```bash
# 登录（必须 form-urlencoded；JSON 会 403）
curl -sk -c /tmp/bmc.jar -X POST https://192.168.0.120/api/session \
  -H 'Content-Type: application/x-www-form-urlencoded' \
  -H 'X-Requested-With: XMLHttpRequest' \
  -d 'username=admin&password=<PW>'
# -> {"ok":0,"privilege":4,...,"CSRFToken":"xxxxxxxx"}
# 之后每个请求必须带 -H 'X-CSRFTOKEN: <token>'，否则 401
```
| 操作 | 方法 + 路径 |
|---|---|
| 列全部 profile | `GET /api/settings/fanprofile` |
| 列 profile 数组 | `GET /api/settings/fanprofile/collection` |
| 查当前激活 | `GET /api/settings/fanprofile/mode` |
| **激活 profile** | **`POST /api/settings/fanprofile/mode`** body `{"strMode":"<name>"}` |
| 新建 profile | `POST /api/settings/fanprofile/collection` body `{"strVersion","strName","arrPolicy"}` |
| 修改 profile | `PUT /api/settings/fanprofile/collection/<name>` |

⚠️ **激活必须用 POST；用 PUT 会返回 `404 {"error":"Invalid API Call","code":1010}`。**

policy 字段：`arrFanSensor`(风扇传感器号) / `arrSensor`(温度源) / `arrRef`(温度拐点) / `arrDuty`(对应占空比) / `iInitDuty` / `iPolicyType`(2=温度斜坡, 1=固定占空比) / `iPCIEDeviceEnable` / `arrHexVendorID`。

## 4. ⚠️ 最大的坑：引用不存在的 GPU 传感器 → BMC 兜底高速
出厂 `low_profile_mi_a` / `SPECpower` 的 policy 把 `arrSensor` 写成 `[24,25,26,27,28,29,30,31]`（GPU0-7）。
本机只装了 Slot4-7 四张卡，**GPU0-3（sensor 24-27）读不到** → BMC 走兜底高占空比：
- `low_profile_mi_a` 实测 GPU 风扇 **8250 RPM**、SYS 风扇 **9750 RPM**（几乎没有调速）
- `SPECpower` 实测 GPU 风扇 **6000 RPM**

⇒ **自建 profile 时 `arrSensor` 只写实际存在的传感器（本机 GPU4-7 = 28,29,30,31）**，占空比才会真正生效（10% → 4350 RPM）。

## 5. 硬件下限 = **3750 RPM**（已定论）
逐档实测（同一台机、同一温度区间）：

| duty | 实测转速 |
|---|---|
| 10% | 4350 RPM |
| 5% | **3750 RPM** |
| **0%** | **仍是 3750 RPM**（`GET /api/settings/fanprofile/collection/quiet_zero` 复核过存的确实是 0） |

⇒ **BMC/风扇本身有最低转速钳位，软件层无法再低**。曲线很浅（≈120 RPM / 1%），所以低档设 0 和设 5 结果一样，**设 5% 即可**（避免 0 被解释成停转）。

**结论：8 把 80mm 高速风扇在 2U 机箱里的物理下限就是 3750 RPM（出厂默认 9750）。想更静只能换硬件：换低转速风扇 / 减少发热卡 / 移机。**

## 5.1 真正的调节旋钮是"斜坡拐点"（knee），不是低档 duty
因为下限被硬钳位，**拐点以下的风扇都跑 3750**，拐点越低越早离开下限、越吵：

- 拐点 68°C（`quiet_low`）⇒ GPU 稳在 69°C，风扇 4350~4800 RPM
- 拐点 74°C（`quiet_max`，已部署）⇒ 风扇长期停在 **3750 下限**，代价 GPU 72~74°C / CPU 75°C
- 斜坡在拐点之上依然成立：实测 GPU 越过拐点后风扇自动从 3750 升到 4350→4800 把温度压住，**保护机制验证有效**

## 6. quiet_max（**当前已部署激活**，最静档）
```json
{"strVersion":"1.00","strName":"quiet_min","arrPolicy":[
 {"arrFanSensor":[160,161,164,165,166,167],"arrSensor":[28,29,30,31],
  "arrRef":[62,72,82],"arrDuty":[10,60,100],"iInitDuty":10,"iPolicyType":2,
  "iSensorCode":1,"iInSDR":1,"iHysteresis":0,"iPCIEDeviceEnable":0,"iCpuTdp":0,
  "iAmbientSensor":0,"iAmbientSensorTemp":0,"arrHexVendorID":[],"arrHexDeviceID":[]},
 {"arrFanSensor":[162,163],"arrSensor":[1],
  "arrRef":[66,78,88],"arrDuty":[10,60,100],"iInitDuty":10,"iPolicyType":2,
  "iSensorCode":1,"iInSDR":1,"iHysteresis":0,"iPCIEDeviceEnable":0,"iCpuTdp":0,
  "iAmbientSensor":0,"iAmbientSensorTemp":0,"arrHexVendorID":[],"arrHexDeviceID":[]}]}
```
- GPU 风扇跟真实 GPU 温度（**74°C→5%、82°C→60%、88°C→100%**）；SYS 风扇跟 CPU 温度（**76°C→5%、84°C→60%、90°C→100%**）。
- **必须保留 82°C→100% 斜坡**：本机装的是 4 张**被动散热卡**（无自带风扇），风道是唯一生命线。

## 7. 实测对比
| 状态 | GPU_FAN12..78 | SYS_FAN1/2 | 功耗 | CPU0_TEMP | GPU4-7 | DIMM | MB_TEMP2 |
|--|--|--|--|--|--|--|--|
| 出厂 `low_profile_mi_a` | 8250 | 9750 | 488W | 49 | 46~50 | 37 | 48 |
| `SPECpower` | 6000 | 4350 | 439W | 59 | 49~53 | 41 | 53 |
| `quiet_min`（拐点68 / 低档10%） | 4500 | 4350 | 444W | 66 | 56~62 | 46 | 61 |
| `quiet_low`（拐点68 / 低档5%） | 3750 | 3750 | 434W | 63 | 54~59 | 43 | 54 |
| `quiet_max`（拐点74 / 低档5%，稳态） | **3750** | **3750** | 466W | 75 | 65~74 | 51 | 65 |

阈值：GPU crit 105 / DIMM crit 87 / MB crit 90 / CPU crit 100 °C。三者都安全；拐点 74 是"用 GPU 温度（72~74°C）换风扇压到 3750 物理下限"的最静档。

## 9. 同机其他关键点（2026-09-20 实测）
- **功耗上限是个雷**：出厂 `LimitInWatts=500` + `LimitException=HardPowerOff`，而待机已 44x W。POST 阶段 8 把风扇全速（仅风扇 200W+）会顶穿 500W → **硬断电**，表现就是"开机卡自检后关机"（对上 SEL 里 boot event 后紧跟 Power off）。
  取消方式（Redfish）：**PATCH 必须带 `If-Match: <ETag>`**，否则 `428 Precondition Required`；顶层 `{"PowerLimit":...}` 会 400（"not in schema"），必须用 `{"PowerControl":[{"LimitInWatts":2200,"LimitException":"NoAction","CorrectionInMs":1000}]}`。设 0 会被 BMC 回写成 1 ⇒ 用 2200W（单电源额定值）+ `NoAction` 达到"实际不限制、且永不断电"。
- **内存**：`DIMM_P0_G0` 曾 `iSize/isSpeed/iRank` 全 0（BMC 完全读不到），重插后恢复 `16384MiB @ 2133MHz`，8/8 正常。⇒ `iSize=0` 是**物理接触问题**，不是内存条坏。
- **GPU 白名单**：`GET /api/settings/fanprofile/device_define` 共 107 条（含 `Tesla_T4 0x10de/0x1eb8`），**没有本机的 `0x1E37`** ⇒ BMC 认不出这批卡，套 `default`（UC=100/UNC=95）阈值；自定义 profile 是唯一正解。
- **采样注意**：`execute_code` 有 300s 硬超时 —— 监测脚本 sleep 总和别超 ~240s，并 `sys.stdout.flush()`，否则超时被杀、输出全丢（踩过）。

## 8. 其他坑
1. **Redfish 与 Web API 必须两套独立会话**：用 Web cookie 去 GET `/redfish/...` 会被截断（JSON 报 `Unterminated string`）；Web 登录会让 Redfish token 失效（401）⇒ 每次采样重新 `POST /redfish/v1/SessionService/Sessions` 取 `X-Auth-Token`。
2. **mode 不是永久的**：BMC 重启/固件升级后可能回到 `default`，需重新 `POST .../mode`。
3. 回滚：`POST /api/settings/fanprofile/mode {"strMode":"default"}`。
