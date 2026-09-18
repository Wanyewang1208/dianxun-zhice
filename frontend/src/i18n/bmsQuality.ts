export const qualityMessages: [string,string][] = [
 ['核心字段未通过','Core field checks failed'],
 ['校验范围未知，请更新后端','Validation scope unknown; update the backend'],
 ['存在未校验字段','Some fields have not been validated'],
 ['核心字段可读取，需复核警告','Core fields readable; review warnings'],
 ['核心字段校验通过','Core field checks passed'],
 ['校验仅涉及核心字段，不等于安全认证或实车 SOH/RUL 验证。','Checks cover core fields only, not safety certification or vehicle SOH/RUL validation.'],
 ['下载完整质量报告','Download full quality report'],
 ['请求超过 2 MiB，请拆分数据后重试。','Request exceeds 2 MiB. Split the data and retry.'],
 ['CSV 超过 10,000 行，请按车辆和时间段拆分后重试。','CSV exceeds 10,000 rows. Split by vehicle and time period, then retry.'],
 ['CSV 存在重复列名，请修改后重试。','CSV contains duplicate column names. Correct them and retry.'],
];
