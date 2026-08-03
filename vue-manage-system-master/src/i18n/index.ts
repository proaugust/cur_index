import { createI18n } from 'vue-i18n';
import zhCN from '@/locales/zh-CN';
import jaJP from '@/locales/ja-JP';
import enUS from '@/locales/en-US';

const STORAGE_KEY = 'vuems_locale';

export type AppLocale = 'en-US' | 'zh-CN' | 'ja-JP';

const SUPPORTED: AppLocale[] = ['en-US', 'zh-CN', 'ja-JP'];

export function getStoredLocale(): AppLocale {
    const saved = localStorage.getItem(STORAGE_KEY);
    return SUPPORTED.includes(saved as AppLocale) ? (saved as AppLocale) : 'zh-CN';
}

export function persistLocale(locale: AppLocale) {
    localStorage.setItem(STORAGE_KEY, locale);
}

const i18n = createI18n({
    legacy: false,
    locale: getStoredLocale(),
    fallbackLocale: 'zh-CN',
    messages: {
        'en-US': enUS,
        'zh-CN': zhCN,
        'ja-JP': jaJP,
    },
});

export default i18n;
