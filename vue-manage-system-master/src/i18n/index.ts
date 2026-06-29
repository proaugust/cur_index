import { createI18n } from 'vue-i18n';
import zhCN from '@/locales/zh-CN';
import jaJP from '@/locales/ja-JP';

const STORAGE_KEY = 'vuems_locale';

export type AppLocale = 'zh-CN' | 'ja-JP';

export function getStoredLocale(): AppLocale {
    const saved = localStorage.getItem(STORAGE_KEY);
    return saved === 'ja-JP' ? 'ja-JP' : 'zh-CN';
}

export function persistLocale(locale: AppLocale) {
    localStorage.setItem(STORAGE_KEY, locale);
}

const i18n = createI18n({
    legacy: false,
    locale: getStoredLocale(),
    fallbackLocale: 'zh-CN',
    messages: {
        'zh-CN': zhCN,
        'ja-JP': jaJP,
    },
});

export default i18n;
