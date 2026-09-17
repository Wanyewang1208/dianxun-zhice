import { useEffect, useSyncExternalStore } from 'react';
import {getLanguage,setLanguage,subscribeLanguage} from './index';
export function useLanguage() {
  const language=useSyncExternalStore(subscribeLanguage,getLanguage,()=> 'zh' as const);
  useEffect(()=>{
    document.documentElement.lang=language==='zh'?'zh-CN':'en';
    document.title=language==='zh'?'电循智策 · 电池全生命周期智能评估':'DianXun ZhiCe · Battery Lifecycle Intelligence';
  },[language]);
  return {language,setLanguage};
}
