import { pairs, mixed, notices } from './catalog';
import { evidence } from './evidence';
import { bmsMessages } from './bms';
export type Language = 'zh' | 'en';
type StorageLike = Pick<Storage, 'getItem' | 'setItem'>;
const key = 'dianxun.language';
const normalize = (value: string) => value.replace(/\s+/g, ' ').trim();
const dictionary = new Map<string, [string, string]>();
for (const [en,zh] of pairs) {
  dictionary.set(normalize(en),[zh,en]);
  // Keep the first preferred English wording when several labels share Chinese copy.
  if(!dictionary.has(normalize(zh)))dictionary.set(normalize(zh),[zh,en]);
}
for(const [source,zh,en] of mixed)dictionary.set(normalize(source),[zh,en]);
for(const [zh,en] of notices)dictionary.set(normalize(zh),[zh,en]);
for(const [source,zh,en] of evidence)dictionary.set(normalize(source),[zh,en]);
for(const [en,zh] of bmsMessages)dictionary.set(normalize(en),[zh,en]);

export function readLanguage(storage?: StorageLike): Language {
  try { return (storage ?? window.localStorage).getItem(key)==='en' ? 'en' : 'zh'; }
  catch { return 'zh'; }
}
export function saveLanguage(language: Language, storage?: StorageLike) {
  try { (storage ?? window.localStorage).setItem(key,language); } catch { /* Private browsing may disable storage. */ }
}
let language: Language = readLanguage();
const listeners = new Set<() => void>();
export const getLanguage = () => language;
export function setLanguage(next: Language) {
  if(next!=='zh' && next!=='en')return;
  language=next;saveLanguage(next);
  listeners.forEach(listener=>listener());
}
export function subscribeLanguage(listener: () => void) {
  listeners.add(listener);
  return () => { listeners.delete(listener); };
}
/** Translate presentation strings only. Numbers, React elements and unknown evidence are preserved. */
export function translate<T>(value: T, locale: Language): T {
  if(typeof value!=='string' || !value.trim())return value;
  const found=dictionary.get(normalize(value));
  if(found) {
    const leading=value.match(/^\s*/)?.[0] ?? '';
    const trailing=value.match(/\s*$/)?.[0] ?? '';
    return (leading+found[locale==='zh'?0:1]+trailing) as T;
  }
  const choose=(zh: string,en: string)=>(locale==='zh'?zh:en) as T;
  const gap=value.match(/^Gap exceeds ([\d.]+) seconds; do not integrate across gap$/);
  if(gap)return choose(`间隔超过 ${gap[1]} 秒；不可跨越该间隔积分`,value);
  const order=value.match(/^(.+) input not chronological; accepted output sorted$/);
  if(order)return choose(`${order[1]} 输入未按时间排序；通过的输出已排序`,value);
  const unit=value.match(/^(voltage_unit|current_unit|temperature_unit|soc_unit) must be (V|A|degC|%); no inferred conversion$/);
  if(unit)return choose(`${unit[1]} 必须为 ${unit[2]}；不进行推测换算`,value);
  // Preserve the caller's battery ID; translate only recognized metadata problems.
  const metadata=value.match(/^(.+?): (.+)$/);
  if(metadata) {
    const details=metadata[2].split(/; (?!(?:no inferred conversion))/);
    if(details.every(part=>bmsMessages.some(([en])=>en===part)||/^(voltage_unit|current_unit|temperature_unit|soc_unit) must be (V|A|degC|%); no inferred conversion$/.test(part)))
      return `${metadata[1]}: ${details.map(part=>translate(part,locale)).join('; ')}` as T;
  }
  const cycles=value.match(/^(N\/A|[\d.,]+) cycles$/);
  if(cycles)return choose(`${translate(cycles[1],locale)} 次循环`,value);
  const moduleLabel=value.match(/^打开 (.+) 模块说明$/);
  if(moduleLabel)return choose(`打开${translate(moduleLabel[1],locale)}模块说明`,`Open ${translate(moduleLabel[1],locale)} module`);
  const curve=value.match(/^示例 SOH 曲线：当前 (\d+) 次循环，预测 (\d+) 次达到 (\d+)% 参考线$/);
  if(curve)return choose(value,`Sample SOH curve: current cycle ${curve[1]}, projected cycle ${curve[2]} at the ${curve[3]}% reference line`);
  const weighted=value.match(/^(.+) (utility \/ 100|weight)$/);
  if(weighted)return choose(`${translate(weighted[1],locale)}${weighted[2]==='weight'?'权重':'效用 / 100'}`,value);
  const component=value.match(/^(.+) \/ 100$/);
  if(component)return `${translate(component[1],locale)} / 100` as T;
  const score=value.match(/^score (.+)$/);
  if(score)return choose(`评分 ${translate(score[1],locale)}`,value);
  const cycleLabel=value.match(/^Cycle (.+)$/);
  if(cycleLabel)return choose(`循环 ${cycleLabel[1]}`,value);
  // Composite report labels use explicit delimiters; no fuzzy or word-by-word translation.
  if(value.includes(' · '))return value.split(' · ').map(part=>translate(part,locale)).join(' · ') as T;
  if(value.includes(', '))return value.split(', ').map(part=>translate(part,locale)).join(', ') as T;
  return value;
}
export const t = <T,>(value: T): T => translate(value,language);
